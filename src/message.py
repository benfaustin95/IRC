import zlib


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
        #self.payload  = self.convert_binary(payload) #Transmute the payload into binary funciton and assign
        self.payload_size = self.size(self.payload) # calc size of payload

        self.opcode = opcode

    def __del__(self):

        self.payload  = None
        self.payload_size = None
        self.opcode = None

    def convert_binary(self, payload):
        return 1

    def size(self, payload):
        return 1
