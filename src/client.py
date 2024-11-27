import socket
import threading
from functions import *
from codes import Operation
from codes import *

import os
import curses
import queue
from gui import Gui
import time

MAX_PICKLED_HEADER_SIZE = 98
MAX_INT = 2 ** 31 - 1
SCREEN_REFRESH_RATE = 0.01

class Client():

    def __init__(self,max_rooms):
        self.header_size = MAX_PICKLED_HEADER_SIZE

        self.max_rooms = max_rooms
        self.server_rooms = []
        self.server_host = 'localhost'
        self.server_port = 49152 #ephemeral port range - dynamic,temp connections used for client application, safe w/o conflicting service on system

        self.msg_queue = []
        self.to_send = []
        self.running = False

        self.gui = None
        self.output_lock = threading.Lock()
        self.input_lock = threading.Lock()

        self.server_socket = None

    def __del__(self):
        pass


    def listen(self, server_socket):
        while self.running:
            try:
                # receive the handshake header of header_size
                header_bytes_object = server_socket.recv(self.header_size)

                #load object back through pickle conversion from byte re-assembly
                header_object = pickle.loads(header_bytes_object)

                if not isinstance(header_object, Header):
                    self.print_client(f"Bad Handshake object from {self.server_host}")
                    return None

                if header_object.opcode not in Operation:
                    self.print_client(f"Bad handshake OPCODE from {self.server_host}")
                    return None
                
                message_bytes_object = server_socket.recv(header_object.payload_size)
                message_object = pickle.loads(message_bytes_object)
                msg = "SERVER: " + str(message_object.payload) 
                self.print_client(msg)
                #print(msg)
            
            except Exception as e:
                self.print_client(f"Exception in Client().listen(): {e}")
                time.sleep(10)
                self.running = False
                break
    
        server_socket.close()

    def connect_to_server(self):
        try:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.connect((self.server_host, self.server_port))
            self.server_socket = server_socket
            return True
        except socket.error as e:
            print(f"Connection failed: {e}")
            return False

    def handshake(self):
        print("in handshake")
        attempted_usernames = []
        while True:
            try:
                user_name = self.get_username(attempted_usernames)
                print(f"Username: {user_name}") 
                packaged_header, pickled_msg = create_packages(user_name, Operation.HELLO, message_type="Message")
                self.server_socket.sendall(packaged_header)
                self.server_socket.sendall(pickled_msg)

                header_bytes = self.server_socket.recv(self.header_size)
                header_obj = pickle.loads(header_bytes)

                print(f"HEADER: {header_obj.opcode}")

                msg_bytes = self.server_socket.recv(header_obj.payload_size)
                msg_obj = pickle.loads(msg_bytes)

                if (header_obj.opcode is Operation.OK):
                    print("Excellent")
                    print(msg_obj.payload)
                    return True 
                else:
                    attempted_usernames.append(user_name)

            except Exception as e:
                self.print_client(f"Handshake failed: {e}")
                self.running = False
                return False
    
    def get_username(self, attempted_usernames):
        while True:
            user_name = input("Enter an alphanumeric username: ").strip()
            if (user_name.isalnum() and user_name not in attempted_usernames):
                return user_name
            else:
                print("Invalid Username")


    def business(self):
        pass

    def start(self):
        self.running = self.connect_to_server()

        if (self.running):
            handshake_result = self.handshake()
            if (handshake_result):
                listening_thread = threading.Thread(target=self.listen, args=(self.server_socket, ), daemon=True)
                listening_thread.start()

                gui_thread = threading.Thread(target=curses.wrapper, args=(self.run_gui,), daemon=True)
                gui_thread.start()

                while(self.running):
                    try:
                        if (self.to_send):
                            with self.output_lock:
                                ph, pmsg = create_packages(self.to_send.pop(0), Operation.SEND_MSG, "Message")
                                self.server_socket.sendall(ph)
                                self.server_socket.sendall(pmsg)

                    
                    except Exception as e:
                        self.print_client(f"Error: {e}")
                        time.sleep(10)
                        print(f"Error: {e}")
                        self.running = False
                        self.gui.exit()
                # self.business
            else:
                print("Failed to connect")

        self.stop()
    
    def stop(self):
        self.running = False
        if self.server_socket:
            try:
                self.server_socket.shutdown(socket.SHUT_RDWR)
                self.server_socket.close()
            except Exception as e:
                print(f"Error closing Socket: {e}")
        print("Logged out...")


    def load_messages(self):
        with self.output_lock:
            while self.msg_queue:
                msg = self.msg_queue.pop(0)
                self.gui.output_window.addstr(msg + "\n")
        self.gui.output_window.refresh()


    def run_gui(self, stdscr):
        self.gui = Gui(stdscr)
        user_input = "" 
        while self.running:

            self.load_messages()    
            self.gui.update_input_window(user_input) 

            # Core input loop
            ch = stdscr.getch()
            if ch != -1:
                # Delete Logic
                if ch in (curses.KEY_BACKSPACE, 127):
                    user_input = user_input[:-1]

                # Input has been sent by user
                elif ch in (curses.KEY_ENTER, 10, 13):
                    if user_input[0] == "/":
                        command = user_input[1:]
                        self.print_client(f"Command Entered: {command}")
                        if (command.strip().lower() == "logout"):
                            break
                    # or send message
                    else:
                        self.to_send.append(user_input)
                    user_input = ""
                elif 0 <= ch <= 255:
                    try:
                        user_input += chr(ch)
                    except Exception as e:
                        self.print_client(f"Exception : {e}")

            time.sleep(SCREEN_REFRESH_RATE)
        
        self.gui.exit()
        self.running = False
    
    
#     def start(self):

# # connect_to_server
        
#         listening_thread = threading.Thread(target=self.listen, args=(server_socket,), daemon=True)
#         listening_thread.start()

#         gui_thread = threading.Thread(target=curses.wrapper, args=(self.run_gui,), daemon=True)
#         gui_thread.start()

#         self.print_client("Succesfully Connected")


#         while self.running:
#             try:
#                 # filepath = input("Enter a file: ")
#                 # file_data = self.read_file(filepath) 
#                 # msg = Message(Operation.SEND_FILE, file_data) 

#                     #server_socket.send(pickled_msg)
#                 if (self.to_send):
#                     with self.output_lock:
#                         packaged_header, pickled_msg = create_packages(self.to_send.pop(0), Operation.HELLO, "Message")
#                         # self.msg_queue.append(self.to_send.pop(0))
#                         server_socket.sendall(packaged_header)
#                         server_socket.send(pickled_msg)
#             except Exception as e:
#                 self.running = False
#                 print(f"{e}")

#         while(self.running):
#             time.sleep(1)
#         for msg in self.to_send:
#             print(msg)
#         print("Logging out")
#         self.gui.exit()
#         self.running = False
#         server_socket.close()

    def print_client(self, msg):
        with self.output_lock:
            self.msg_queue.insert(0, str(msg))

    def read_file(self, filepath):

        try:
            with open(filepath, "rb") as file:
                file_data = file.read() 
        except FileNotFoundError as e:
            print(f"{e} : {filepath}")

        return file_data
        

        # write_loc = os.path.abspath("../data/")

        # filename = os.path.basename(filepath)
        # write_loc = os.path.join(write_loc, filename)
        # print(write_loc)

        # try:
        #     with open(write_loc, "wb") as b_file:
        #         b_file.write(file_data)
        # except Exception as e:
        #     print(f"{e} : {write_loc}")
    

    def test_send_file(self):
        notes_path = os.path.abspath("notes")
        codes_path = os.path.abspath("codes.py")
        rar_path = os.path.abspath("../test_archive.zip")
        self.send_file(notes_path)
        self.send_file(codes_path)
        self.send_file(rar_path)




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
            #TODO: CUSTOM LOGIC HERE FOR VERIFICATION + FINDING PATH & UPLOAD
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
    # h = Header(Operation.TERMINATE, MAX_INT)
    # print(f"Header: {h}")

    # ph = pickle.dumps(h)
    # print(f"Pickled Header: {ph}")
    # print(f"MAX (?) Pickled Header Length: {len(ph)}")

    Client(max_rooms=12).start()
