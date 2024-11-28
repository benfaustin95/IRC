import queue
import socket
import threading
from message import get_message, MAX_MSG_BYTES, Message, get_message_len
from codes import Operation, Error, NonFatalErrors, ErrorException, NonFatalErrorException
from functions import server_action_map, ServerActions
from ServerClient import ServerClient

LOCAL_HOST = "127.0.0.1"
PORT = 49152
MAX_QUEUE_SIZE = 5



class Server(ServerActions):

    def __init__(self, max_rooms):
        super().__init__(max_rooms)
        ####### Server Stuff ###

        self.running = True  # Flag to control server loop
        # message buffer size is message dependent!!!!!! LOCAL SCOPE!!!!
        self.queue_size = MAX_QUEUE_SIZE
        self.port = PORT  # ephemeral port range - dynamic,temp connections used for client application, safe w/o conflicting service on system
        self.host = LOCAL_HOST  # loopback address: allows computer to communicate with itself without user external network
        self.server = None

        ######### Thread Stuff ########
        self.broadcast_lock = threading.Lock()

    def start(self):

        # |  Create server and bind it to host and port |
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((self.host, self.port))
        self.server.listen(self.queue_size)  # enables the server to accept {queue_size}  number of connections
        self.server.settimeout(1.0)  # Timeout for accepting new connections; will throw exception: socket.timeout

        # NOTE: I DON'T KNOW HOW TIMEOUT WORKS VERY WELL YET
        print(f"Server started on {self.host}:{self.port}")  # ?DEBUG?

        # start lobby
        self.rooms['lobby'] = {
            'room_number': 'lobby',
            'room_queue': queue.Queue(),
        }
        threading.Thread(
            target=self.run_lobby,
            args=(self.rooms['lobby'],),
            daemon=True,
        ).start()

        try:
            while self.running:
                try:

                    client_socket, client_address = self.server.accept()  # accept connect socket, get the socket object, address

                    print(f"Connection established with {client_address}")  # ?DEBUG?

                    # Spin off a thread to handle the client. Make it a daemon( Daemon threads are abruptly stopped at shutdown) should't be a problem as no persisitng data????
                    threading.Thread(
                        target=self.spin_off_thread,
                        args=(client_socket, client_address),
                        daemon=True
                    ).start()

                # No connection was ready within the timeout, continue the loop
                except socket.timeout:
                    continue
        finally:
            self.shutdown()

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
                self.client_lock.acquire()
                found = None
                for name, client in self.clients.items():
                    if client.socket == client_socket:
                        found = name
                        break

                if found is not None:
                    del self.clients[found]

                if client_socket.fileno() != -1:
                    client_socket.close()

            except socket.error as e:
                # Handle the case where the socket is already closed or in a bad state
                print(f"Socket error when closing client {client_address}: {e}")
            except Exception as e:
                # Catch any other unexpected exceptions
                print(f"Unexpected error while closing socket for {client_address}: {e}")
            finally:
                self.client_lock.release()

    def handshake(self, client_socket, client_address):
        try:
            # receive the handshake header of header_size
            msg_len = get_message_len(client_socket.recv(MAX_MSG_BYTES))
            msg = get_message(client_socket.recv(msg_len))

            # Ensure we receive the handshake message
            if msg.header.opcode is not Operation.HELLO:
                print(f"Bad handshake OPCODE from {client_address}")  # ? DEBUG ?
                return None

            print("DEBUG: waiting to receive nickname message")
            # Receive the payload (nickname)
            nickname = msg.payload
            print(f"DEBUG: Nickname {nickname}")
            return getattr(self, server_action_map[msg.header.opcode])(
                message=msg,
                client_socket=client_socket,
                client_address=client_address
            )
        except Exception as e:
            print(f"Handshake error with {client_address}: {e}")
            opcode = e.error if isinstance(e, ErrorException) else Error.INVALID_HELLO
            message = "INVALID HELLO: CONNECTION TERMINATED"
            serialized_len, serialized_message = Message(opcode, message).serialize()
            client_socket.sendall(serialized_len)
            client_socket.sendall(serialized_message)
            return None

    def business(self, client: ServerClient):
        while self.running:
            try:
                message = client.recv_from_client()
                # Ensure we receive the handshake message
                if message.header.opcode not in Operation or message.header.opcode is Operation.HELLO:
                    raise Error.INVALID_OPCODE
                getattr(self, server_action_map[message.header.opcode])(message=message, client=client)
            except socket.timeout:
                # timeout message
                print(f"Business timeout with {client.nickname} at {client.socket}")
            except NonFatalErrorException as e:
                # TODO: Probably want to send the original message back in payload
                serialized_len, serialized_message = Message(e.error, 'INVALID OPERATION').serialize()
                print('non fatal error', e)
                client.send_to_client(serialized_len, serialized_message)
            except ErrorException as e:
                # TODO: Probably want to send the original message back in payload
                serialized_len, serialized_message = Message(e.error, 'FATAL ERROR: CONNECTION TERMINATED').serialize()
                client.send_to_client(serialized_len, serialized_message)
                return
            except Exception as e:
                # TODO: Probably want to send the original message back in payload
                print(f"Communication error with {client.nickname} at {client.client_address}: {e}")
                serialized_header, serialized_message = Message(
                    Error.GEN_ERROR,
                    'FATAL ERROR: CONNECTION TERMINATED'
                ).serialize()
                client.send_to_client(serialized_header, serialized_message)
                return
    # stop time
    def stop(self):
        print("Stopping server...")
        self.running = False

    # Resources cleanup &  Close all connections
    def shutdown(self):

        print("Shutting down server...")  # ? DEBUG ?
        if self.server:
            self.server.close()

        # #TODO: this isn't gonna work
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
