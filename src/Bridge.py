import struct
import threading
from collections import deque
from functools import reduce
from os import getcwd
from socket import create_connection, create_server
from time import sleep

import pytun
from networkx import Graph
from pytun import TunTapDevice, IFF_TUN
from scapy.layers.inet import IP, TCP
from scapy.layers.tuntap import LinuxTunPacketInfo
from scapy.packet import Raw
from scapy.sendrecv import sniff

from src.Crypto import Crypto
from src.KeyManager import KeyManager
from src.sim.MainDevices.Eventable import Eventable


class Bridge(Eventable):
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

    HEADER_LENGTH = 3
    HEADER_CTRL = b'ctr'
    HEADER_CRYPT = b'cry'
    HEADER_CLASSIC = b'cls'
    HEADER_DISCOVER = b'dsc'

    EVENT_SOCKET_INCOMING = 's_inc'
    TUN_MTU = 3000
    PACKET_LENGTH = 30000
    SOCKET_MTU = 65000

    def __init__(self,
                 external_ip: str,
                 tun_ip: str, tun_netmask: str = '255.255.255.0',
                 in_port=51001, out_port=51002):
        super().__init__()

        # (mode, packet index, full packets count, msg len, crypt start, crypt end, ipv4) + message
        self.PACKET_STRUCT = 'hHHLHH'
        self.DISCOVER_PACKET_STRUCT = 'Bbbbb'

        self.cryptos = {}

        self.conn_graph = Graph()
        self.conn_graph.add_node((external_ip, None))

        self.connections = dict()
        self.tun_to_ext_ip = dict()

        self.external_ip = external_ip
        self.in_port = in_port
        self.out_port = out_port

        self.running = True
        self.threads = []

        self.tun_ip = tun_ip
        self.tun = TunTapDevice(flags=IFF_TUN)
        self.tun_up(tun_ip, tun_netmask)

        self.server_sock = create_server(("0.0.0.0", self.in_port))
        self.client_sock = None

        self.read_deque = deque()
        self.send_deque = deque()

        self.send_lock = self.LOCK_FLAG_IDLE
        self.recv_lock = self.LOCK_FLAG_IDLE

        self.split_data = dict()
        self.split_len = dict()

        assert (self.PACKET_LENGTH + 20) < self.SOCKET_MTU
        assert (self.TUN_MTU + 20) < self.SOCKET_MTU

    def connect(self, ip, port=None):
        conn = create_connection((ip, self.in_port if port is None else port))
        self.connections[ip] = conn
        self.threads.append(
            threading.Thread(target=self._process_sockets_incoming, args=(ip, conn, False), daemon=True)
        )
        self.threads[-1].start()

    def tun_up(self, ip, netmask):
        self.tun.addr = ip
        self.tun.netmask = netmask
        self.tun.mtu = self.TUN_MTU
        self.tun.up()

    def register_crypto(self, ip, crypto):
        self.cryptos[ip] = crypto

    def _process_incoming_tunnel(self):
        def proc(x):
            if x.haslayer(TCP):
                ip = self.tun_to_ext_ip.get(x.getlayer(IP).dst, None)
                if ip is None:
                    return
                raw = (LinuxTunPacketInfo() / x).convert_to(Raw).load
                print(ip, x.summary(), raw)
                self.send_crypt(ip, raw, mode=Bridge.MODE_TUN)

        self.tun_sniff = sniff(count=0, iface=self.tun.name, prn=proc)

    def __del__(self):
        self.running = False

        try:
            self.tun.down()
            self.tun.close()
        except pytun.Error:
            pass

        for i in self.connections.values():
            try:
                i.close()
            except:
                pass
        if self.server_sock is not None:
            self.server_sock.close()

    def _process_sockets_accepts(self):
        while self.running:
            conn, addr = self.server_sock.accept()
            self.connections[addr[0]] = conn
            self.threads.append(
                threading.Thread(target=self._process_sockets_incoming, args=(addr[0], conn, True), daemon=True)
            )
            self.threads[-1].start()

    def _process_sockets_incoming(self, ip, conn, from_client):
        while self.running:
            data = conn.recv(self.SOCKET_MTU)
            if not data:
                break
            self.read_deque.append((ip, *Bridge.split_message(data), from_client))

    @staticmethod
    def split_message(message):
        return message[:Bridge.HEADER_LENGTH], message[Bridge.HEADER_LENGTH:]

    def _process_queues(self):
        while self.running:
            self._process_incoming_packets()
            self._process_outgoing_packets()

            sleep(10e-3)

    def _process_discover(self):
        while self.running:
            self.broadcast_ip()
            sleep(10)

    def _process_incoming_packets(self):
        if len(self.read_deque) == 0:
            return

        ip, header, data, is_from_client = self.read_deque[0]
        # print(f"RECV {header} from {ip} with data: {data}...")

        if header == Bridge.HEADER_DISCOVER:
            data = struct.unpack(self.DISCOVER_PACKET_STRUCT, data)
            tun_ip = '.'.join([str(i) for i in data[1:]])
            self.tun_to_ext_ip[tun_ip] = ip
        elif header == Bridge.HEADER_CTRL:
            if data[0] == Bridge.LOCK_CTRL_MSG_REQUEST:  # We are going to receive message
                if self.send_lock != Bridge.LOCK_FLAG_IDLE:
                    if not is_from_client:
                        self.read_deque.popleft()
                        self.send_data(ip, Bridge.HEADER_CTRL, bytes([Bridge.LOCK_CTRL_MSG_REJECT]))
                        return

                    self.send_lock = Bridge.LOCK_FLAG_REJECTED

                self.send_data(ip, Bridge.HEADER_CTRL, bytes([Bridge.LOCK_CTRL_MSG_RESPONSE]))
                self.recv_lock = Bridge.LOCK_FLAG_LISTEN

            elif data[0] == Bridge.LOCK_CTRL_MSG_RESPONSE:  # Connection established. We are going to send message
                self.send_lock = Bridge.LOCK_FLAG_CONFIRMED

            elif data[0] == Bridge.LOCK_CTRL_MSG_REJECT:
                self.send_lock = Bridge.LOCK_FLAG_LISTEN

        elif header == self.HEADER_CRYPT:
            self.recv_lock = Bridge.LOCK_FLAG_IDLE
            if self.send_lock == Bridge.LOCK_FLAG_REJECTED:
                self.send_lock = Bridge.LOCK_FLAG_IDLE

            crypt = self.get_crypto(ip)
            if crypt is None:
                self.read_deque.popleft()
                return

            # print(f"PKT {header}@{0} from {ip} with data: {data}...")

            try:
                mode, index, pkts_len, msg_len, crypt_start, crypt_end = \
                    struct.unpack(self.PACKET_STRUCT, data[:struct.calcsize(self.PACKET_STRUCT)])
                data = data[struct.calcsize(self.PACKET_STRUCT):]
            except:
                self.read_deque.popleft()
                return

            if crypt_start != crypt_end:
                data = crypt.decrypt(data, crypt_start=crypt_start, crypt_end=crypt_end)

            if mode == Bridge.MODE_TUN:
                # print(data)
                self.tun.write(data)

            if mode == Bridge.MODE_SPLIT:
                if ip not in self.split_data:
                    self.split_data[ip] = dict()
                self.split_data[ip][index] = data

                if len(self.split_data[ip]) == pkts_len:
                    res = bytes(reduce(lambda acc, i: acc + i[1],
                                       sorted(self.split_data[ip].items(), key=lambda x: x[0]),
                                       bytearray()))
                    del self.split_data[ip]
                    self.emit(Bridge.EVENT_SOCKET_INCOMING, res[:msg_len])

        self.read_deque.popleft()

    def _process_outgoing_packets(self, idx=0):
        if len(self.send_deque) == 0:
            return

        ip, header, data = self.send_deque[idx]

        ip = self.next_hop(ip)

        if self.recv_lock == self.LOCK_FLAG_LISTEN and \
                not (header == Bridge.HEADER_CTRL and data[0] == Bridge.LOCK_CTRL_MSG_RESPONSE):
            return

        if header == Bridge.HEADER_CRYPT:
            if self.send_lock == Bridge.LOCK_FLAG_IDLE:
                self.send_data(ip, Bridge.HEADER_CTRL, bytes([Bridge.LOCK_CTRL_MSG_REQUEST]))
                return
            elif self.send_lock in [Bridge.LOCK_FLAG_SENT, Bridge.LOCK_FLAG_REJECTED]:
                return

            cs, ce = data[4], data[5]

            if cs != ce:
                crypt = self.get_crypto(ip)
                if crypt is None:
                    return

                if crypt.km.available() < (ce - cs) * 8:
                    return

                data[6] = crypt.encrypt(data[6], crypt_start=cs, crypt_end=ce)

            data = struct.pack(self.PACKET_STRUCT, *data[:-1]) + data[6]

            self.send_lock = Bridge.LOCK_FLAG_IDLE

        elif header == Bridge.HEADER_CTRL and data[0] == Bridge.LOCK_CTRL_MSG_REQUEST:
            self.send_lock = Bridge.LOCK_FLAG_SENT

        try:
            conn = self.connections[ip]
            conn.send(header + data)
            # print(f"SENDING: {header} {data} {ip}")
        except:
            print(f"FAILED SENDING: {header} {data} {ip}")

        self.send_deque.popleft()

    def send_data(self, ip: str, header: bytes, data):
        if Bridge.HEADER_CTRL == header:
            self.send_deque.appendleft((ip, header, data))
        else:
            self.send_deque.append((ip, header, data))

    def broadcast(self, header: bytes, data: bytes):
        for i in self.connections.keys():
            self.send_data(i, header, data)

    def broadcast_ip(self):
        self.broadcast(Bridge.HEADER_DISCOVER,
                       struct.pack(self.DISCOVER_PACKET_STRUCT, 0, *map(int, self.tun_ip.split('.'))))

    def send_crypt(self, ip: str, data: bytes, mode=None, crypt_start=0, crypt_end=None):
        crypt_end = len(data) if crypt_end is None else crypt_end
        mode = Bridge.MODE_SPLIT if mode is None else mode

        if mode == Bridge.MODE_TUN:
            self.send_data(
                ip,
                Bridge.HEADER_CRYPT,
                [mode, 0, 0, len(data), crypt_start, crypt_end, data]
            )
            return

        pkts = list(enumerate(range(0, len(data), self.PACKET_LENGTH)))

        for (index, start_byte) in pkts:
            end_byte = start_byte + self.PACKET_LENGTH
            cur_cs, cur_ce = 0, 0

            if crypt_start < end_byte:
                if start_byte <= crypt_start:
                    cur_cs = crypt_start - start_byte

                if crypt_end >= end_byte:
                    cur_ce = self.PACKET_LENGTH
                    crypt_start = end_byte
                elif crypt_end > start_byte:
                    cur_ce = crypt_end - start_byte

            self.send_data(
                ip,
                Bridge.HEADER_CRYPT,
                [mode, index, len(pkts), len(data), cur_cs, cur_ce, data[start_byte:end_byte]]
            )

    def get_crypto(self, ip) -> Crypto:
        return self.cryptos.get(ip, None)

    def next_hop(self, target_ext_ip):
        if target_ext_ip in self.connections.keys():
            return target_ext_ip
        return None

    def run(self):
        self.threads = [threading.Thread(target=i, daemon=True) for i in [
            self._process_incoming_tunnel,
            self._process_sockets_accepts,
            self._process_queues,
            self._process_discover
        ]]
        [i.start() for i in self.threads[-4:]]


def main():
    c0 = Crypto(KeyManager(directory=f'{getcwd()}/../data/alice'))
    b0 = Bridge('0.0.0.0', '10.10.10.1', '255.255.255.0', in_port=50001)
    b0.subscribe(Bridge.EVENT_SOCKET_INCOMING, lambda x: print("0", x))
    b0.register_crypto('127.0.0.1', c0)

    c1 = Crypto(KeyManager(directory=f'{getcwd()}/../data/bob'))
    b1 = Bridge('127.0.0.1', '10.10.10.2', '255.255.255.0', in_port=50002)
    b1.subscribe(Bridge.EVENT_SOCKET_INCOMING, lambda x: print("1", x))
    b1.register_crypto('0.0.0.0', c1)

    b1.connect('0.0.0.0', 50001)

    b0.send_crypt('127.0.0.1',
                  ''.join([chr(i) for i in range(ord('a'), ord('z') + 1)]).encode('utf-8'),
                  crypt_start=5, crypt_end=13)

    threading.Thread(target=b0.run, daemon=True).start()
    threading.Thread(target=b1.run, daemon=True).start()

    # sleep(2)
    # print(b0.connections)
    # print(b1.connections)

    # b1.send_crypt('0.0.0.0', b'code1')
    # b1.send_crypt('0.0.0.0', b'code2')
    # b0.send_crypt('127.0.0.1', b'code3')
    # b1.send_crypt('0.0.0.0', b'code4')
    # b0.send_crypt('127.0.0.1', b'code5')

    sleep(500000)

    del b0
    del b1


def main2():
    c0 = Crypto(KeyManager(directory=f'{getcwd()}/../data/alice'))
    # c1 = Crypto(KeyManager(directory=f'{getcwd()}/../data/bob'))

    b0 = Bridge('0.0.0.0', '10.10.10.1', '255.255.255.0', in_port=50001)
    # b1 = Bridge(c1, '127.0.0.1', '10.10.10.2', '255.255.255.0', in_port=51002)

    b0.register_crypto('127.0.0.1', c0)
    b0.subscribe(Bridge.EVENT_SOCKET_INCOMING, lambda x: print("0", x))
    # b1.subscribe(Bridge.EVENT_SOCKET_INCOMING, lambda x: print("1", x))
    b0.connect('127.0.0.1', 51002)

    # b0.send_crypt('127.0.0.1', b'324')

    threading.Thread(target=b0.run, daemon=True).run()
    # threading.Thread(target=b1.run, daemon=True).run()

    # b1.send_crypt('0.0.0.0', b'code1')
    # b1.send_crypt('0.0.0.0', b'code2')
    # b0.send_crypt('127.0.0.1', b'code3')
    # b1.send_crypt('0.0.0.0', b'code4')
    # b0.send_crypt('127.0.0.1', b'code5')

    sleep(500000)

    del b0
    # del b1


if __name__ == '__main__':
    main2()
