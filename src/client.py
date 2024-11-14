class Client():

    def __init__(self, socket, adress,name):

        self.sock = socket
        self.adress = adress
        self.name = name

        self.server_rooms = []


    def __del__(self):
        pass