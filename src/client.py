import socket
import threading
import pickle
from functions import *
from codes import Operation
from codes import *
from message import Header

MAX_PICKLED_HEADER_SIZE = 98
MAX_INT = 2 ** 31 - 1


class Client:

    def __init__(self, max_rooms=12):
        self.header_size = MAX_PICKLED_HEADER_SIZE

        self.max_rooms = max_rooms
        self.server_rooms = []
        self.server_host = 'localhost'
        self.server_port = 49152  # ephemeral port range - dynamic,temp connections used for client application, safe w/o conflicting service on system

    def __del__(self):
        pass

    def listen(self, server_socket):
        while True:
            # receive the handshake header of header_size
            header_bytes_object = server_socket.recv(self.header_size)
            if not header_bytes_object:
                break

            # load object back through pickle conversion from byte re-assembly
            header_object = pickle.loads(header_bytes_object)

            # return none if it's not a header object, handshake cannot proceed. !!! If u dont do this ur gonna love Executable malware !!!!!
            if not isinstance(header_object, Header):
                print(f"Bad header from Server")  # ? DEBUG ?
                return None

            message_bytes_object = server_socket.recv(header_object.payload_size)
            message_object = pickle.loads(message_bytes_object)

            # Do something with the message depending on the opcode

    def start(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.connect((self.server_host, self.server_port))

        listening_thread = threading.Thread(target=self.listen, args=(server_socket,))
        listening_thread.start()

        user_input = ""
        while (user_input.lower() != "logout"):
            user_input = input("Enter something: ")
            msg = Message(Operation.SEND_MSG, {'nickname': user_input})
            pickled_msg = pickle.dumps(msg)
            handshake_header = Header(Operation.HELLO, len(pickled_msg))

            header_pickle = pickle.dumps(handshake_header)
            header_size = len(header_pickle)
            diff = MAX_PICKLED_HEADER_SIZE - header_size

            print(f"Pickled Header Len (Should be < MAX): {len(header_pickle)}")

            padding = diff * (b'\x00')
            package = header_pickle + padding
            print(f"Package Size: {len(package)}   <--- Should be MAX_PICKLED_HEADER_SIZE == 98")
            server_socket.sendall(package)
            server_socket.sendall(pickled_msg)

        print("Logging out")
        server_socket.close()

    def verify_command(self, input_string):

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
            # TODO: CUSTOME LOGIC HERE FOR VERIFICATION + FINDING PATH & UPLOAD
            if isinstance(argument, str) and len(argument) > 0:
                return (True, command, argument)
            else:
                print(f"!ERROR: The command '{command}' expects a valid file path.")
                return (False, None, None)

        elif expected_type == str:
            # isalnum() method returns True if all the characters are alphanumeric, meaning alphabet letter (a-z) and numbers (0-9).
            if isinstance(argument, str) and argument.isalnum():
                return (True, command, argument)
            else:
                print(f"!ERROR: The command '{command}' expects an alphanumeric string.")
                return (False, None, None)

        else:
            try:
                converted_argument = expected_type(argument)
                if isinstance(converted_argument, expected_type):

                    if (converted_argument > self.max_rooms):
                        print(f"!ERROR: The command '{command}' expects a number between 1 - {self.max_rooms}.")
                        return (False, None, None)
                else:
                    print(f"!ERROR: The command '{command}' expects a number.")
                    return (False, None, None)
            except (ValueError, TypeError):
                print(f"!ERROR: The command '{command}' expects a number.")
                return (False, None, None)


if __name__ == "__main__":
    h = Header(Operation.TERMINATE, MAX_INT)
    print(f"Header: {h}")

    ph = pickle.dumps(h)
    print(f"Pickled Header: {ph}")
    print(f"MAX (?) Pickled Header Length: {len(ph)}")

    Client().start()
