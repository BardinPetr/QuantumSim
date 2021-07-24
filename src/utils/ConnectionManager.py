from collections import deque
from functools import reduce

from src.Crypto import Crypto
from src.KeyManager import KeyManager
from src.msgs.Message import Message
from src.msgs.Payloads import CryptMsg, MsgPayload
from src.utils.DistributedLock import LockClient


class ConnectionManager:
    def __init__(self, local_ip, peer_ip, key_manager: KeyManager, dlmc: LockClient):
        self.local_ip = local_ip
        self.peer_ip = peer_ip
        self.identity = self.gen_identity(local_ip, peer_ip)

        self.km = key_manager
        self.crypt = Crypto(self.km)
        self.dlmc = dlmc

        self.send_queue = deque()
        self.crypto_queue = deque()

        self.split_msg_buffer = dict()

    @staticmethod
    def gen_identity(ip_a: str, ip_b: str) -> str:
        return str(int.from_bytes(ip_a.encode('utf-8'), 'big') + int.from_bytes(ip_b.encode('utf-8'), 'big'))

    def release_peer(self):
        self.dlmc.release_other(self.identity, self.peer_ip)

    def pop_outgoing_msg(self):
        res = None
        if len(self.crypto_queue) > 0:
            res = self._process_out_msg(self.crypto_queue[0])
            if res is not None:
                self.crypto_queue.popleft()
                return res

        if len(self.send_queue) > 0:
            res = self._process_out_msg(self.send_queue[0])
            if res is not None:
                self.send_queue.popleft()

        return res

    def _process_out_msg(self, msg: Message):
        if msg.header_mode == Message.HEADER_CRYPT:
            acc_res = self.dlmc.acquire(self.identity, timeout=0.0001)
            if not acc_res or self.crypt.km.available() < 8 * (msg.payload.crypt_end - msg.payload.crypt_start):
                return None
            msg.payload.data = self.crypt.encrypt(msg.payload.data,
                                                  crypt_start=msg.payload.crypt_start,
                                                  crypt_end=msg.payload.crypt_end)

        return msg

    def push_outgoing_crypt_msgs(self, msgs: list[Message]):
        for i in msgs:
            self.crypto_queue.append(i)

    def push_outgoing_msg(self, msg: Message):
        self.send_queue.append(msg)

    @staticmethod
    def encrypt_prepare(mode: int, data: bytes, encryptor: str,
                        crypt_start: int = 0, crypt_end: int = None) -> list[MsgPayload]:
        crypt_end = len(data) if crypt_end is None else crypt_end

        pkts = list(enumerate(range(0, len(data), CryptMsg.PACKET_LENGTH)))
        res = []

        for (index, start_byte) in pkts:
            end_byte = start_byte + CryptMsg.PACKET_LENGTH
            cur_cs, cur_ce = 0, 0

            if crypt_start < end_byte:
                if start_byte <= crypt_start:
                    cur_cs = crypt_start - start_byte

                if crypt_end >= end_byte:
                    cur_ce = CryptMsg.PACKET_LENGTH
                    crypt_start = end_byte
                elif crypt_end > start_byte:
                    cur_ce = crypt_end - start_byte

            res.append(CryptMsg(mode, cur_cs, cur_ce, index, len(pkts), data[start_byte:end_byte], encryptor))
        return res

    def decrypt(self, msg: Message, force=False):
        msg.payload.data = self.crypt.decrypt(msg.payload.data,
                                              crypt_start=msg.payload.crypt_start,
                                              crypt_end=msg.payload.crypt_end)
        self.release_peer()

        payload: CryptMsg = msg.payload

        self.split_msg_buffer[payload.packet_index] = payload.data

        if force or len(self.split_msg_buffer) == payload.packets_full_cnt:
            res = bytes(reduce(lambda acc, i: acc + i[1],
                               sorted(self.split_msg_buffer.items(), key=lambda x: x[0]),
                               bytearray()))
            self.split_msg_buffer = dict()
            msg.payload.data = res
            return res, msg
        return None
