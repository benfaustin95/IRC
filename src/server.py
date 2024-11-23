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

        self.running = True  # Flag to control server loop

        self.header_size = 600;
        #message buffer size is message dependent!!!!!! LOCAL SCOPE!!!!
        self.queue_size = 5
        self.port = 49152 #ephemeral port range - dynamic,temp connections used for client application, safe w/o conflicting service on system
        self.host = "127.0.0.1" # loopback address: allows computer to communicate with itself without user external network
        self.server = None

        self.sockets = []

        ######### Thread Stuff ########
        self.lock = threading.Lock()

    def start(self):

        # |  Create server and bind it to host and port |
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((self.host, self.port))
        self.server.listen(self.queue_size)  # enables the server to accept {queue_size}  number of connections
        self.server.settimeout(120.0)  # Timeout for accepting new connections; will throw exception: socket.timeout

        #NOTE: I DONT KNOW HOW TIMEOUT WORKS VERY WELL YET
        print(f"Server started on {self.host}:{self.port}") # ?DEBUG?

        while True:
            try:
                while self.running:
                    try:

                        client_socket, client_address = self.server.accept()#accept connect socket, get the socket object, address

                        print(f"Connection established with {client_address}")# ?DEBUG?

                        # Spin off a thread to handle the client. Make it a daemon( Daemon threads are abruptly stopped at shutdown) should't be a problem as no persisitng data????
                        threading.Thread(target=self.spin_off_thread, args=(client_socket, client_address), daemon=True).start()

                    # No connection was ready within the timeout, continue the loop
                    except socket.timeout:
                        continue
            finally:
                self.shutdown()


    def spin_off_thread(self, client_socket, client_address):

        client_socket.settimeout(600.0)  # Timeout for receiving data: 10 min

        try:
            # process handshake
            success = self.handshake(client_socket, client_address)


            # handshake was good, business logic time;passed socket,adress, nick
            if success is not None:
                self.business(client_socket, client_address,success)

        except Exception as e:
            print(f"Error with client {client_address}: {e}")
        finally:
            client_socket.close()
            print(f"Client {client_address} disconnected")

            # Clean up the client from the list and remove
            self.remove_client_connected_socket(client_socket)


    def handshake(self, client_socket, client_address):

        try:

            # receive the handshake header of header_size
            header_bytes_object = client_socket.recv(self.header_size)

            #load object back through pickle conversion from byte re-assembly
            header_object = pickle.loads(header_bytes_object)

            #return none if it's not a header object, handshake cannot proceed. !!! If u dont do this ur gonna love Executable malware !!!!!
            if not isinstance(Header):
                print(f"Bad handshake object from {client_address}") # ? DEBUG ?
                return None

            #Ensure we receive the handshake message
            if header_object.opcode is not Operation.HELLO:
                #send a message to the cleint indicating bad handshake
                print(f"Bad handshake OPCODE from {client_address}") # ? DEBUG ?
                return None

            #TODO: Ensure payload size is not 0 or None

            #get payload size
            payload_buffer = header_object.payload_size


            # Receive the payload (nickname)
            message_bytes_object = client_socket.recv(payload_buffer)
            message_object = pickle.loads(message_bytes_object)
            nickname = message_object.payload


            # Ensure the nickname doesn't already exist
            if nickname in self.clients:
                print(f"Nickname '{nickname}' already taken from {client_address}") # ? DEBUG ?
                return None

            #store client in existing clients list
            self.clients[nickname] = Client(client_socket, client_address, nickname)
            print(f"Handshake successful: {nickname} at {client_address}") # ? DEBUG ?
            return nickname


        except socket.timeout:
            #No data received within the timeout, return None
            print(f"Handshake Timeout {client_address}: {e}")
            return None

        except Exception as e:
            print(f"Handshake error with {client_address}: {e}")
            return None


    def business(self, client_socket, client_address, nickname):
        try:
            while self.running:
                try:
                    buffer_size = None
                    #read in next header of header_size

                        #verify its a good opcode
                        #figure out our buffer
                        #ensure its not None or 0


                    #read in  the message buffer size
                        #load message body if exists


                    #process into action mapped function
                        #process r_value of aciton map
                        #SPECIAL: check if its disconnect is call

                except socket.timeout:
                    # timeout message
                    print(f"Business timeout with {nickname} at {client_address}")
                    return


        except Exception as e:
            print(f"Communication error with {nickname} at {client_address}: {e}")


    # Clean up the client from the list
    def remove_client_connected_socket(self,client_socket):

        remove_nickname = None
        #find the key based on the client_socket
        for nickname, client in self.clients.items():
            if client.socket == client_socket:
                remove_nickname = nickname
                break

        # If a key was found, remove the key-value pair from the dictionary
        if remove_nickname is not None:
            del self.clients[remove_nickname]
            print(f"Removed client with socket: {client_socket}") # ? DEBUG ?
        else:
            #TODO: Raise custom exception...something is really wrong
            print(f"No client found with socket: {client_socket}") # ? DEBUG ?



    #stop time
    def stop(self):
        print("Stopping server...")
        self.running = False


    #Resources cleanup &  Close all connections
    def shutdown(self):

        print("Shutting down server...") # ? DEBUG ?
        if self.server:
            self.server.close()

        for nickname, client in self.clients.items():
            client.socket.close()

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


