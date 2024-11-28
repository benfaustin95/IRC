import pickle
from codes import NonFatalErrors, NonFatalErrorException
MAX_PICKLED_HEADER_SIZE = 200

class Header:
    def __init__(self, opcode, payload_size, ):
        self.opcode = opcode
        self.payload_size = payload_size

    def __del__(self):
        self.opcode = None
        self.payload_size = None


class Message:

    def __init__(self, opcode, payload):
        self.payload = payload
        # self.payload  = self.convert_binary(payload) #Transmute the payload into binary funciton and assign
        self.payload_size = self.size(self.payload)  # calc size of payload

        self.opcode = opcode

    def __del__(self):
        self.payload = None
        self.payload_size = None
        self.opcode = None

    def convert_binary(self, payload):
        return 1

    def size(self, payload):
        return 1


def create_packages(user_input, opcode, message_type):
    msg = None

    # Create a Message object based on the message type
    # TODO: will get more complex if we do private message child classes
    if message_type == "Message":
        msg = Message(opcode, user_input)

    # Serialize the message into a pickled object
    pickled_msg = pickle.dumps(msg)

    # Generate the header package
    header_package = create_header_package(pickled_msg, opcode)

    return header_package, pickled_msg


def create_header_package(pickled_msg, opcode):
    handshake_header = Header(opcode, len(pickled_msg))

    # Serialize the header
    header_pickle = pickle.dumps(handshake_header)
    header_size = len(header_pickle)

    # Add padding to ensure the header size matches MAX_PICKLED_HEADER_SIZE
    diff = max(0, MAX_PICKLED_HEADER_SIZE - header_size)
    padding = diff * b'\x00'

    header_package = header_pickle + padding

    return header_package


def deserialize_object(serialized_object):
    if not serialized_object:
        raise NonFatalErrorException(NonFatalErrors.INVALID_MSG_FMT)

    try:
        return pickle.loads(serialized_object)
    except pickle.UnpicklingError:
        raise NonFatalErrorException(NonFatalErrors.INVALID_MSG_FMT)


def get_headers(serialized_headers) -> Header:
    header = deserialize_object(serialized_headers)
    print(header)
    if not isinstance(header, Header):
        raise NonFatalErrorException(NonFatalErrors.INVALID_MSG_FMT)
    return header


def get_message(serialized_message) -> Message:
    message = deserialize_object(serialized_message)
    if not isinstance(message, Message):
        raise NonFatalErrorException(NonFatalErrors.INVALID_MSG_FMT)
    return message
