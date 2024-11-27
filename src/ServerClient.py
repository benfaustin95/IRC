import queue
import collections
from socket import socket
from codes import Error, RoomCode, NonFatalErrors
from message import Message, get_message, get_headers, MAX_PICKLED_HEADER_SIZE
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
            if (not self.socket_open or
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
        self.socket.close()
        self.socket_open = False
        for room in self.room_queues.keys():
            self.remove_room_from_client(room)
        self.socket_lock.release()

    def add_room_to_client(self, room_name: str, room_queue: queue.Queue):
        try:
            room_queue.put((RoomCode.ADD_CLIENT, self))
            self.room_queues[room_name] = room_queue
        except queue.ShutDown:
            raise Exception(NonFatalErrors.INVALID_JOIN_ROOM)

    def remove_room_from_client(self, room_name: str):
        if room_name not in self.room_queues:
            return

        try:
            self.room_queues[room_name].put(RoomMessage(RoomCode.REMOVE_CLIENT, self.nickname))
        except queue.ShutDown:
            print(f'{room_name} has already been closed')
        finally:
            del self.room_queues[room_name]

    def send_to_room(self, room_name: str, message: Message):
        try:
            if room_name not in self.room_queues:
                raise Exception(NonFatalErrors.MSG_FAILED)
            self.room_queues[room_name].put(RoomMessage(RoomCode.BROADCAST_MESSAGE, message))
        except queue.ShutDown:
            del self.room_queues[room_name]
            raise Exception(NonFatalErrors.ROOM_CLOSED)
