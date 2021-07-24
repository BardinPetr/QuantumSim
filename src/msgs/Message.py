from typing import Any, Optional

from msgpack import packb, unpackb

from src.msgs.Payloads import DiscoverMsg, MsgPayload, CryptMsg, RPCMsg


class Message:
    MSG_BEGIN = b'msg_bgn'
    MSG_END = b'msg_end'

    HEADER_CTRL = 0
    HEADER_CRYPT = 1
    HEADER_RPC = 2
    HEADER_DISCOVER = 3

    PAYLOAD_CLASSES: dict[int, MsgPayload] = {
        HEADER_DISCOVER: DiscoverMsg,
        HEADER_RPC:      RPCMsg,
        HEADER_CRYPT:    CryptMsg,
    }

    header_mode: int
    source_ip: str
    destination_ip: str
    from_ip: str
    payload: Any

    def __init__(self, header_mode: int, source_ip: str, destination_ip: str, from_ip: str, payload: Any) -> None:
        self.from_ip = from_ip
        self.header_mode = header_mode
        self.source_ip = source_ip
        self.destination_ip = destination_ip
        self.payload = payload

    def _serialize_payload(self) -> bytes:
        if self.header_mode in Message.PAYLOAD_CLASSES:
            return Message.PAYLOAD_CLASSES[self.header_mode].serialize(self.payload)
        return self.payload

    def serialize(self) -> bytes:
        return packb([
            self.header_mode,
            self.source_ip,
            self.destination_ip,
            self._serialize_payload()
        ])

    @staticmethod
    def deserialize(raw: bytes, from_ip: str) -> Optional['Message']:
        try:
            mode, s_ip, d_ip, payload = unpackb(raw)
            if mode in Message.PAYLOAD_CLASSES:
                payload = Message.PAYLOAD_CLASSES[mode].deserialize(payload)
            return Message(mode, s_ip, d_ip, from_ip, payload)
        except:
            return None

    def __str__(self):
        return f"MSG[ H{self.header_mode} (S{self.source_ip}->(F{self.from_ip})->D{self.destination_ip}) {self.payload} ]"
