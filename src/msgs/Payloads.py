from msgpack import packb, unpackb


class MsgPayload:
    @staticmethod
    def serialize(data) -> bytes:
        return b''

    @staticmethod
    def deserialize(raw: bytes):
        return


class DiscoverMsg(MsgPayload):
    mode: int
    int_ip: str
    connections: list[str]

    def __init__(self, mode: int, int_ip: str, conns: list[str]):
        self.mode = mode
        self.int_ip = int_ip
        self.connections = conns

    def serialize(self) -> bytes:
        return packb([self.mode, self.int_ip, self.connections])

    @staticmethod
    def deserialize(raw: bytes):
        return DiscoverMsg(*unpackb(raw))


class ClassicChannel(MsgPayload):

    def __init__(self):
        pass

    def serialize(self) -> bytes:
        return packb([])

    @staticmethod
    def deserialize(raw: bytes):
        return DiscoverMsg(*unpackb(raw))
