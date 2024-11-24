import socket
import threading
from functions import *
from codes import Operation

MAX_PICKLED_HEADER_SIZE = 98
MAX_INT = 2 ** 31 - 1

class Client():

    def __init__(self):
        self.header_size = MAX_PICKLED_HEADER_SIZE

        self.server_rooms = []
        self.server_host = 'localhost'
        self.server_port = 49152 #ephemeral port range - dynamic,temp connections used for client application, safe w/o conflicting service on system


    def __del__(self):
        pass


    def listen(self, server_socket):
        while True:
            # receive the handshake header of header_size
            header_bytes_object = server_socket.recv(self.header_size)
            if not header_bytes_object:
                break

            #load object back through pickle conversion from byte re-assembly
            header_object = pickle.loads(header_bytes_object)

            #return none if it's not a header object, handshake cannot proceed. !!! If u dont do this ur gonna love Executable malware !!!!!
            if not isinstance(header_object,Header):
                print(f"Bad header from Server") # ? DEBUG ?
                return None

            message_bytes_object = server_socket.recv(header_object.payload_size)
            message_object= pickle.loads(message_bytes_object)

            # Do something with the message depending on the opcode

    def start(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.connect((self.server_host, self.server_port))
        
        listening_thread = threading.Thread(target=self.listen, args=(server_socket,))
        listening_thread.start()

        user_input = ""
        while(user_input.lower() != "logout"):
            user_input = input("Enter something: ")
            msg = Message(Operation.SEND_MSG, user_input) 
            pickled_input = pickle.dumps(user_input) 
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

            server_socket.send(pickled_msg)

        print("Logging out")
        server_socket.close()


if __name__ == "__main__":
    h = Header(Operation.TERMINATE, MAX_INT)
    print(f"Header: {h}")

    ph = pickle.dumps(h)
    print(f"Pickled Header: {ph}")
    print(f"MAX (?) Pickled Header Length: {len(ph)}")

    Client().start()