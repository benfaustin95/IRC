import zlib




class Header:
    def __init__(self, opcode, payload_size, payload_checksum):

        self.opcode = opcode
        self.payload_size = None
        self.payload_checksum = None


    def __del__(self):

        self.opcode = None
        self.payload_size = None
        self.payload_checksum = None



class Message:

    def __init__(self, opcode, payload):

        self.payload  = self.convert_binary(payload) #Transmute the payload into binary funciton and assign
        payload_size = self.payload_size(self.payload) # calc size of payload

        self.header(opcode,payload_size) #construct header

    def __del__(self):

        self.payload  = None
        self.header = None

    def convert_binary(self, payload):
        pass

    def payload_size(self, payload):
        pass
