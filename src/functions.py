import threading
import queue
from message import Message, create_packages
from ServerClient import ServerClient, RoomMessage
from codes import Error, NonFatalErrors, Operation, ErrorException, NonFatalErrorException, RoomCode

"""
# Action_map is a dictionary that maps the number of arguments (arg_len) to specific functions.
# This allows us to dynamically choose which function to execute based on the number of arguments.
self._default_constructor()
action_map = {
    0: lambda: self._default_constructor(),
    1: lambda: self._sftp_client_DI_constructor(*args),  # Wrap the call in a lambda to pass args
    4: lambda: self._param_constructor(*args)  # Wrap the call in a lambda to pass args
}

#Call the appropriate constructor based on match.
if opcodde in action_map:
    action_map[arg_len]()  # Now correctly passes args to _copy_constructor and _param_constructor
#Cannot find correct argument, abort instansiation.
else:
    raise ValueError("Invalid argument length when initializing SFTP build")
"""

# Creates a serialized header with padding to match the required size.


server_action_map = {
    Operation.HELLO: 'hello',
    Operation.CREATE_ROOM: 'create_room',
    Operation.LIST_ROOMS: 'list_rooms',
    Operation.JOIN_ROOM: 'join_room',
    Operation.LEAVE_ROOM: 'leave_room',
    Operation.LIST_MEMBERS: 'list_members',
    Operation.SEND_MSG: 'send_msg',
    Operation.TERMINATE: 'terminate',
    12: 'private_msg',
    13: 'forward_msg',
    14: 'forward_msg_q',
    15: 'send_file',
    16: 'forward_file',
    17: 'forward_file_q',
    18: 'ping',
}


class ServerActions:
    def __init__(self, max_rooms):
        self.max_rooms = max_rooms
        self.client_lock = threading.Lock()
        self.clients = {}
        self.room_lock = threading.Lock()
        self.rooms = {}

    def hello(self, **kwargs):
        print("Hello function called")  # Implement the actual logic
        self.client_lock.acquire()
        try:
            message, client_socket, client_address = kwargs['message'], kwargs['client_socket'], kwargs[
                'client_address']
            payload = message.payload

            print(payload)
            if 'nickname' not in payload:
                raise ErrorException(Error.INVALID_HELLO)

            nickname = payload['nickname']
            print(f"DEBUG: Nickname {nickname}")

            # Ensure the nickname doesn't already exist
            if nickname in self.clients:
                print(f"Nickname '{payload['nickname']}' already taken from {client_address}")  # ? DEBUG ?
                raise ErrorException(Error.TAKEN_NAME)

            # store client in existing clients list
            self.clients[nickname] = ServerClient(client_socket, client_address, nickname)
            print(f"Handshake successful: {nickname} at {client_address}")  # ? DEBUG ?
            return self.clients[nickname]
        finally:
            self.client_lock.release()

    def create_room(self, **kwargs):
        print("Create Room function called")  # Implement the actual logic
        self.room_lock.acquire()
        try:
            message, client = kwargs['message'], kwargs['client']

            if len(self.rooms) == self.max_rooms:
                raise NonFatalErrorException(NonFatalErrors.MAX_ROOMS)

            if 'room_name' not in message.payload or message.payload['room_name'] in self.rooms:
                raise NonFatalErrorException(NonFatalErrors.INVALID_CREATE_ROOM)

            room_name = message.payload['room_name']

            self.rooms[room_name] = (room_name, queue.Queue(), {client.nickname: client})

            threading.Thread(
                target=self.run_room,
                args=self.rooms[room_name],
                daemon=True,
            ).start()

            client.add_room_to_client(room_name, self.rooms[room_name][1])
        finally:
            self.room_lock.release()

    def run_room(self, room_name: str, message_queue: queue.Queue[RoomMessage], clients: dict[str, ServerClient]):
        while True:
            message_type, payload = message_queue.get()

            if message_type is RoomCode.REMOVE_CLIENT and payload in clients:
                del clients[payload]
                payload = create_packages(
                    {'room_name': room_name, 'text': f'{payload} has left the room'},
                    Operation.BROADCAST_MSG,
                    'Message',
                )
            elif message_type is RoomCode.ADD_CLIENT and payload.nickname not in clients:
                clients[payload.nickname] = payload
                payload = create_packages(
                    {'room_name': room_name, 'text': f'{payload} has joined the room'},
                    Operation.BROADCAST_MSG,
                    'Message',
                )
            elif message_type is RoomCode.ADD_CLIENT:
                continue
            else:
                payload = create_packages(payload.payload, Operation.BROADCAST_MSG, 'Message')

            if len(clients) == 0 and message_queue.empty():
                break

            for client in self.clients.values():
                try:
                    if not client.socket_open:
                        del clients[client.nickname]
                    else:
                        client.send_to_client(*payload)
                except Error:
                    del self.clients[client.nickname]

        self.room_lock.acquire()
        message_queue.shutdowm()
        del self.rooms[room_name]
        self.room_lock.release()

    def list_rooms(self, **kwargs):
        print("List Rooms function called")  # Implement the actual logic
        client = kwargs['client']
        serialized_header, serialized_message = create_packages({'rooms': self.rooms.keys()}, Operation.LIST_ROOMS_RESP,
                                                                'Message')
        client.send_to_client(serialized_header, serialized_message)

    def join_room(self, **kwargs):
        print("Join Room function called")  # Implement the actual logic
        self.room_lock.acquire()
        try:
            message, client = kwargs['message'], kwargs['client']
            if 'room_name' not in message.payload or message.payload['room_name'] not in self.rooms:
                raise NonFatalErrorException(NonFatalErrors.INVALID_JOIN_ROOM)
            room_name = message.payload['room_name']
            client.add_room_to_client(room_name, self.rooms[room_name][1])
        finally:
            self.room_lock.release()

    def leave_room(self, **kwargs):
        print("Leave Room function called")  # Implement the actual logic
        message, client = kwargs['message'], kwargs['client']
        if 'room_name' in message.payload:
            client.remove_room_from_client(message.payload['room_name'])

    def send_msg(self, **kwargs):
        print("Send Message function called")  # Implement the actual logic
        message, client = kwargs['message'], kwargs['client']
        room_name = message.payload.get('room_name')
        text = message.payload.get('text')
        if room_name is None or text is None:
            raise NonFatalErrorException(NonFatalErrors.MSG_FAILED)
        message = Message(Operation.BROADCAST_MSG, text)
        client.send_to_room(room_name, message)

    def terminate(self, **kwargs):
        print("Terminate function called")  # Implement the actual logic
        self.client_lock.acquire()
        try:
            client = kwargs['client']
            client.close()
            del self.clients[client.nickname]
        finally:
            self.client_lock.release()

    def private_msg(self, **kwargs):
        print("Private Message function called")  # Implement the actual logic

    def forward_msg(self, **kwargs):
        print("Forward Message function called")  # Implement the actual logic

    def forward_msg_q(self, **kwargs):
        print("Forward Message Query function called")  # Implement the actual logic

    def send_file(self, **kwargs):
        print("Send File function called")  # Implement the actual logic

    def forward_file(self, **kwargs):
        print("Forward File function called")  # Implement the actual logic

    def forward_file_q(self, **kwargs):
        print("Forward File Query function called")  # Implement the actual logic

    def ping(self, **kwargs):
        print("Ping function called")  # Implement the actual logic
