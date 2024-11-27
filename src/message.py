import zlib


class Header:
    def __init__(self, opcode, checksum):

        self.opcode = opcode
        self.payload_checksum = checksum

    def __del__(self):

        self.opcode = None
        self.payload_size = None



class Message:

    def __init__(self, opcode, payload):

        self.opcode = opcode
        self.payload = payload
        self.header = Header(self.opcode, self.crc32(payload))

    def crc32(self, payload):
        c = zlib.crc32(str(payload).encode("utf-8"))
        return c
        

    def __del__(self):

        self.payload  = None
        self.payload_size = None
        self.opcode = None

