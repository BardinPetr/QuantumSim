from src.Crypto import Crypto
from src.KeyManager import KeyManager
from src.msgs.Message import Message
from src.utils.DistributedLock import LockClient

from queue import Queue


class ConnectionManager:
    def __init__(self, key_manager: KeyManager, dlmc: LockClient):
        self.km = key_manager
        self.crypt = Crypto(self.km)
        self.dlmc = dlmc

        self.send_queue = Queue()
        self.postponed_queue = Queue()

    def pop_outgoing_msg(self):
        if not self.send_queue.empty():
            return self.send_queue.get()
        return None

    def push_outgoing_msg(self, msg: Message):
        self.send_queue.put(msg)

    def process_msg(self, header, msg):
        pass
