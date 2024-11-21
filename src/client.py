class Client():

    def __init__(self, socket, address, name):
        self.socket = socket
        self.address = address
        self.name = name

        self.server_rooms = []

    def __del__(self):
        pass
