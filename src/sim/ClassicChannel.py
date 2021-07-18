from src.Eventable import Eventable


class ClassicChannel(Eventable):
    EVENT_MESSAGE_INCOMING = 'message_incoming'

    def __init__(self, ip: str):
        super().__init__()

        self.ip = ip
        self.connections = {}

    def connect(self, cc):
        self.connections[cc.ip] = cc

    def send_data(self, receiver_ip: str, data: bytes):
        if receiver_ip not in self.connections.keys():
            raise Exception('This connection doesn`t exist')

        self.connections[receiver_ip].emit(ClassicChannel.EVENT_MESSAGE_INCOMING, data)
