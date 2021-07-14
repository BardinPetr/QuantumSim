from src.sim.MainDevices.Eventable import Eventable


class ClassicChannel(Eventable):
    MODE_LOCAL = 0
    MODE_TCP_SERVER = 2
    MODE_TCP_CLIENT = 3

    EVENT_ON_RECV = 'on_receive'

    def __init__(self, mode=MODE_LOCAL):
        super().__init__()

        self.mode = mode

        if self.mode > self.MODE_LOCAL:
            raise NotImplementedError()

    def send(self, x: bytes):
        if self.mode == self.MODE_LOCAL:
            self.emit(self.EVENT_ON_RECV, x)
