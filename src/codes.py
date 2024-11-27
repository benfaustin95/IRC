from enum import Enum


class Operation(Enum):
    OK = 0
    HELLO = 1  # Initial request sent by client to join server.
    CREATE_ROOM = 2  # The client requests to join a room on the server.
    LIST_ROOMS = 3  # The client requests to list rooms on the server.
    LIST_ROOMS_RESP = 4  # Server response from successful retrieval of rooms.
    JOIN_ROOM = 5  # The client requests to join a room on the server.
    LEAVE_ROOM = 6  # The client requests to leave a room on the server.
    LIST_MEMBERS = 7  # The client requests to list members on the server.
    LIST_MEMBERS_RESP = 8  # Server response from successful retrieval of members.
    SEND_MSG = 9  # The client requests to send a message to a specific user.
    BROADCAST_MSG = 10  # The server broadcasts a new message to all users in a chat room.
    TERMINATE = 11  # Client request to terminate connection to the server.
    PRIVATE_MSG = 12  # The client requests to send a private message to a specific user.
    FORWARD_MSG = 13  # The server forwards a private message to the recipient.
    FORWARD_MSG_Q = 14  # The server queries the client about accepting a private message.
    SEND_FILE = 15  # The client requests to send a file to the server.
    FORWARD_FILE = 16  # The server forwards a file to the recipient.
    FORWARD_FILE_Q = 17  # The server queries the client about accepting a file.
    PING = 18  # Client/Server request/response to test the connection.


class Error(Enum):
    GEN_ERROR = 1  # Sent by client and/or server when an unknown error has occurred.
    MAX_USERS = 2  # Sent by server when max user capacity has been reached.
    TAKEN_NAME = 3  # Sent by the server when a username has already been claimed.
    CHECKSUM_FAIL = 4  # Sent by client and/or server when a message payload has been corrupted in transit.
    MAX_REQUESTS = 5  # Sent by the server when a client has exceeded their rate limit.
    MSG_FAILED = 6  # Sent by the server when a valid message has failed to be fulfilled.
    MSG_REJECTED = 7  # Sent by the server when an invalid message has been identified.

class Command(Enum):
    BAD_FILE_PATH = -5
    INVALID_ARGS = -2
    NOT_COMMAND = -1
    NO_EXTRA_ARGS = 0



commands = {
        "/create_room": int,
        "/list_rooms": None,  # Can have anything
        "/join_room": int,
        "/leave_room": int,
        "/list_members": None,  # Can have anything
        "/send_msg": str,
        "/broadcast_msg": str,
        "/terminate": None,  # Can have anything
        "/private_msg": str,
        "/send_file": "file_path",  # Custom check for file path
        "/ping": None  # Can have anything
}



