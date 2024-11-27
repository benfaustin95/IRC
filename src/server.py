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

        self.sockets = []

        ######### Thread Stuff ########
        self.lock = threading.Lock()

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
        client = False

        try:
            # process handshake
            while client is False:
                client = self.handshake(client_socket, client_address)


            # handshake was good, business logic time;passed socket,adress, nick
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

            #NOTE: recv() returns an empty byte string when the socket is closed or there is no data left to read.

            # load object back through pickle conversion from byte re-assembly
            header_object = get_headers(header_bytes_object)

            print(f"HEADER: {header_object.opcode}")

            ###### Emegency Checks. Ideally client should filter all this bad data out #############


            # Ensure we receive the handshake message
            if header_object.opcode is not Operation.HELLO:
                print(f"Bad handshake OPCODE from {client_address}")  # ? DEBUG ?
                return None



            #TODO: Ensure payload size is not 0 or None

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
            serialized_header, serialized_message = create_packages(message, opcode, 'Message')
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
                if header.opcode is Operation.TERMINATE:
                    break
                server_action_map[message.opcode][0](message=message, client=client)
            except socket.timeout:
                # timeout message
                print(f"Business timeout with {client.nickname} at {client.socket}")
            except NonFatalErrorException as e:
                # TODO: Probably want to send the original message back in payload
                serialized_header, serialized_message = create_packages('INVALID OPERATION', e.error, 'Message')
                client.send_to_client(serialized_header, serialized_message)
            except ErrorException as e:
                # TODO: Probably want to send the original message back in payload
                serialized_header, serialized_message = create_packages('FATAL ERROR: CONNECTION TERMINATED', e.error, 'Message')
                client.send_to_client(serialized_header, serialized_message)
                return
            except Exception as e:
                # TODO: Probably want to send the original message back in payload
                print(f"Communication error with {client.nickname} at {client.client_address}: {e}")
                serialized_header, serialized_message = create_packages('FATAL ERROR: CONNECTION TERMINATED', Error.GEN_ERROR, 'Message')
                client.send_to_client(serialized_header, serialized_message)
                return

    def business_og(self, client_socket, client_address, nickname):
        try:
            while self.running:
                try:
                    buffer_size = None
                    buffer = None

                    # ************************************* #
                    # |  read in next header of header_size |
                    # ************************************* #

                    # receive the handshake header of header_size
                    header_bytes_object = client_socket.recv(self.header_size)


                    #load object back through pickle conversion from byte re-assembly
                    header_object = pickle.loads(header_bytes_object)

                    #return none if it's not a header object, handshake cannot proceed. !!! If u dont do this ur gonna love Executable malware !!!!!
                    if not isinstance(header_object,Header):
                        print(f"Bad handshake object from {client_address}") # ? DEBUG ?
                        return None

                    #Ensure we receive the handshake message
                    if header_object.opcode not in Operation:
                        #send a message to the cleint indicating bad handshake
                        print(f"Bad handshake OPCODE from {client_address}") # ? DEBUG ?
                        return None


                    if header_object.opcode == Operation.TERMINATE:
                        print(f"Client {client_address} requested termination.")
                        return None

                    #TODO: Ensure payload size is not 0 or None

                    #get payload size
                    buffer_size = header_object.payload_size

                    # ************************************* #
                    # |  read in payload of buffer_size |
                    # ************************************* #

                    # receive the handshake header of header_size
                    message_bytes_object = client_socket.recv(header_object.payload_size)

                    #load object back through pickle conversion from byte re-assembly
                    message_object = pickle.loads(message_bytes_object)

                    #return none if it's not a header object, handshake cannot proceed. !!! If u dont do this ur gonna love Executable malware !!!!!

                    #TODO: check if instance in second element of one of action map assosciated opcode operation
                    if not isinstance(message_object,Message): # message_object, type(action_map[opcode][1])
                        print(f"Bad message object from {client_address}") # ? DEBUG ?
                        return None

                    print(f"OPCODE: {header_object.opcode}")
                    print(f"MESSAGE: {message_object.payload}")
                    if (header_object.opcode == Operation.BROADCAST_MSG):
                        msg = nickname + ":" + str(message_object.payload)
                        ph, pmsg = create_packages(msg, Operation.SEND_MSG, "Message")
                        item = (ph, pmsg)
                        self.broadcast_msg_queue.append(item)
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

    def business(self, client: ServerClient):
        while self.running:
            try:
                header, message = client.recv_from_client()
                # Ensure we receive the handshake message
                if header.opcode not in Operation or header.opcode is Operation.HELLO:
                    raise Error.INVALID_OPCODE
                if header.opcode is Operation.TERMINATE:
                    break
                server_action_map[message.opcode][0](message=message, client=client)
            except socket.timeout:
                # timeout message
                print(f"Business timeout with {client.nickname} at {client.socket}")
            except NonFatalErrorException as e:
                # TODO: Probably want to send the original message back in payload
                serialized_header, serialized_message = create_packages('INVALID OPERATION', e.error, 'Message')
                client.send_to_client(serialized_header, serialized_message)
            except ErrorException as e:
                # TODO: Probably want to send the original message back in payload
                serialized_header, serialized_message = create_packages('FATAL ERROR: CONNECTION TERMINATED', e.error, 'Message')
                client.send_to_client(serialized_header, serialized_message)
                return
            except Exception as e:
                # TODO: Probably want to send the original message back in payload
                print(f"Communication error with {client.nickname} at {client.client_address}: {e}")
                serialized_header, serialized_message = create_packages('FATAL ERROR: CONNECTION TERMINATED', Error.GEN_ERROR, 'Message')
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


