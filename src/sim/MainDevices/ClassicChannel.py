from src.Crypto import Crypto
from src.KeyManager import KeyManager
from src.sim.MainDevices.Eventable import Eventable


class ClassicChannel(Eventable):
    MODE_LOCAL = 0
    MODE_TCP_SERVER = 2
    MODE_TCP_CLIENT = 3

    EVENT_ON_RECV = 'on_receive'

    def __init__(self, crypto: Crypto, mode=MODE_LOCAL):
        super().__init__()

        self.mode = mode
        self.crypto = crypto

        if self.mode > self.MODE_LOCAL:
            raise NotImplementedError()

    def send(self, x: bytes):
        self._send(self.crypto.encrypt(x, psk=True))

    def _send(self, x: bytes):
        if self.mode == self.MODE_LOCAL:
            self.emit(self.EVENT_ON_RECV, self.crypto.decrypt(x, psk=True))
