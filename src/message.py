import pickle
import zlib
from codes import NonFatalErrors, NonFatalErrorException

MAX_MSG_BYTES = 4


class Header:
    def __init__(self, opcode, checksum):
        self.opcode = opcode
        self.payload_checksum = checksum

    def __del__(self):
        self.opcode = None
        self.payload_size = None


class Message:

    def __init__(self, opcode, payload):
        self.header = Header(opcode, self.crc32(payload))
        self.payload = payload

    def crc32(self, payload):
        c = zlib.crc32(str(payload).encode("utf-8"))
        return c

    def serialize(self):
        serialized_message = pickle.dumps(self)
        return len(serialized_message).to_bytes(MAX_MSG_BYTES, byteorder='big'), serialized_message

    def __del__(self):
        self.payload = None
        self.payload_size = None
        self.opcode = None


def deserialize_object(serialized_object):
    if not serialized_object:
        raise NonFatalErrorException(NonFatalErrors.INVALID_MSG_FMT)
    try:
        return pickle.loads(serialized_object)
    except pickle.UnpicklingError:
        raise NonFatalErrorException(NonFatalErrors.INVALID_MSG_FMT)

#! isinstance checks for class inheritance, so it will return True if the object is an instance of the class you specify or any subclass of it.???
def get_message(serialized_message) -> Message:
    message = deserialize_object(serialized_message)
    if not isinstance(message, Message):
        raise NonFatalErrorException(NonFatalErrors.INVALID_MSG_FMT)
    return message


def get_message_len(serialized_message_len) -> int:
    m_len = int.from_bytes(serialized_message_len, byteorder='big')
    if m_len <= 0:
        raise NonFatalErrorException(NonFatalErrors.INVALID_MSG_FMT)
    return m_len
