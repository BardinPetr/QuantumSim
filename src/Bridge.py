import logging as L
import struct
import threading
from collections import deque
from functools import reduce
from os import getcwd
from socket import create_connection, create_server
from time import sleep

import matplotlib.pyplot as plt
import networkx as nx
from pytun import TunTapDevice, IFF_TUN
from scapy.layers.inet import IP, TCP
from scapy.layers.tuntap import LinuxTunPacketInfo
from scapy.packet import Raw
from scapy.sendrecv import sniff

from src.Crypto import Crypto
from src.KeyManager import KeyManager
from src.sim.MainDevices.Eventable import Eventable
from src.utils.algebra import ip_str_to_bytes, ip_bytes_to_str

L.basicConfig(encoding='utf-8', level=L.DEBUG)


class Bridge(Eventable):
    BROADCAST_IP = '255.255.255.255'

    # (dst_ip, mode, packet index, full packets count, msg len, crypt start, crypt end, ipv4) + message
    BASE_PACKET_STRUCT = 'hHHLHH'
    DISCOVER_PACKET_STRUCT = 'B4sB%s'  # mode, int_ip, n_conns, * ([conn_ip] * n)
    HEADER_STRUCT = 'h4s4s'  # header, ip_target, ip_source

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

    EVENT_SOCKET_INCOMING = 's_inc'
    TUN_MTU = 3000
    PACKET_LENGTH = 30000
    SOCKET_MTU = 65000

    def __init__(self,
                 external_ip: str,
                 tun_ip: str, tun_netmask: str = '255.255.255.0',
                 in_port=51001, out_port=51002):
        super().__init__()

        self.cryptos = {}

        self.conn_graph = nx.Graph()
        self.conn_graph.add_node(external_ip, internal=tun_ip)

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

        self.client_conn_ip = None
        self.client_conn_port = None

        assert (self.PACKET_LENGTH + 20) < self.SOCKET_MTU
        assert (self.TUN_MTU + 20) < self.SOCKET_MTU

    def connect(self, ip, port=None):
        self.client_conn_ip = ip
        self.client_conn_port = port

        def _reconnect():
            sleep(10)
            L.error("Reconnecting....")
            self.connect(ip, port)

        try:
            conn = create_connection((ip, self.in_port if port is None else port))
        except:
            L.error("Failed to connect")
            threading.Thread(target=_reconnect, daemon=True).start()
            return

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
                self.send_crypt(ip, raw, mode=Bridge.MODE_TUN)

        self.tun_sniff = sniff(count=0, iface=self.tun.name, prn=proc)

    def __del__(self):
        self.running = False

        try:
            self.tun.down()
            self.tun.close()
        except:
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
            self.read_deque.append((ip, *self.split_message(data), from_client))

    def split_message(self, message):
        hl = struct.calcsize(self.HEADER_STRUCT)
        header_m, header_ip, header_source_ip = struct.unpack(self.HEADER_STRUCT, message[:hl])
        return header_m, ip_bytes_to_str(header_ip), ip_bytes_to_str(header_source_ip), message[hl:]

    def _process_queues(self):
        while self.running:
            try:
                self._process_incoming_packets()

                for i in range(len(self.send_deque)):
                    if self._process_outgoing_packets(i):
                        break
            except Exception as ex:
                print(ex)
            finally:
                sleep(10e-3)

    def _process_discover(self):
        while self.running:
            self.broadcast_discover()
            sleep(10)

    def _process_incoming_packets(self):
        if len(self.read_deque) == 0:
            return

        from_ip, header, target_ip, source_ip, data, is_from_client = self.read_deque[0]
        L.debug(f"RECV FROM {from_ip} SOURCE {source_ip} TARGET {target_ip} H:{header}")

        if header == Bridge.HEADER_CTRL:
            if data[0] == Bridge.LOCK_CTRL_MSG_REQUEST:  # We are going to receive message
                if self.send_lock != Bridge.LOCK_FLAG_IDLE:
                    if not is_from_client:
                        self.read_deque.popleft()
                        self.send_data(from_ip, Bridge.HEADER_CTRL, bytes([Bridge.LOCK_CTRL_MSG_REJECT]))
                        return

                    self.send_lock = Bridge.LOCK_FLAG_REJECTED

                self.send_data(from_ip, Bridge.HEADER_CTRL, bytes([Bridge.LOCK_CTRL_MSG_RESPONSE]))
                self.recv_lock = Bridge.LOCK_FLAG_LISTEN

            elif data[0] == Bridge.LOCK_CTRL_MSG_RESPONSE:  # Connection established. We are going to send message
                self.send_lock = Bridge.LOCK_FLAG_CONFIRMED

            elif data[0] == Bridge.LOCK_CTRL_MSG_REJECT:
                self.send_lock = Bridge.LOCK_FLAG_LISTEN

        elif header == self.HEADER_CRYPT:
            self.recv_lock = Bridge.LOCK_FLAG_IDLE
            if self.send_lock == Bridge.LOCK_FLAG_REJECTED:
                self.send_lock = Bridge.LOCK_FLAG_IDLE

            crypt = self.get_crypto(from_ip)
            if crypt is None:
                self.read_deque.popleft()
                return

            try:
                mode, index, pkts_len, msg_len, crypt_start, crypt_end = \
                    struct.unpack(self.BASE_PACKET_STRUCT, data[:struct.calcsize(self.BASE_PACKET_STRUCT)])
                data = data[struct.calcsize(self.BASE_PACKET_STRUCT):]
            except:
                self.read_deque.popleft()
                return

            if crypt_start != crypt_end:
                data = crypt.decrypt(data, crypt_start=crypt_start, crypt_end=crypt_end)

            # packet forwarding
            if target_ip != self.external_ip:
                self.send_crypt(
                    target_ip,
                    data,
                    mode=mode,
                    crypt_start=crypt_start,
                    crypt_end=crypt_end,
                    source_ip=source_ip
                )

            elif mode == Bridge.MODE_TUN:
                self.tun.write(data)

            elif mode == Bridge.MODE_SPLIT:
                if from_ip not in self.split_data:
                    self.split_data[from_ip] = dict()
                self.split_data[from_ip][index] = data

                if len(self.split_data[from_ip]) == pkts_len:
                    res = bytes(reduce(lambda acc, i: acc + i[1],
                                       sorted(self.split_data[from_ip].items(), key=lambda x: x[0]),
                                       bytearray()))
                    del self.split_data[from_ip]

                    self.emit(Bridge.EVENT_SOCKET_INCOMING, res[:msg_len])

        else:
            # packet forwarding
            if target_ip != self.external_ip:  # this include broadcast already
                self.send_data(target_ip, header, data, broadcast_ignore_ip=from_ip, source_ip=source_ip)

            if header == Bridge.HEADER_DISCOVER:
                n_conns = data[5]
                print(n_conns, data.hex())
                mode, int_ip, _, *conns = struct.unpack(self.DISCOVER_PACKET_STRUCT % ('4s' * n_conns), data)
                conns = [(source_ip, ip_bytes_to_str(i)) for i in conns]
                int_ip = ip_bytes_to_str(int_ip)
                self.tun_to_ext_ip[int_ip] = source_ip

                self.conn_graph.add_node(source_ip, internal=int_ip)
                self.conn_graph.add_edges_from(conns)

                nx.draw(self.conn_graph, with_labels=True)
                plt.show()

                L.debug(f"CONNECTIONS OF {source_ip} MAPPED TO {int_ip} -> {[i[1] for i in conns]}")

        self.read_deque.popleft()
        print(f"DROP {source_ip}")

    def _process_outgoing_packets(self, idx=0):
        if len(self.send_deque) == 0:
            return

        msg_target_ip, msg_header, raw_data, from_ip, source_ip = self.send_deque[idx]

        for target_ip in [msg_target_ip] if msg_target_ip != Bridge.BROADCAST_IP else self.connections.keys():
            if target_ip in [from_ip, self.external_ip]:
                continue

            header = msg_header
            data = raw_data[:]

            ip = self.next_hop(target_ip)
            if ip is None:
                self.send_deque.popleft()
                return

            # L.debug(f"NEXT HOP {target_ip} -> {ip}")

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

                    data[-1] = crypt.encrypt(data[-1], crypt_start=cs, crypt_end=ce)

                data = struct.pack(Bridge.BASE_PACKET_STRUCT, *data[:-1]) + data[-1]

                self.send_lock = Bridge.LOCK_FLAG_IDLE

            elif header == Bridge.HEADER_CTRL and data[0] == Bridge.LOCK_CTRL_MSG_REQUEST:
                self.send_lock = Bridge.LOCK_FLAG_SENT

            header = struct.pack(Bridge.HEADER_STRUCT,
                                 header, ip_str_to_bytes(msg_target_ip), ip_str_to_bytes(source_ip))

            try:
                L.debug(f"SENDING TO {target_ip} VIA {ip} MSG H:{header}")
                conn = self.connections[ip]
                conn.send(header + data)
            except OSError:
                self.connect(self.client_conn_ip, self.client_conn_port)
            except Exception as ex:
                L.warning(f"FAILED SENDING: {header} {data} {ip}")
                raise ex

        self.send_deque.popleft()
        return True

    def send_data(self, ip: str, header: int, data, broadcast_ignore_ip=None, source_ip=None):
        source_ip = source_ip if source_ip is not None else self.external_ip
        msg = (ip, header, data, broadcast_ignore_ip, source_ip)
        (self.send_deque.appendleft if Bridge.HEADER_CTRL == header else self.send_deque.append)(msg)

    def broadcast(self, header: int, data):
        self.send_data(self.BROADCAST_IP, header, data)

    def broadcast_discover(self):
        conns = [ip_str_to_bytes(i) for i in self.connections.keys()]
        print(self.connections.keys())
        self.broadcast(
            Bridge.HEADER_DISCOVER,
            struct.pack(
                Bridge.DISCOVER_PACKET_STRUCT % ('4s' * len(conns)),
                0, ip_str_to_bytes(self.tun_ip),
                len(conns), *conns
            )
        )

    def send_crypt(self, ip: str, data: bytes, mode=None, crypt_start=0, crypt_end=None, target_ip=None,
                   source_ip=None):
        crypt_end = len(data) if crypt_end is None else crypt_end
        mode = Bridge.MODE_SPLIT if mode is None else mode

        if mode == Bridge.MODE_TUN:
            self.send_data(
                ip,
                Bridge.HEADER_CRYPT,
                [mode, 0, 0, len(data), crypt_start, crypt_end, data],
                source_ip=source_ip
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
                [mode, index, len(pkts), len(data), cur_cs, cur_ce, data[start_byte:end_byte]],
                source_ip=source_ip
            )

    def get_crypto(self, ip) -> Crypto:
        return self.cryptos.get(ip, None)

    def next_hop(self, ip):
        try:
            path = nx.shortest_path(self.conn_graph, self.external_ip, ip)
            print(path)
            ip = path[1]
        except:
            pass
        if ip in self.connections.keys():
            return ip
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

    sleep(500000)

    del b0
    del b1


def main2():
    c0 = Crypto(KeyManager(directory=f'{getcwd()}/../data/alice'))

    # b0 = Bridge('192.168.1.66', '10.10.10.1', '255.255.255.0', in_port=50001)
    # b0.register_crypto('192.168.1.72', c0)
    # b0.connect('192.168.1.72', 51002)

    b0 = Bridge('192.168.8.100', '10.10.10.10', '255.255.255.0', in_port=50001)
    b0.register_crypto('192.168.8.102', c0)
    b0.connect('192.168.8.102', 51002)

    threading.Thread(target=b0.run, daemon=True).run()

    sleep(500000)

    del b0
    # del b1


if __name__ == '__main__':
    main2()
