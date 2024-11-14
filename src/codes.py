from enum import Enum



class Operation(Enum):
    HELLO = 1
    CREATE_ROOM = 2
    LIST_ROOMS = 3
    JOIN_ROOM = 4
    LEAVE_ROOM = 5
    LIST_MEM = 6
    SEND_MSG = 7
    BROADCAST_MSG = 8
    TERMINATE = 9
    PRIVATE_MSG = 10
    FORWARD_MSG = 11
    SEND_FILE = 12
    FORWARD_FILE = 13
    PING = 14



class Operation(Enum):
    CRASH = -1
    MAX_USERS = -2
    TAKEN_NAME = -3
    CHECKSUM_FAIL = -4
    MAX_REQESTS = -5
    MSG_FAILED = -5
    MSG_REJECTED = -6

