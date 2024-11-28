import socket
import threading
from codes import Operation
from codes import Error
from client import Client
from functions import *

import time

MAX_MSG_BYTES = 4
LOCAL_HOST = "127.0.0.1"
PORT = 49152
MAX_QUEUE_SIZE = 5

class Server:

    def __init__(self, max_rooms):

        self.clients = {}
        self.max_rooms = max_rooms
        self.rooms = [[]]

        self.client_names = []
        #! Placeholder for testing broadcast
        self.broadcast_msg_queue = []
        self.broadcast_lock = threading.Lock()


        ####### Server Stuff ###
        self.running = True  # Flag to control server loop
        self.queue_size = MAX_QUEUE_SIZE
        self.port = PORT #ephemeral port range - dynamic,temp connections used for client application, safe w/o conflicting service on system
        self.host = LOCAL_HOST # loopback address: allows computer to communicate with itself without user external network
        self.server = None

        self.sockets = []

        ######### Thread Stuff ########
        self.broadcast_lock = threading.Lock()

    def start(self):

        # |  Create server and bind it to host and port |
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((self.host, self.port))
        self.server.listen(self.queue_size)  # enables the server to accept {queue_size}  number of connections
        self.server.settimeout(1.0)  # Timeout for accepting new connections; will throw exception: socket.timeout

        #NOTE: I DONT KNOW HOW TIMEOUT WORKS VERY WELL YET
        print(f"Server started on {self.host}:{self.port}") # ?DEBUG?

        try:
            while self.running:
                try:

                    client_socket, client_address = self.server.accept()#accept connect socket, get the socket object, address
                    print(f"Connection established with {client_address}")# ?DEBUG?
                    
                    # Spin off a thread to handle the client. Make it a daemon( Daemon threads are abruptly stopped at shutdown) should't be a problem as no persisitng data????
                    threading.Thread(target=self.spin_off_thread, args=(client_socket, client_address), daemon=True).start()

                    threading.Thread(target=self.broadcast_thread, args=(), daemon=True).start()

                # No connection was ready within the timeout, continue the loop
                except socket.timeout:
                    continue
        finally:
            self.shutdown()

    def broadcast_thread(self):
        try:
            while (self.running):
                if (self.broadcast_msg_queue):
                    with self.broadcast_lock:
                        msg = self.broadcast_msg_queue.pop(0)
                        for nickname in self.client_names:
                            if (self.clients[nickname]):
                                self.send_msg(msg, self.clients[nickname])
        except Exception as e:
            print(f"Exception in broadcast thread: {e}")


    def spin_off_thread(self, client_socket, client_address):

        client_socket.settimeout(600.0)  # Timeout for receiving data: 10 min
        success = False

        try:
            while success is False:
                success = self.handshake(client_socket, client_address)

            if success is not None:
                self.business(client_socket, client_address,success)

        except Exception as e:
            print(f"Error with client {client_address}: {e}")
        finally:
            # Safe closing of the socket
            try:
                # Check if the socket is open before closing
                if client_socket.fileno() != -1:
                    client_socket.close()
                    print(f"Client {client_address} socket closed.")
            except socket.error as e:
                # Handle the case where the socket is already closed or in a bad state
                print(f"Socket error when closing client {client_address}: {e}")
            except Exception as e:
                # Catch any other unexpected exceptions
                print(f"Unexpected error while closing socket for {client_address}: {e}")


    def handshake(self, client_socket, client_address):
        try:
            msg_obj = self.recv_msg(client_socket)
            print(msg_obj.payload)


            nickname = msg_obj.payload
            if nickname in self.clients:
                err_msg = Message(Error.TAKEN_NAME, "username taken")
                self.send_msg(err_msg, client_socket)
                return False

            msg_response = Message(Operation.OK, "OK")
            self.send_msg(msg_response, client_socket)
            print("sent OK")

            self.clients[nickname] = client_socket
            self.client_names.append(nickname)
            return nickname

        except socket.timeout:
            #No data received within the timeout, return None
            print(f"Handshake Timeout {client_address}: socket.timeout")
            return None

        except Exception as e:
            print(f"Handshake error with {client_address}: {e}")
            return None

    def recv_msg(self, client_socket):
        msg_len = client_socket.recv(4)
        msg_len = int.from_bytes(msg_len, byteorder='big')
        print(f"MSG LEN: {msg_len}")

        msg_obj = pickle.loads(client_socket.recv(msg_len)) 
        return msg_obj

    def send_msg(self, msg, client_socket):
        p_msg = pickle.dumps(msg)
        msg_len = len(p_msg).to_bytes(4, byteorder='big')
        
        client_socket.sendall(msg_len)
        client_socket.sendall(p_msg)

    
    def business(self, client_socket, client_address, nickname):
        try:
            while self.running:
                try:
                    msg_obj = self.recv_msg(client_socket)
                    print(f"Received: {msg_obj.payload} from {nickname}")

                    # if not isinstance(msg_obj, Message):
                    #     print(f"Bad handshake object from {client_address}") # ? DEBUG ?
                    #     return None

                    # #Ensure we receive the handshake message
                    # if msg_obj.opcode not in Operation:
                    #     #send a message to the cleint indicating bad handshake
                    #     print(f"Bad handshake OPCODE from {client_address}") # ? DEBUG ?
                    #     return None
                    

                    # if msg_obj.opcode == Operation.TERMINATE:
                    #     print(f"Client {client_address} requested termination.")
                    #     return None

                    print(f"OPCODE: {msg_obj.opcode}")
                    print(f"MESSAGE: {msg_obj.payload}")
                    if (msg_obj.opcode == Operation.BROADCAST_MSG):
                        msg_payload = nickname + ":" + str(msg_obj.payload)
                        msg = Message(Operation.SEND_MSG, msg_payload)

                        self.broadcast_msg_queue.append(msg)
                        # client_socket.sendall(ph)
                        # client_socket.sendall(pmsg)

                    #process into action mapped function
                        #process r_value of aciton map
                        #SPECIAL: check if its disconnect is call
                    #result = func_to_run(message_object)

                    # if (result is Operation.TERMINATE):
                    #     print(f"Terminate operation")

                except socket.timeout:
                    # timeout message
                    print(f"Business timeout with {nickname} at {client_address}")
                    return


        except Exception as e:
            print(f"Communication error with {nickname} at {client_address}: {e}")


#     # Clean up the client from the list
#     def remove_client_connected_socket(self,client_socket):
# #! TODO: Bring back dictionary 
#         # remove_nickname = None
#         # #find the key based on the client_socket
#         # for nickname, client in self.clients.items():
#         #     if client.socket == client_socket:
#         #         remove_nickname = nickname
#         #         break

#         # If a key was found, remove the key-value pair from the dictionary
#         if remove_nickname is not None:
#             del self.clients[remove_nickname]
#             print(f"Removed client with socket: {client_socket}") # ? DEBUG ?
#         else:
#             #TODO: Raise custom exception...something is really wrong
#             print(f"No client found with socket: {client_socket}") # ? DEBUG ?



    #stop time
    def stop(self):
        print("Stopping server...")
        self.running = False


    #Resources cleanup &  Close all connections
    def shutdown(self):

        print("Shutting down server...") # ? DEBUG ?
        if self.server:
            self.server.close()

        # #TODO: this isnt gonna work
        # for nickname, client in self.clients.items():
        #     client.socket.close()

        print("Server shut down.") # ? DEBUG ?


if __name__ == "__main__":
    server = Server(max_rooms=12)

    # Run server in  separate thread
    server_thread = threading.Thread(target=server.start)
    server_thread.start()

    # Wait fr input to stop the server
    input("Press Enter to stop the server...\n")
    server.stop()
    server_thread.join()