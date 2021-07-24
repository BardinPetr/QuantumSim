from typing import Any

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

    def __str__(self):
        return f'DISCOVER[ {self.int_ip} -> {self.connections} ]'


class ClassicMsg(MsgPayload):

    def __init__(self):
        pass

    def serialize(self) -> bytes:
        return packb([])

    @staticmethod
    def deserialize(raw: bytes):
        return DiscoverMsg(*unpackb(raw))


class CascadeMsg(MsgPayload):
    MODE_SEED = 0
    MODE_CALL = 1
    MODE_CALL_RESP = 2

    mode: int

    seed: int = None

    cur_id: int = None
    req: list[tuple[int, int]] = None

    res: list[int] = None

    def __init__(self, mode: int,
                 seed: int = None,
                 cur_id: int = None, req: list[tuple[int, int]] = None,
                 res: list[int] = None):
        self.mode = mode
        self.seed = seed
        self.cur_id = cur_id
        self.req = req
        self.res = res

    @staticmethod
    def from_seed(seed):
        return CascadeMsg(mode=CascadeMsg.MODE_SEED, seed=seed)

    @staticmethod
    def from_req(cur_id, req):
        return CascadeMsg(mode=CascadeMsg.MODE_CALL, cur_id=cur_id, req=req)

    @staticmethod
    def from_res(res):
        return CascadeMsg(mode=CascadeMsg.MODE_CALL_RESP, res=res)

    def serialize(self) -> bytes:
        if self.mode == CascadeMsg.MODE_SEED:
            data = self.seed
        elif self.mode == CascadeMsg.MODE_CALL:
            data = []
        return packb([self.mode, data])

    @staticmethod
    def deserialize(raw: bytes) -> 'CascadeMsg':
        mode, data = unpackb(raw)
        if mode == CascadeMsg.MODE_SEED:
            return


class RPCMsg(MsgPayload):
    CASCADE_SEED = 'cascade_set_seed'
    CASCADE_REQUEST = 'cascade_request'

    req_id: str
    proc_name: str
    is_req: bool
    data: Any

    def __init__(self, req_id: str, proc_name: str, is_req: bool, data: Any):
        self.req_id = req_id
        self.proc_name = proc_name
        self.is_req = is_req
        self.data = data

    def serialize(self) -> bytes:
        return packb([self.req_id, self.proc_name, self.is_req, self.data])

    @staticmethod
    def deserialize(raw: bytes):
        return RPCMsg(*unpackb(raw))


class CryptMsg(MsgPayload):
    PACKET_LENGTH = 30000

    MODE_EVT = 0
    MODE_TUN = 1
    MODE_FILE = 2

    mode: int
    crypt_start: int
    crypt_end: int
    packet_index: int
    packets_full_cnt: int
    encryptor: str
    data: bytes

    def __init__(self, mode: int,
                 crypt_start: int,
                 crypt_end: int,
                 packet_index: int,
                 packets_full_cnt: int,
                 data: bytes,
                 encryptor: str = None):
        self.mode = mode
        self.crypt_start = crypt_start
        self.crypt_end = crypt_end
        self.packet_index = packet_index
        self.packets_full_cnt = packets_full_cnt
        self.encryptor = encryptor
        self.data = data

    def serialize(self) -> bytes:
        return packb([self.mode,
                      self.crypt_start, self.crypt_end,
                      self.packet_index, self.packets_full_cnt,
                      self.data])

    @staticmethod
    def deserialize(raw: bytes):
        return CryptMsg(*unpackb(raw))

    def __str__(self):
        return f'CRYPT[ M:{self.mode} D:{self.data} ]'
