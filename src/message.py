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

    def __init__(self, opcode, payload=None):
        self.payload = payload
        self.header = Header(opcode, self.crc32())

    def crc32(self):
        c = zlib.crc32(str(self.payload).encode("utf-8"))
        return c

    def validate_check_sum(self):
        return self.crc32() == self.header.payload_checksum

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


def get_message(serialized_message) -> Message:
    message = deserialize_object(serialized_message)
    if not isinstance(message, Message):
        raise NonFatalErrorException(NonFatalErrors.INVALID_MSG_FMT)
    if not message.validate_check_sum():
        raise NonFatalErrorException(NonFatalErrors.CORRUPTED_PAYLOAD)
    return message


def get_message_len(serialized_message_len) -> int:
    m_len = int.from_bytes(serialized_message_len, byteorder='big')
    if m_len <= 0:
        raise NonFatalErrorException(NonFatalErrors.INVALID_MSG_FMT)
    return m_len
