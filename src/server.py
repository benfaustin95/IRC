import socket
import threading
from message import get_message, get_headers, create_packages, MAX_PICKLED_HEADER_SIZE
from codes import Operation, Error, NonFatalErrors, ErrorException, NonFatalErrorException
from functions import server_action_map, ServerActions
from ServerClient import ServerClient

MAX_INT = 2 ** 31 - 1
LOCAL_HOST = "127.0.0.1"
PORT = 49152
QUEUE_SIZE = 5


class Server(ServerActions):

    def __init__(self, max_rooms):
        super().__init__(max_rooms)
        ####### Server Stuff ###

        self.running = True  # Flag to control server loop

        self.header_size = MAX_PICKLED_HEADER_SIZE
        # message buffer size is message dependent!!!!!! LOCAL SCOPE!!!!
        self.queue_size = QUEUE_SIZE
        self.port = PORT  # ephemeral port range - dynamic,temp connections used for client application, safe w/o conflicting service on system
        self.host = LOCAL_HOST  # loopback address: allows computer to communicate with itself without user external network
        self.server = None

    def start(self):

        # |  Create server and bind it to host and port |
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((self.host, self.port))
        self.server.listen(self.queue_size)  # enables the server to accept {queue_size}  number of connections
        self.server.settimeout(1.0)  # Timeout for accepting new connections; will throw exception: socket.timeout

        # NOTE: I DON'T KNOW HOW TIMEOUT WORKS VERY WELL YET
        print(f"Server started on {self.host}:{self.port}")  # ?DEBUG?

        try:
            while self.running:
                try:

                    client_socket, client_address = self.server.accept()  # accept connect socket, get the socket object, address

                    print(f"Connection established with {client_address}")  # ?DEBUG?

                    # Spin off a thread to handle the client. Make it a daemon( Daemon threads are abruptly stopped at shutdown) should't be a problem as no persisitng data????
                    threading.Thread(target=self.spin_off_thread, args=(client_socket, client_address),
                                     daemon=True).start()

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
                        for c in self.clients:
                            ph = msg[0]
                            pmsg = msg[1]
                            c.sendall(ph)
                            c.sendall(pmsg)
        except Exception as e:
            print(f"Exception in broadcast thread: {e}")

    def spin_off_thread(self, client_socket, client_address):

        client_socket.settimeout(600.0)  # Timeout for receiving data: 10 min
        client = None

        try:
            # process handshake
            while client is None:
                client = self.handshake(client_socket, client_address)

            # handshake was good, business logic time;passed socket,address, nick
            if client is not None:
                self.business(client)

        except Exception as e:
            print(f"Error with client {client_address}: {e}")
        finally:
            # Safe closing of the socket
            try:
                # Check if the socket is open before closing
                if client_socket.fileno() != -1:
                    client_socket.close()
                    print(f"Client {client_address} socket closed.")
                self.client_lock.acquire()

                found = None
                for (name, client) in self.clients.items():
                    if client.socket == client_socket:
                        found = name
                        break

                if found and self.clients[found].:
                    del self.clients[found]

                self.client_lock.release()
            except socket.error as e:
                # Handle the case where the socket is already closed or in a bad state
                print(f"Socket error when closing client {client_address}: {e}")
            except Exception as e:
                # Catch any other unexpected exceptions
                print(f"Unexpected error while closing socket for {client_address}: {e}")

    def handshake(self, client_socket, client_address):

        try:
            # receive the handshake header of header_size
            header_bytes_object = client_socket.recv(self.header_size)

            # NOTE: recv() returns an empty byte string when the socket is closed or there is no data left to read.
            print(header_bytes_object)
            # load object back through pickle conversion from byte re-assembly
            header_object = get_headers(header_bytes_object)

            print(f"HEADER: {header_object.opcode}")

            ###### Emegency Checks. Ideally client should filter all this bad data out #############

            # Ensure we receive the handshake message
            if header_object.opcode is not Operation.HELLO:
                print(f"Bad handshake OPCODE from {client_address}")  # ? DEBUG ?
                return None

            # TODO: Ensure payload size is not 0 or None

            # get payload size
            payload_buffer = header_object.payload_size

            print("DEBUG: waiting to receive nickname message")
            # Receive the payload (nickname)
            message_bytes_object = client_socket.recv(payload_buffer)
            message_object = get_message(message_bytes_object)
            print(f"DEBUG: Message object {message_object}")
            nickname = message_object.payload
            print(f"DEBUG: Nickname {nickname}")
            return getattr(self, server_action_map[header_object.opcode])(
                message=message_object,
                client_socket=client_socket,
                client_address=client_address
            )

        except Exception as e:
            print(f"Handshake error with {client_address}: {e}")
            opcode = e.error if isinstance(e, ErrorException) else Error.INVALID_HELLO
            message = "INVALID HELLO: CONNECTION TERMINATED"
            serialized_header, serialized_message = create_packages(message, opcode, message_type='Message')
            client_socket.sendall(serialized_header)
            client_socket.sendall(serialized_message)
            return None

    def test_send(self, client_socket):
        print("SENDING TEST")
        ph, pmsg = create_packages("TEST_SEND", Operation.HELLO, "Message")
        client_socket.sendall(ph)
        client_socket.sendall(pmsg)

    def business(self, client: ServerClient):
        while self.running:
            try:
                header, message = client.recv_from_client()
                # Ensure we receive the handshake message
                if header.opcode not in Operation or header.opcode is Operation.HELLO:
                    raise Error.INVALID_OPCODE
                getattr(self, server_action_map[header.opcode])(message=message, client=client)
            except socket.timeout:
                # timeout message
                print(f"Business timeout with {client.nickname} at {client.socket}")
            except NonFatalErrorException as e:
                # TODO: Probably want to send the original message back in payload
                serialized_header, serialized_message = create_packages('INVALID OPERATION', e.error, 'Message')
                print('non fatal error', e)
                client.send_to_client(serialized_header, serialized_message)
            except ErrorException as e:
                # TODO: Probably want to send the original message back in payload
                serialized_header, serialized_message = create_packages('FATAL ERROR: CONNECTION TERMINATED', e.error,
                                                                        'Message')
                client.send_to_client(serialized_header, serialized_message)
                return
            except Exception as e:
                # TODO: Probably want to send the original message back in payload
                print(f"Communication error with {client.nickname} at {client.client_address}: {e}")
                serialized_header, serialized_message = create_packages('FATAL ERROR: CONNECTION TERMINATED',
                                                                        Error.GEN_ERROR, 'Message')
                client.send_to_client(serialized_header, serialized_message)
                return

    #     # Clean up the client from the list
    #     def remove_client_connected_socket(self,client_socket):
    # #! TODO: Bring back dictionary
    #         # remove_nickname = None
    #         # #find the key based on the client_socket
    #         # for nickname, client in self.clients.items():
    #         #     if client.socket == client_socket:
    #         #         remove_nickname = nickname
    #         #         break
    # Clean up the client from the list
    def remove_client_connected_socket(self, client_socket):

        #         # If a key was found, remove the key-value pair from the dictionary
        #         if remove_nickname is not None:
        #             del self.clients[remove_nickname]
        #             print(f"Removed client with socket: {client_socket}") # ? DEBUG ?
        #         else:
        #             #TODO: Raise custom exception...something is really wrong
        #             print(f"No client found with socket: {client_socket}") # ? DEBUG ?
        remove_nickname = None
        # find the key based on the client_socket
        for nickname, client in self.clients.items():
            if client.socket == client_socket:
                remove_nickname = nickname
                break

        # If a key was found, remove the key-value pair from the dictionary
        if remove_nickname is not None:
            del self.clients[remove_nickname]
            print(f"Removed client with socket: {client_socket}")  # ? DEBUG ?
        else:
            # TODO: Raise custom exception...something is really wrong
            print(f"No client found with socket: {client_socket}")  # ? DEBUG ?

    # stop time
    def stop(self):
        print("Stopping server...")
        self.running = False

    # Resources cleanup &  Close all connections
    def shutdown(self):

        print("Shutting down server...")  # ? DEBUG ?
        if self.server:
            self.server.close()

        # #TODO: this isnt gonna work
        # for nickname, client in self.clients.items():
        #     client.socket.close()

        print("Server shut down.")  # ? DEBUG ?


if __name__ == "__main__":
    server = Server(max_rooms=12)

    # Run server in  separate thread
    server_thread = threading.Thread(target=server.start)
    server_thread.start()

    # Wait fr input to stop the server
    input("Press Enter to stop the server...\n")
    server.stop()
    server_thread.join()
