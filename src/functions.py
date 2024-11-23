from message import Message

"""
# Action_map is a dictionary that maps the number of arguments (arg_len) to specific functions.
# This allows us to dynamically choose which function to execute based on the number of arguments.
self._default_constructor()
action_map = {
    0: lambda: self._default_constructor(),
    1: lambda: self._sftp_client_DI_constructor(*args),  # Wrap the call in a lambda to pass args
    4: lambda: self._param_constructor(*args)  # Wrap the call in a lambda to pass args
}

#Call the appropriate constructor based on match.
if opcodde in action_map:
    action_map[arg_len]()  # Now correctly passes args to _copy_constructor and _param_constructor
#Cannot find correct argument, abort instansiation.
else:
    raise ValueError("Invalid argument length when initializing SFTP build")
"""


def hello():
    print("Hello function called")  # Implement the actual logic

def createRoom():
    print("Create Room function called")  # Implement the actual logic

def listRooms():
    print("List Rooms function called")  # Implement the actual logic

def listRoomsResp():
    print("List Rooms Response function called")  # Implement the actual logic

def joinRoom():
    print("Join Room function called")  # Implement the actual logic

def leaveRoom():
    print("Leave Room function called")  # Implement the actual logic

def listMembers():
    print("List Members function called")  # Implement the actual logic

def listMembersResp():
    print("List Members Response function called")  # Implement the actual logic

def sendMsg():
    print("Send Message function called")  # Implement the actual logic

def broadcastMsg():
    print("Broadcast Message function called")  # Implement the actual logic

def terminate():
    print("Terminate function called")  # Implement the actual logic

def privateMsg():
    print("Private Message function called")  # Implement the actual logic

def forwardMsg():
    print("Forward Message function called")  # Implement the actual logic

def forwardMsgQ():
    print("Forward Message Query function called")  # Implement the actual logic

def sendFile():
    print("Send File function called")  # Implement the actual logic

def forwardFile():
    print("Forward File function called")  # Implement the actual logic

def forwardFileQ():
    print("Forward File Query function called")  # Implement the actual logic

def ping():
    print("Ping function called")  # Implement the actual logic

action_map = {
    2: createRoom,
    3: listRooms,
    4: listRoomsResp,
    5: joinRoom,
    6: leaveRoom,
    7: listMembers,
    8: listMembersResp,
    9: sendMsg,
    10: broadcastMsg,
    11:  terminate,
    12:  privateMsg,
    13:  forwardMsg,
    14:  forwardMsgQ,
    15:  sendFile,
    16:  forwardFile,
    17:  forwardFileQ,
    18:  ping,
}