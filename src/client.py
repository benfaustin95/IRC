import socket
import threading
from functions import *
from codes import Operation
from codes import *

MAX_PICKLED_HEADER_SIZE = 98
MAX_INT = 2 ** 31 - 1

# Define the Client class
class Client():

    def __init__(self, max_rooms):
        self.header_size = MAX_PICKLED_HEADER_SIZE
        self.running = True
        self.max_rooms = max_rooms
        self.server_rooms = []
        self.server_host = 'localhost'
        self.server_port = 49152  # Ephemeral port range
        self.socket_instance = None

    def listen(self):
        while self.running:
            continue
            try:

                # receive the handshake header of header_size
                header_bytes_object = self.socket_instance.recv(self.header_size)

                #load object back through pickle conversion from byte re-assembly
                header_object = pickle.loads(header_bytes_object)

                #return none if it's not a header object, handshake cannot proceed. !!! If u dont do this ur gonna love Executable malware !!!!!
                if not isinstance(header_object,Header):
                    print(f"Bad handshake object from {self.server_host}") # ? DEBUG ?
                    return None

                #Ensure we receive the handshake message
                if header_object.opcode not in Operation:
                    #send a message to the cleint indicating bad handshake
                    print(f"Bad handshake OPCODE from {self.server_host}") # ? DEBUG ?
                    return None


                # ******************************************************** #
                #TODO: Process the message (currently not printing or doing anything)
                # ******************************************************** #

            except Exception as e:
                print(f"Error in listening thread: {e}")
                self.running = False

        # Close the socket when the loop ends
        self.socket_instance.close()

    def connect_to_server(self, server_host, server_port):
        try:
            print("\n.....Attempting to connect.....")
            self.socket_instance = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket_instance.connect((server_host, server_port))
            print("\n✓ Connected to the server.")
            return True
        except socket.error as e:
            print(f"\n✗ Connection failed: {e}")
            return False

    def input_loops(self):
        user_input = input("Enter something: ")
        return self.verify_command(user_input)



    def handshake(self):

        print("\n\n\ ---in handshake --\n\n ")
        attemped_usernames = []

        while True:
            try:
                username = self.get_username(attemped_usernames)
                # Generate the header package
                header_package, pickled_msg = create_packages(username, Operation.HELLO.value, message_type="Message")
                # Send the header
                print(f"DEBUG: HEADER BYTES OBJ HANDSHAKE: {header_package}\n       MESSAGE BYTES OBJ: {pickled_msg}")
                self.socket_instance.sendall(header_package)
                self.socket_instance.sendall(pickled_msg)
                #recive if we ont get a message back that is also hello
                #if its error
                # receive the handshake header of header_size


                print(f"ABOUT TO RECEIVDE")
                header_bytes_object = self.socket_instance.recv(self.header_size)

                #NOTE: recv() returns an empty byte string when the socket is closed or there is no data left to read.
                print(f"RECV HEADER BYTES OBJ: {header_bytes_object}")

                #load object back through pickle conversion from byte re-assembly
                header_object = pickle.loads(header_bytes_object)

                print(f"Header object: {header_object}")
                print(f"Header object->opcode: {header_object.opcode}")

                #Ensure we receive the handshake message
                if header_object.opcode is  Operation.OK.value:
                    print("*Leaving Handshake processs")
                    return True
                else:
                    attemped_usernames.append(username)
                    print("*Restarting Handshake proccess")
                    continue

            except Exception as e:
                print(f"Handshake process to server failed: {e}")
                self.running = False
                return None



    def get_username(self,attempted_usernames=None):
        while True:
            username = input("Enter an alphanumeric username to connect to the server with: ").strip()

            if username.isalnum() and username  not in attempted_usernames:  # Check if the input is alphanumeric
                return username
            else:
                print("Invalid username. Please enter an alphanumeric username.")

    def busines(self):

        print("\n\n\ ---in buinesss--\n\n ")

        input_loop = True

        # User input loop
        while input_loop:

            result, command, argument = self.input_loops()
            print(f"DEBUG: result ={result}, command={command}, argument={argument}")

            if result is False:
                continue  # Invalid command, prompt again

            elif command == "/logout":
                pickled_msg = pickle.dumps("TERMINATE")
                # Generate the header package
                header_package = create_header_package(pickled_msg, Operation.TERMINATE.value)  # Assuming logout corresponds to terminating the connection

                try:
                    # Send the header
                    self.socket_instance.sendall(header_package)

                    print(f"Sent command '{command}' to the server.")
                except Exception as e:
                    print(f"Error sending data to server: {e}")
                    self.running = False
                    break

                input_loop = False
                continue

            elif command == "/help":
                self.explain_commands()
                continue

            # Create and send the packages if there is an argument to send
            if argument is not None:

                # Map the command to an operation code
                opcode = self.get_opcode_for_command(command)
                if opcode is None: # this should never happen but we will just put it
                    print("!ERROR: Unsupported operation.")
                    continue

                print(f"?DEBUG: argument={argument}, opcode={opcode}")
                header_package, pickled_msg = create_packages(argument, opcode, message_type="Message")

                #NOTE: recv() returns an empty byte string when the socket is closed or there is no data left to read.
                print(f"DEBUG: HEADER BYTES OBJ: {header_package}\n       MESSAGE BYTES OBJ: {pickled_msg}")


                try:
                    # Send the header
                    self.socket_instance.sendall(header_package)
                    # Send the message body if code is not TERMINATE
                    self.socket_instance.sendall(pickled_msg)
                    print(f"Sent command '{command}' to the server.")
                except Exception as e:
                    print(f"Error sending data to server: {e}")
                    self.running = False
                    break


    def start(self):
        input_loop = True

        #Return if cnnection unsucessful
        if self.connect_to_server(self.server_host, self.server_port) is False:
            return False


        # Start the listening thread for incoming server data
        #listening_thread = threading.Thread(target=self.listen)
        #listening_thread.start()

        hand = self.handshake()
        print(hand)

        if hand:
            print("\nFor a list of commands, type /help and press Enter")
            self.busines()

        self.stop()



    def stop(self):
        print("Logging out from the server...")
        self.running = False
        if self.socket_instance:
            try:
                self.socket_instance.shutdown(socket.SHUT_RDWR)
                self.socket_instance.close()
            except Exception as e:
                print(f"Error closing socket: {e}")
        print("Logged out.")

    def explain_commands(self):
        print(f"{'Command':<20} {'Argument Type':<20} {'Explanation'}")  # Header
        print("="*80)  # Separator for clarity

        for command, arg_type in commands.items():
            if arg_type == int:
                argument = "integer"
                if command == "/create_room":
                    explanation = "This command requires an integer argument between 1 and {self.max_rooms} to request the server to create a room."
                elif command == "/join_room":
                    explanation = "This command requires an integer argument between 1 and {self.max_rooms} to join an existing room on the server."
                elif command == "/leave_room":
                    explanation = "This command requires an integer argument between 1 and {self.max_rooms} to leave a specified room."
                else:
                    explanation = "This command requires an integer argument."
            elif arg_type == str:
                argument = "string"
                if command == "/send_msg":
                    explanation = "This command requires an alphanumeric string argument to send a message to the current room."
                elif command == "/broadcast_msg":
                    explanation = "This command requires an alphanumeric string argument to broadcast a message to all connected users."
                elif command == "/private_msg":
                    explanation = "This command requires an alphanumeric string argument to send a private message to another user."
                else:
                    explanation = "This command requires an alphanumeric string argument."
            elif arg_type == "file_path":
                argument = "file path"
                if command == "/send_file":
                    explanation = "This command requires a file path as an argument to send a file to the server or other users."
            elif arg_type is None:
                argument = "None"
                if command == "/list_rooms":
                    explanation = "This command does not require any argument and lists all available rooms on the server."
                elif command == "/list_members":
                    explanation = "This command does not require any argument and lists all members in the current room."
                elif command == "/ping":
                    explanation = "This command does not require any argument and checks if the server is reachable."
                elif command == "/logout":
                    explanation = "This command does not require any argument and logs you out of the server."
                elif command == "/help":
                    explanation = "This command does not require any argument and provides a list of available commands."
                else:
                    explanation = "This command does not require any argument."
            else:
                argument = "custom"
                explanation = "This command has a custom argument requirement."

            # Print the formatted string
            print(f"{command:<20} {argument:<20} {explanation}")


    def verify_command(self, input_string):
        parts = input_string.strip().split(maxsplit=1)
        if not parts:
            print("No command entered.")
            return (False, None, None)

        command = parts[0]
        argument = parts[1] if len(parts) > 1 else None

        if command not in commands:
            print(f"!ERROR: Invalid command: {command}")
            return (False, None, None)

        expected_type = commands[command]

        if expected_type is None:
            return (True, command, argument)

        elif expected_type == "file_path":
            # For simplicity, accept any non-empty string as a file path
            if isinstance(argument, str) and len(argument) > 0:
                return (True, command, argument)
            else:
                print(f"!ERROR: The command '{command}' expects a valid file path.")
                return (False, None, None)

        elif expected_type == str:
            if isinstance(argument, str) and argument.isalnum():
                return (True, command, argument)
            else:
                print(f"!ERROR: The command '{command}' expects an alphanumeric string.")
                return (False, None, None)

        elif expected_type == int:
            try:
                converted_argument = int(argument)
                if 1 <= converted_argument <= self.max_rooms:
                    return (True, command, converted_argument)
                else:
                    print(f"!ERROR: The command '{command}' expects a number between 1 and {self.max_rooms}.")
                    return (False, None, None)
            except (ValueError, TypeError):
                print(f"!ERROR: The command '{command}' expects an integer argument.")
                return (False, None, None)
        else:
            print(f"!ERROR: Unknown argument type for command '{command}'.")
            return (False, None, None)

    def get_opcode_for_command(self, command):
        # Mapping of commands to corresponding Operation enum values
        command_to_opcode = {
            "/create_room": Operation.CREATE_ROOM.value,
            "/list_rooms": Operation.LIST_ROOMS.value,
            "/join_room": Operation.JOIN_ROOM.value,
            "/leave_room": Operation.LEAVE_ROOM.value,
            "/list_members": Operation.LIST_MEMBERS.value,
            "/send_msg": Operation.SEND_MSG.value,
            "/broadcast_msg": Operation.BROADCAST_MSG.value,
            "/private_msg": Operation.PRIVATE_MSG.value,
            "/send_file": Operation.SEND_FILE.value,
            "/ping": Operation.PING.value,
            "/logout": Operation.TERMINATE.value,  # Assuming logout corresponds to terminating the connection
            # Add any other commands that are needed
        }

        # Return the opcode for the given command, or None if the command is not found
        return command_to_opcode.get(command, None)





if __name__ == "__main__":

    client = Client(max_rooms=12)
    # Initial Enter Screen  #
    input("...Enter to Connect..... ")    #start clienth
    client.start()



