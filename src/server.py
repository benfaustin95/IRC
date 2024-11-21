import pickle
import socket
import threading
from src.message import Header
from src.codes import Operation
from src.client import Client
import time


class Server:

    def __init__(self, max_rooms):

        self.clients = {}

        self.max_rooms = max_rooms
        self.rooms = [[]]

        ####### Server Stuff ###
        self.buffer_size = 1024
        self.queue_size = 5
        self.port = 5001
        self.host = socket.gethostbyname(socket.gethostname())
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((self.host, self.port))

        self.sockets = []

        ######### Thread Stuff ########
        self.lock = threading.Lock()

    def start(self):

        self.server.listen(self.queue_size)

        while True:

            a_socket, address = self.server.accept()  #TODO: change this to assing to tuple?

            #receive the object in pickle serialization form( bytes)
            header_bytes_object = a_socket.recv(self.buffer_size)  #TODO: refactor to use message class

            #Return the pickled representation of the object obj as a bytes object
            header_object = pickle.loads(header_bytes_object)

            #then sends the message to get the buffer size need for the coming message
            payload_buffer = header_object.payload_size

            #store the header's opcode
            opcode = header_object.opcode

            #Ensure we receive the handshake message
            if opcode is not Operation.HELLO:
                #send a message to the cleint indicating bad handshake

                #close connection to a_socket
                pass

            #receive the object in pickle serialization form( bytes)
            message_bytes_object = a_socket.recv(payload_buffer)

            #Return the pickled representation of the object obj as a bytes object
            message_object = pickle.loads(message_bytes_object)

            #set the name
            nickname = message_object.payload

            #ensure the nickname is not alreayd present and add it to our list of Clients
            if nickname not in self.clients:
                self.clients[nickname] = Client(a_socket, address, nickname)

                #Spin off the thead
                self.spin_off_thread(self.clients[nickname])

            else:

                #TODO: send message to client indicating taken username

                #TODO: close the connection
                pass

    def worker_func(self, client):

        while True:
            try:
                message_bytes = client.socket.recv(self.buffer_size)
                if not message_bytes:
                    break

                message_object = pickle.loads(message_bytes)

                #TODO: Process the message object here

                #TODO: if its not a valid opcode return errro

            #TODO: done with task( deincrement queue)

            except Exception as e:
                print(f"Error with client {client.nickname}: {e}")
                break

        with self.lock:
            del self.clients[client.nickname]
        client.socket.close()

    def spin_off_thread(self, client):
        client_thread = threading.Thread(target=self.worker_func, args=client)
        client_thread.daemon = True
        client_thread.start()

    def __del_(self):
        pass
