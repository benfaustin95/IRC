import socket
from functions import *
from codes import *
from message import MAX_MSG_BYTES, get_message
from enrycpt import Private_Message

import os
import curses
from gui import Gui
import time

MAX_INT = 2 ** 31 - 1
SCREEN_REFRESH_RATE = 0.01


help_msg = """

/create_room        integer      This command requires an integer argument between 1 and 12 to request the server to create a room.
/join_room          integer      This command requires an integer argument between 1 and 12 to join an existing room on the server.
/leave_room         integer      This command requires an integer argument between 1 and 12 to leave a specified room.
/send_msg           string       This command requires an alphanumeric string argument to send a message to the current room.
/broadcast_msg      string       This command requires an alphanumeric string argument to broadcast a message to all connected users.
/private_msg        string       This command requires an alphanumeric string argument to send a private message to another user.
/send_file          file path    This command requires a file path as an argument to send a file to the server or other users.
/list_rooms         None         This command does not require any argument and lists all available rooms on the server.
/list_members       None         This command does not require any argument and lists all members in the current room.
/logout             None         This command does not require any argument and logs you out of the server.
/help               None         This command does not require any argument and provides a list of available commands.

"""

class Client:

    def __init__(self, max_rooms):
        self.max_rooms = max_rooms
        self.server_rooms = []
        self.server_host = 'localhost'
        self.server_port = 49152  # ephemeral port range - dynamic,temp connections used for client application, safe w/o conflicting service on system

        self.incoming_msg_queue = []
        self.outgoing_msg_queue = []
        self.running = False

        self.gui = None
        self.incoming_lock = threading.Lock()
        self.outgoing_lock = threading.Lock()

        self.server_socket = None

        self.user = None

        # TODO: add stubs, uncomment
        # self.command_map = {
        #     "/create_room": self.create_room,
        #     "/list_rooms": self.list_rooms,
        #     "/join_room": self.join_room,
        #     "/leave_room": self.leave_room,
        #     "/list_members": self.list_members,
        #     "/private_msg": self.private_msg,
        #     "/send_file": self.send_file,
        #     "/ping": self.ping
        # }

        # ! temp map for testing
        self.command_map = {
            "/list_rooms": self.list_rooms,
            "/join_room": self.join_room,
            "/create_room": self.create_room,
            "/send_msg": self.send_msg_command,
            "/broadcast_msg": self.broadcast_msg,
            "/leave_room": self.leave_room,
            "/list_members": self.list_members,
            "/private_msg": self.private_msg,
        }

    # ? Do we need this?
    def __del__(self):
        pass

    def listen(self, server_socket):
        while self.running:
            try:
                msg_obj = self.recv_msg()

                if msg_obj.header.opcode in NonFatalErrors:
                    # might want to add a mapping of error code to display message
                    self.print_client(f'Non Fatal Error: {msg_obj.header.opcode}, {msg_obj.payload}')
                    return None
                elif msg_obj.header.opcode in Error:
                    self.print_client(f'Fatal Error: {msg_obj.header.opcode}')
                    return None
                if msg_obj.header.opcode not in Operation:
                    self.print_client(f"Bad handshake OPCODE from {self.server_host}")
                    return None

                msg = f'{msg_obj.header.opcode}: {msg_obj.payload}'

                if msg_obj.header.opcode == Operation.PRIVATE_MSG:
                    private_msg = Private_Message(None,None)
                    private_msg.set_data(msg_obj)
                    msg = f'{private_msg.header.opcode}: {{{private_msg.decrypt_data()}}}'


                self.print_client(msg)

            except Exception as e:
                self.print_client(f"Exception in Client().listen(): {e}")
                time.sleep(10)  # ! Sleeps are just to give enough time for the gui to print an error before exiting and setting self.running
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
        attempted_usernames = []
        while True:
            try:
                user_name = self.get_username(attempted_usernames)
                msg = Message(Operation.HELLO, user_name)
                self.send_msg(msg)
                msg_obj = self.recv_msg()
                print(f"Received: {msg_obj.payload}")

                # ? Worth using a map here for only a few options?
                if msg_obj.header.opcode == Operation.OK:
                    print(f"{msg_obj.header.opcode}")
                    return True
                elif msg_obj.header.opcode == Error.TAKEN_NAME:
                    attempted_usernames.append(user_name)
                else:
                    raise Exception("Invalid handshake opcode from Server")

            except Exception as e:
                print(f"Handshake failed: {e}")
                self.running = False
                return False

    def recv_msg(self):
        msg_len = self.server_socket.recv(MAX_MSG_BYTES)
        msg_len = int.from_bytes(msg_len, byteorder='big')
        print(f"MSG LEN: {msg_len}")

        msg_obj = get_message(self.server_socket.recv(msg_len))
        return msg_obj

    def send_msg(self, msg):
        msg_len, p_msg = msg.serialize()
        self.server_socket.sendall(msg_len)
        self.server_socket.sendall(p_msg)

    def get_username(self, attempted_usernames):
        while self.running:
            user_name = input("Enter an alphanumeric username: ").strip()
            if (user_name.isalnum() and user_name not in attempted_usernames):
                self.user = user_name
                return user_name
            else:
                print("Invalid Username")


    def business(self):
        self.print_client(f"~~ Welcome to the Server: {self.user} ~~")
        while(self.running):
            try:
                if (self.outgoing_msg_queue):
                    with self.outgoing_lock:
                        msg = self.outgoing_msg_queue.pop(0)
                        self.send_msg(msg)
            except Exception as e:
                self.print_client(f"Error: {e}")
                time.sleep(10)
                print(f"Error: {e}")
                self.running = False
                self.gui.exit()


    def start(self):
        self.running = self.connect_to_server()

        if (self.running):
            handshake_result = self.handshake()
            if (handshake_result):
                listening_thread = threading.Thread(target=self.listen, args=(self.server_socket, ), daemon=True)
                listening_thread.start()

                gui_thread = threading.Thread(target=curses.wrapper, args=(self.run_gui,), daemon=True)
                gui_thread.start()

                self.business()
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
        try:
            with self.incoming_lock:
                while self.incoming_msg_queue:
                    msg = self.incoming_msg_queue.pop(0)
                    self.gui.output_window.addstr(msg + "\n")
            self.gui.output_window.refresh()
        except curses.error as e:
            self.print_client(f"Curses error in load_messages : {e}")


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
                        if (user_input.strip().lower() == "/logout"):
                            msg = Message(Operation.TERMINATE, "TERMINATE")
                            with self.outgoing_lock:
                                self.outgoing_msg_queue.insert(0, msg)
                            break
                        #! The verify command function scares me
                        result, command, argument = self.verify_command(user_input)
                        if(result):
                            self.execute_command(command, argument)

                    # or send message   #? What seems better, storing payloads in the outgoing queue, or full Messages objects?
                    else:
                        self.print_client('Invalid command')
                        # msg = Message(Operation.BROADCAST_MSG, user_input)
                        # self.outgoing_msg_queue.append(msg)

                    user_input = ""
                elif 0 <= ch <= 255:
                    try:
                        user_input += chr(ch)
                    except Exception as e:
                        self.print_client(f"Exception : {e}")

            time.sleep(SCREEN_REFRESH_RATE)

        self.gui.exit()
        self.running = False


    def print_client(self, msg):
        with self.incoming_lock:
            self.incoming_msg_queue.insert(0, str(msg)) # Insert at the front since client-side messages should take priority


    def test_send_file(self):
        notes_path = os.path.abspath("notes")
        codes_path = os.path.abspath("codes.py")
        rar_path = os.path.abspath("../test_archive.zip")
        self.send_file(notes_path)
        self.send_file(codes_path)
        self.send_file(rar_path)


    def execute_command(self, command, arg):
        if command == "/help":
            self.print_client(f"USER: {self.user}{help_msg}")
        elif arg:
            self.command_map[command](arg)
        else:
            self.command_map[command]()

    def verify_command(self, input_string):

        parts = input_string.split(maxsplit=1)
        command = parts[0]
        argument = parts[1] if len(parts) > 1 else None

        self.print_client(f"COMMAND: {command}")

        if command not in commands:

            self.print_client(f"!ERROR: Invalid command: {command}")
            return False, None, None

        expected_type = commands[command]

        if expected_type is None:
            return True, command, argument
        # will probably need more expansive logic as we add more complex commands
        elif isinstance(expected_type, tuple):
            try:
                arguments = argument.split(maxsplit=1)
                if len(arguments) <= 1:
                    return False, None, None
                arg_1, arg_2 = expected_type[0](arguments[0]), expected_type[1](arguments[1])
                if isinstance(arg_1, expected_type[0]) and isinstance(arg_2, expected_type[1]):
                    return True, command, (arg_1, arg_2)
                return False, None, None
            except (ValueError, TypeError):
                self.print_client(f"!ERROR: The command '{command}' expects {expected_type}.")
                return False, None, None
        elif expected_type == "file_path":
            #TODO: CUSTOM LOGIC HERE FOR VERIFICATION + FINDING PATH & UPLOAD
            if isinstance(argument, str) and len(argument) > 0:
                return (True, command, argument)
            else:
                self.print_client(f"!ERROR: The command '{command}' expects a valid file path.")
                return False, None, None

        elif expected_type == str:
            # isalnum() method returns True if all the characters are alphanumeric, meaning alphabet letter (a-z) and numbers (0-9).
            if isinstance(argument, str) and argument.isalnum():
                return True, command, argument
            else:
                self.print_client(f"!ERROR: The command '{command}' expects an alphanumeric string.")
                return False, None, None

        else:
            try:
                converted_argument = expected_type(argument)
                if isinstance(converted_argument, expected_type):

                    if(converted_argument > self.max_rooms):
                        self.print_client(f"!ERROR: The command '{command}' expects a number between 1 - {self.max_rooms}.")
                        return False, None, None
                    return True, command, converted_argument
                else:
                    self.print_client(f"!ERROR: The command '{command}' expects a number.")
                    return False, None, None
            except (ValueError, TypeError):
                self.print_client(f"!ERROR: The command '{command}' expects a number.")
                return False, None, None

    def join_room(self, arg):
        self.outgoing_msg_queue.append(Message(Operation.JOIN_ROOM, arg))

    def create_room(self, arg):
        self.outgoing_msg_queue.append(Message(Operation.CREATE_ROOM, arg))

    def send_msg_command(self, arg):
        self.outgoing_msg_queue.append(Message(Operation.SEND_MSG, {'room_number': arg[0], 'text': arg[1]}))

    def broadcast_msg(self, arg):
        self.outgoing_msg_queue.append(Message(Operation.BROADCAST_MSG, {'text': arg}))

    def leave_room(self, arg):
        self.outgoing_msg_queue.append(Message(Operation.LEAVE_ROOM, arg))

    def list_rooms(self):
        self.outgoing_msg_queue.append(Message(Operation.LIST_ROOMS, None))

    def list_members(self):
        self.outgoing_msg_queue.append(Message(Operation.LIST_MEMBERS, None))

    def private_msg(self,arg):
        self.outgoing_msg_queue.append(Private_Message(Operation.PRIVATE_MSG, {'target_user':arg[0], 'message':arg[1],'sender':self.user}))

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



if __name__ == "__main__":
    # h = Header(Operation.TERMINATE, MAX_INT)
    # print(f"Header: {h}")

    # ph = pickle.dumps(h)
    # print(f"Pickled Header: {ph}")
    # print(f"MAX (?) Pickled Header Length: {len(ph)}")

    Client(max_rooms=12).start()
