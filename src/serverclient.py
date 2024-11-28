import queue
import collections
from socket import socket, SHUT_RDWR, error
from codes import Error, NonFatalErrors, Operation, NonFatalErrorException, ErrorException
from message import get_message, Message, get_message_len, MAX_MSG_BYTES
import threading

RoomMessage = collections.namedtuple('RoomMessage', ['roomCode', 'payload'])


class ServerClient:
    def __init__(self, client_socket: socket, client_address, nickname: str, room_queues=None):
        self.nickname: str = nickname
        self.client_address = client_address
        self.socket: socket = client_socket
        self.room_queues: dict[str, queue.Queue] = room_queues if room_queues is not None else {}
        self.socket_lock: threading.Lock = threading.Lock()
        self.socket_open: bool = True

    def send_to_client(self, msg_len: bytes, serialized_message: bytes):
        try:
            self.socket_lock.acquire()
            print('message sent to client: ', get_message(serialized_message).payload)
            if (self.socket.fileno() == -1 or
                    self.socket.sendall(msg_len) is not None or
                    self.socket.sendall(serialized_message) is not None):
                # Should this be client closed error?
                raise ErrorException(Error.GEN_ERROR)
        finally:
            self.socket_lock.release()

    def recv_from_client(self):
        msg_len = get_message_len(self.socket.recv(MAX_MSG_BYTES))
        serialized_message = self.socket.recv(msg_len)
        return get_message(serialized_message)

    def close(self):
        self.socket_lock.acquire()

        if self.socket.fileno() != -1:
            try:
                self.socket.shutdown(SHUT_RDWR)
                self.socket.close()
            except error:
                print('socket already closed....')

        self.socket_open = False
        self.socket_lock.release()

    def add_room_to_client(self, room_name: str, room_queue: queue.Queue):
        if room_name in self.room_queues:
            return
        try:
            room_queue.put(Message(
                Operation.BROADCAST_MSG,
                {'text': f'{self.nickname} has joined the room'},
            ))
            self.room_queues[room_name] = room_queue
        except queue.ShutDown:
            raise NonFatalErrorException(NonFatalErrors.INVALID_JOIN_ROOM)

    def remove_room_from_client(self, room_name: str):
        if room_name not in self.room_queues:
            return

        try:
            self.room_queues[room_name].put(Message(
                Operation.BROADCAST_MSG,
                {'text': f'{self.nickname} has left room'},
            ))
        except queue.ShutDown:
            print(f'{room_name} has already been closed')
        finally:
            del self.room_queues[room_name]

    def send_to_room(self, room_name: str, message: Message):
        try:
            if room_name not in self.room_queues:
                raise NonFatalErrorException(NonFatalErrors.MSG_FAILED)
            self.room_queues[room_name].put(message)
        except queue.ShutDown:
            del self.room_queues[room_name]
            raise NonFatalErrorException(NonFatalErrors.ROOM_CLOSED)

    def send_ok(self):
        self.send_to_client(*Message(Operation.OK, 'SUCCESS').serialize())
