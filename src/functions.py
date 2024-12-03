import threading
import queue
from message import Message
from serverclient import ServerClient
from codes import Error, NonFatalErrors, Operation, ErrorException, NonFatalErrorException

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
if opcode in action_map:
    action_map[arg_len]()  # Now correctly passes args to _copy_constructor and _param_constructor
#Cannot find correct argument, abort instantiation.
else:
    raise ValueError("Invalid argument length when initializing SFTP build")
"""

server_action_map = {
    Operation.HELLO: 'hello',
    Operation.CREATE_ROOM: 'create_room',
    Operation.LIST_ROOMS: 'list_rooms',
    Operation.JOIN_ROOM: 'join_room',
    Operation.LEAVE_ROOM: 'leave_room',
    Operation.LIST_MEMBERS: 'list_members',
    Operation.SEND_MSG: 'send_msg',
    Operation.TERMINATE: 'terminate',
    Operation.BROADCAST_MSG: 'broadcast_lobby',
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

            nickname = message.payload
            print(f"DEBUG: Nickname {nickname}")

            # Ensure the nickname doesn't already exist
            if not nickname or not isinstance(nickname, str):
                raise ErrorException(Error.INVALID_HELLO)

            if nickname in self.clients:
                print(f"Nickname '{nickname}' already taken from {client_address}")  # ? DEBUG ?
                raise ErrorException(Error.TAKEN_NAME)
            # store client in existing clients list
            client = self.clients[nickname] = ServerClient(
                client_socket,
                client_address,
                nickname,
            )
            print(f"Handshake successful: {nickname} at {client_address}")  # ? DEBUG ?
            client.send_ok()
            client.add_room_to_client('lobby', self.rooms['lobby']['room_queue'])
            return self.clients[nickname]
        finally:
            self.client_lock.release()

    def create_room(self, **kwargs):
        print("Create Room function called")  # Implement the actual logic
        self.room_lock.acquire()
        try:
            message, client = kwargs['message'], kwargs['client']

            if len(self.rooms) >= self.max_rooms:
                raise NonFatalErrorException(NonFatalErrors.MAX_ROOMS)

            # might be able to change this to room names if we would like to
            room_number = message.payload

            if room_number in self.rooms or not isinstance(room_number, int):
                raise NonFatalErrorException(NonFatalErrors.INVALID_CREATE_ROOM)

            room = {
                'room_number': room_number,
                'room_queue': queue.Queue(),
                'room_clients': {client.nickname},
                'active': True,
            }
            threading.Thread(
                target=self.run_room,
                args=(room,),
                daemon=True,
            ).start()

            self.rooms[room['room_number']] = room
            client.send_to_room('lobby', {'text': f'room {room_number} has been created'})
            client.add_room_to_client(room_number, room['room_queue'])
            client.send_ok()
        finally:
            self.room_lock.release()

    def run_lobby(self, room):
        message_queue = room['room_queue']
        while True:
            try:
                payload = message_queue.get(timeout=60)

                if isinstance(payload, dict):
                    payload['room_number'] = 'lobby'
                else:
                    payload = {'room_number': 'lobby', 'text': payload}

                serialized_message = Message(Operation.BROADCAST_MSG, payload).serialize()
                try:
                    self.client_lock.acquire()
                    for client in self.clients.values():
                        try:
                            client.send_to_client(*serialized_message)
                        except:
                            print(f'failed to broadcast lobby message to {client.nickname}')
                finally:
                    self.client_lock.release()
            except queue.Empty:
                print('no message to broadcast lobby')

    def run_room(self, room):
        message_queue, clients = room['room_queue'], room['room_clients']
        while room['active']:
            try:
                payload = message_queue.get(timeout=60)

                if isinstance(payload, dict):
                    payload['room_number'] = room['room_number']
                else:
                    payload = {'room_number': room['room_number'], 'text': payload}

                serialized_message = Message(Operation.BROADCAST_MSG, payload).serialize()
                try:
                    self.client_lock.acquire()
                    for client in set(clients):
                        try:
                            if client in self.clients:
                                self.clients[client].send_to_client(*serialized_message)
                            else:
                                clients.remove(client)
                        except:
                            # what exceptions need to be handled
                            clients.remove(client)
                finally:
                    self.client_lock.release()
            except queue.Empty:
                print('no message to broadcast room:', room['room_number'])

            if len(clients) > 0:
                continue

            # If empty begin process of ending room by acquiring lock
            self.room_lock.acquire()
            # After acquiring lock if a client was added during that waiting period then do not end room
            if len(clients) == 0:
                message_queue.shutdown()
                del self.rooms[room['room_number']]
                room['active'] = False
            self.room_lock.release()

    def list_rooms(self, **kwargs):
        print("List Rooms function called")  # Implement the actual logic
        client = kwargs['client']
        serialized_message = Message(
            Operation.LIST_ROOMS_RESP,
            list(self.rooms.keys()),
        ).serialize()
        client.send_to_client(*serialized_message)

    def join_room(self, **kwargs):
        print("Join Room function called")  # Implement the actual logic
        message, client = kwargs['message'], kwargs['client']
        self.room_lock.acquire()
        # after lock has been acquired we know the room dict is accurate
        try:
            room_number = message.payload
            if room_number not in self.rooms:
                raise NonFatalErrorException(NonFatalErrors.INVALID_JOIN_ROOM)
            room = self.rooms[room_number]
            room['room_clients'].add(client.nickname)
            client.add_room_to_client(room_number, room['room_queue'])
            client.send_ok()
        finally:
            self.room_lock.release()

    def leave_room(self, **kwargs):
        print("Leave Room function called")  # Implement the actual logic
        self.room_lock.acquire()
        try:
            message, client = kwargs['message'], kwargs['client']
            room_number = message.payload

            if room_number == 'lobby':
                raise NonFatalErrorException(NonFatalErrors.INVALID_LEAVE_ROOM)

            if room_number not in self.rooms:
                client.send_ok()
                return

            room = self.rooms[room_number]
            if client.nickname in room['room_clients']:
                room['room_clients'].remove(client.nickname)

            client.remove_room_from_client(room_number)
            client.send_ok()
        finally:
            self.room_lock.release()

    def send_msg(self, **kwargs):
        print("Send Message function called")  # Implement the actual logic
        message, client = kwargs['message'], kwargs['client']
        if not isinstance(message.payload, dict):
            raise NonFatalErrorException(NonFatalErrors.MSG_REJECTED)
        room_number = message.payload.get('room_number')
        text = message.payload.get('text')
        if text is None:
            raise NonFatalErrorException(NonFatalErrors.MSG_REJECTED)
        client.send_to_room(room_number, {'text': text})

    def broadcast_lobby(self, **kwargs):
        print("Broadcast to lobby")  # Implement the actual logic
        message, client = kwargs['message'], kwargs['client']
        if not isinstance(message.payload, dict):
            raise NonFatalErrorException(NonFatalErrors.MSG_REJECTED)
        text = message.payload.get('text')
        if text is None:
            raise NonFatalErrorException(NonFatalErrors.MSG_REJECTED)
        client.send_to_room('lobby', {'text': text})

    def list_members(self, **kwargs):
        print("List Members function called")  # Implement the actual logic
        client = kwargs['client']
        serialized_message = Message(
            Operation.LIST_MEMBERS_RESP,
            list(self.clients.keys()),
        ).serialize()
        client.send_to_client(*serialized_message)

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
