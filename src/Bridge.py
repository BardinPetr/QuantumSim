import threading
from collections import deque
from os import getcwd
from socket import create_connection, create_server
from time import sleep

import pyshark
import pytun
from pytun import TunTapDevice, IFF_TUN

from src.Crypto import Crypto
from src.KeyManager import KeyManager
from src.Eventable import Eventable


class Bridge(Eventable):
    LOCK_CTRL_MSG_REQUEST = 0
    LOCK_CTRL_MSG_RESPONSE = 1
    LOCK_CTRL_MSG_REJECT = 2

    LOCK_FLAG_IDLE = 0
    LOCK_FLAG_SENT = 1
    LOCK_FLAG_CONFIRMED = 2
    LOCK_FLAG_LISTEN = 3
    LOCK_FLAG_REJECTED = 4

    HEADER_LENGTH = 14
    HEADER_CTRL = b'control_header'
    HEADER_CRYPT = b'crypto__header'
    HEADER_CLASSIC = b'classic_header'

    EVENT_SOCKET_INCOMING = 's_inc'
    MTU = 3000

    def __init__(self,
                 crypto: Crypto,
                 external_ip: str,
                 tun_ip: str, tun_netmask: str = '255.255.255.0',
                 in_port=51001, out_port=51002):
        super().__init__()
        self.crypto = crypto

        self.external_ip = external_ip
        self.in_port = in_port
        self.out_port = out_port

        self.connections = dict()
        self.running = True
        self.threads = []

        self.tun = TunTapDevice(flags=IFF_TUN)
        self.tun_up(tun_ip, tun_netmask)

        self.server_sock = create_server(("0.0.0.0", self.in_port))
        self.client_sock = None

        self.read_deque = deque()
        self.send_deque = deque()

        self.send_lock = self.LOCK_FLAG_IDLE
        self.recv_lock = self.LOCK_FLAG_IDLE

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
        self.tun.mtu = self.MTU
        self.tun.up()

    def _process_incoming_tunnel(self):
        while self.running:
            data = self.tun.read(self.tun.mtu)
            cap = pyshark.InMemCapture()
            res = cap.parse_packet(data)
            # cap = pyshark.LiveCapture(interface=self.tun.name, include_raw=True, use_json=True)
            # cap.sniff(timeout=3)
            # self.send_data(..., data)
            # print(res)

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
            data = conn.recv(self.MTU)
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

    def _process_incoming_packets(self):
        if len(self.read_deque) == 0:
            return

        ip, header, data, is_from_client = self.read_deque[0]
        print(f"Received packet from {ip} with data: {data}")

        if header == Bridge.HEADER_CTRL:
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
                self.send_lock = Bridge.LOCK_FLAG_IDLE
        elif header == self.HEADER_CRYPT:
            data = self.crypto.decrypt(data)
            self.recv_lock = Bridge.LOCK_FLAG_IDLE
            if self.send_lock == Bridge.LOCK_FLAG_REJECTED:
                self.send_lock = Bridge.LOCK_FLAG_IDLE
            self.emit(Bridge.EVENT_SOCKET_INCOMING, data)

        self.read_deque.popleft()

    def _process_outgoing_packets(self):
        if len(self.send_deque) == 0:
            return

        ip, header, data = self.send_deque[0]

        if self.recv_lock == self.LOCK_FLAG_LISTEN and \
                not (header == Bridge.HEADER_CTRL and data[0] == Bridge.LOCK_CTRL_MSG_RESPONSE):
            return

        if header == Bridge.HEADER_CRYPT:
            if self.crypto.km.available() < len(data) * 8:
                print("FAILED", self.crypto.km.available(), len(data) * 8)
                return

            if self.send_lock == Bridge.LOCK_FLAG_IDLE:
                self.send_data(ip, Bridge.HEADER_CTRL, bytes([Bridge.LOCK_CTRL_MSG_REQUEST]))
                return
            elif self.send_lock in [Bridge.LOCK_FLAG_SENT, Bridge.LOCK_FLAG_REJECTED]:
                return

            data = self.crypto.encrypt(data)
            self.send_lock = Bridge.LOCK_FLAG_IDLE

        elif header == Bridge.HEADER_CTRL and data[0] == Bridge.LOCK_CTRL_MSG_REQUEST:
            self.send_lock = Bridge.LOCK_FLAG_SENT

        try:
            # print(f"SENDING packet from {ip} with data: {header} {data}")
            conn = self.connections[self.dig(ip)]
            conn.send(header + data)
        except:
            return

        self.send_deque.popleft()

    def send_data(self, ip: str, header: bytes, data: bytes):
        if Bridge.HEADER_CTRL == header:
            self.send_deque.appendleft((ip, header, data))
        else:
            self.send_deque.append((ip, header, data))

    def send_crypt(self, ip: str, data: bytes):
        self.send_data(ip, Bridge.HEADER_CRYPT, data)

    def dig(self, target_ext_ip):
        return target_ext_ip

    def run(self):
        self.threads = [threading.Thread(target=i, daemon=True) for i in [
            self._process_incoming_tunnel,
            self._process_sockets_accepts,
            self._process_queues
        ]]
        [i.start() for i in self.threads]


def main():
    c0 = Crypto(KeyManager(directory=f'{getcwd()}/../data/alice'))
    c1 = Crypto(KeyManager(directory=f'{getcwd()}/../data/bob'))

    b0 = Bridge(c0, '0.0.0.0', '10.10.10.1', in_port=51001)
    b1 = Bridge(c1, '127.0.0.1', '10.10.10.2', in_port=51002)

    b0.subscribe(Bridge.EVENT_SOCKET_INCOMING, lambda x: print("0", x))
    b1.subscribe(Bridge.EVENT_SOCKET_INCOMING, lambda x: print("1", x))

    threading.Thread(target=b0.run, daemon=True).run()
    threading.Thread(target=b1.run, daemon=True).run()

    b1.connect('0.0.0.0', 51001)
    # print(len(c0.km.key_file), c0.km.available(), c1.km.available())
    b1.send_crypt('0.0.0.0', b'code1')
    b1.send_crypt('0.0.0.0', b'code2')
    # sleep(1)
    # print(c0.km.available(), c1.km.available())
    b0.send_crypt('127.0.0.1', b'code3')
    b1.send_crypt('0.0.0.0', b'code4')
    b0.send_crypt('127.0.0.1', b'code5')
    # sleep(1)
    # print(c0.km.available(), c1.km.available())
    # sleep(1)
    # c0.km.append(np.array([0, 0, 0, 1, 1, 1, 0, 0, 0]))
    # c1.km.append(np.array([0, 0, 0, 1, 1, 1, 0, 0, 0]))

    # sleep(1)
    # print(len(c0.km.key_file), c0.km.available(), c1.km.available())

    sleep(5000)

    del b0
    del b1


if __name__ == '__main__':
    main()
