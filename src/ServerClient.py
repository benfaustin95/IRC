import queue
import collections
from socket import socket
from codes import Error, RoomCode, NonFatalErrors, Operation, NonFatalErrorException
from message import Message, get_message, get_headers, MAX_PICKLED_HEADER_SIZE, create_packages
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

    def send_to_client(self, serialized_header: bytes, serialized_message: bytes):
        try:
            self.socket_lock.acquire()
            if (self.socket.fileno() == -1 or
                    self.socket.sendall(serialized_header) is not None or
                    self.socket.sendall(serialized_message) is not None):
                # Should this be client closed error?
                raise Exception(Error.GEN_ERROR)
        finally:
            self.socket_lock.release()

    def recv_from_client(self):
        header_bytes_object = self.socket.recv(MAX_PICKLED_HEADER_SIZE)
        header = get_headers(header_bytes_object)
        serialized_message = self.socket.recv(header.payload_size)
        return header, get_message(serialized_message)

    def close(self):
        self.socket_lock.acquire()
        if self.socket.fileno() != -1:
            self.socket.close()
        self.socket_open = False
        self.socket_lock.release()

    def add_room_to_client(self, room_name: str, room_queue: queue.Queue):
        if room_name in self.room_queues:
            return
        print(self.room_queues.keys())
        try:
            message = create_packages(
                f'{self.nickname} has joined the room',
                Operation.BROADCAST_MSG,
                message_type='Message'
            )
            room_queue.put(message)
            self.room_queues[room_name] = room_queue
        except queue.ShutDown:
            raise NonFatalErrorException(NonFatalErrors.INVALID_JOIN_ROOM)

    def remove_room_from_client(self, room_name: str):
        if room_name not in self.room_queues:
            return

        try:
            message = create_packages(
                f'{self.nickname} has left the room',
                Operation.BROADCAST_MSG,
                message_type='Message'
            )
            self.room_queues[room_name].put(message)
        except queue.ShutDown:
            print(f'{room_name} has already been closed')
        finally:
            del self.room_queues[room_name]

    def send_to_room(self, room_name: str, message):
        try:
            if room_name not in self.room_queues:
                raise NonFatalErrorException(NonFatalErrors.MSG_FAILED)
            self.room_queues[room_name].put(message)
        except queue.ShutDown:
            del self.room_queues[room_name]
            raise NonFatalErrorException(NonFatalErrors.ROOM_CLOSED)

    def send_ok(self):
        serialized_header, serialized_message = create_packages('Success', Operation.OK, message_type='Message')
        self.send_to_client(serialized_header, serialized_message)
