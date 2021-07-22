import struct
from socket import inet_aton, inet_ntoa
from typing import Any


class Message:
    # (dst_ip, mode, packet index, full packets count, msg len, crypt start, crypt end, ipv4) + message
    STRUCT_BASE_PACKET = 'hHHLHH'
    STRUCT_DISCOVER_PACKET = 'B4sB%s'  # mode, int_ip, n_conns, * ([conn_ip] * n)
    STRUCT_HEADER = 'h4s4s'

    MODE_PLAIN = 0
    MODE_TUN = 1
    MODE_SPLIT = 2

    LOCK_CTRL_MSG_REQUEST = 0
    LOCK_CTRL_MSG_RESPONSE = 1
    LOCK_CTRL_MSG_REJECT = 2

    LOCK_FLAG_IDLE = 0
    LOCK_FLAG_SENT = 1
    LOCK_FLAG_CONFIRMED = 2
    LOCK_FLAG_LISTEN = 3
    LOCK_FLAG_REJECTED = 4
    LOCK_FLAG_GOT_REJECT = 5

    HEADER_CTRL = 0
    HEADER_CRYPT = 1
    HEADER_CLASSIC = 2
    HEADER_DISCOVER = 3

    PAYLOAD_SERIALIZERS = {

    }
    PAYLOAD_DESERIALIZERS = {

    }

    header_mode: int
    source_ip: str
    destination_ip: str
    from_ip: str
    payload: Any

    def __init__(self, header_mode: int, source_ip: str, destination_ip: str, from_ip: str, payload: Any) -> None:
        self.header_mode = header_mode
        self.source_ip = source_ip
        self.destination_ip = destination_ip
        self.from_ip = from_ip
        self.payload = payload

    def _serialize_payload(self) -> bytes:
        if self.header_mode in self.PAYLOAD_SERIALIZERS:
            return self.PAYLOAD_SERIALIZERS[self.header_mode](self.payload)
        return self.payload

    def serialize(self) -> bytes:
        header = struct.pack(
            self.STRUCT_HEADER,
            self.header_mode,
            inet_aton(self.source_ip),
            inet_aton(self.destination_ip)
        )
        return header + self._serialize_payload()

    @staticmethod
    def deserialize(raw: bytes, from_ip: str):
        hl = struct.calcsize(Message.STRUCT_HEADER)
        header_mode, source_ip, destination_ip = struct.unpack(Message.STRUCT_HEADER, raw[:hl])
        payload = Message.PAYLOAD_SERIALIZERS.get(header_mode, lambda x: x)(raw[hl:])
        return Message(header_mode, inet_ntoa(source_ip), inet_ntoa(destination_ip), from_ip, payload)

    def __str__(self):
        return f"MSG[ H{self.header_mode} ({self.source_ip}->{self.destination_ip}) {self.payload} ]"
