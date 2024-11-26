import socket
import threading
from functions import *
from codes import Operation
from codes import *

MAX_PICKLED_HEADER_SIZE = 98
MAX_INT = 2 ** 31 - 1

class Client():

    def __init__(self,max_rooms):
        self.header_size = MAX_PICKLED_HEADER_SIZE

        self.running = True
        self.max_rooms = max_rooms
        self.server_rooms = []
        self.server_host = 'localhost'
        self.server_port = 49152 #ephemeral port range - dynamic,temp connections used for client application, safe w/o conflicting service on system


    def __del__(self):
        pass


    def listen(self, server_socket):
        while self.running:
            try:
                # Receive the header
                header_data = self.socket_instance.recv(self.header_size)
                if not header_data:
                    break  # Server disconnected

                # Deserialize the header
                header = pickle.loads(header_data.rstrip(b'\x00'))  # Remove padding

                # Receive the message based on the length specified in the header
                msg_length = header.length
                message_data = b''
                while len(message_data) < msg_length:
                    chunk = self.socket_instance.recv(msg_length - len(message_data))
                    if not chunk:
                        break
                    message_data += chunk

                # Deserialize the message
                message = pickle.loads(message_data)

                # Process the message (currently not printing or doing anything)
                # To process and print messages from the server, you can add code here
                # For now, we are not printing server messages as per your request

            except Exception as e:
                print(f"Error in listening thread: {e}")
                self.running = False

    def connect_to_server(self, server_host, server_port):
        try:
            print("\n.....attempting to connect.....")
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.connect((server_host, server_port))
            print("\n✓ Connected to the server.")
            return server_socket
        except socket.error as e:
            print(f"\n✗ Connection failed: {e}")
            return None

    def input_loops(self):

        user_input = input("Enter something: ")

        return self.verify_command(user_input)


    def start(self):

        input_loop = True

        #attempt to connect
        socket_instance = self.connect_to_server(self.server_host, self.server_port)

        #check r-value
        if socket_instance:
            print("\n\nConnection successful!")
        else:
            print("\n\nCould not establish a connection.")
            return False
        print("\n\n?For a list of commands type /help and enter")

        #spin off listening thread
        listening_thread = threading.Thread(target=self.listen, args=(socket_instance,))
        listening_thread.start()

        #user input loop
        user_input = ""
        while input_loop  == True:
            result, command, argument = self.input_loops()

            if command == "/logout":
                input_loop = False
            #create our package/header
            #send the header
            #send bodu re[eart

        self.stop()


        #! outside of loop now we want to call stop and

    def stop(self):
        print("Loggin off from server from server...")
        #stop our socket and end the program
        self.running = False
        print("Logging out")

    def explain_commands(self):
        for command, arg_type in commands.items():
            if arg_type == int:
                print(f"{command}: This command requires an integer argument, between 1 and {self.max_rooms}.")
            elif arg_type == str:
                print(f"{command}: This command requires a string argument")
            elif arg_type == "file_path":
                print(f"{command}: This command requires a file path as an argument.")
            elif arg_type is None:
                print(f"{command}: This command does not require any specific argument.")
            else:
                print(f"{command}: This command has a custom argument requirement.")

    def verify_command(self,input_string):

        parts = input_string.split(maxsplit=1)
        command = parts[0]
        argument = parts[1] if len(parts) > 1 else None

        if command not in commands:
            print(f"!ERROR: Invalid command: {command}")
            return (False, None, None)

        expected_type = commands[command]

        if expected_type is None:
            return (True, command, argument)

        elif expected_type == "file_path":
            #TODO: CUSTOME LOGIC HERE FOR VERIFICATION + FINDING PATH & UPLOAD
            if isinstance(argument, str) and len(argument) > 0:
                return (True, command, argument)
            else:
                print(f"!ERROR: The command '{command}' expects a valid file path.")
                return (False, None, None)

        elif expected_type == str:
            #isalnum() method returns True if all the characters are alphanumeric, meaning alphabet letter (a-z) and numbers (0-9).
            if isinstance(argument, str) and argument.isalnum():
                return (True, command, argument)
            else:
                print(f"!ERROR: The command '{command}' expects an alphanumeric string.")
                return (False, None, None)

        else:
            try:
                converted_argument = expected_type(argument)
                if isinstance(converted_argument, expected_type):

                    if(converted_argument > self.max_rooms):
                        print(f"!ERROR: The command '{command}' expects a number between 1 - {self.max_rooms}.")
                        return (False, None, None)
                else:
                    print(f"!ERROR: The command '{command}' expects a number.")
                    return (False, None, None)
            except (ValueError, TypeError):
                print(f"!ERROR: The command '{command}' expects a number.")
                return (False, None, None)


if __name__ == "__main__":

    client = Client(max_rooms=12)
    # Initial Enter Screen  #
    input("Press Enter to connect to the server...")    #start client

    client.start()



