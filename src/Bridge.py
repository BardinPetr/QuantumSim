import threading
from os import getcwd
from socket import create_connection, create_server
from time import sleep

import pyshark
import pytun
from pytun import TunTapDevice, IFF_TUN

from src.Crypto import Crypto
from src.KeyManager import KeyManager
from src.sim.MainDevices.Eventable import Eventable


class Bridge(Eventable):
    EVENT_SOCKET_INCOMING = 's_inc'
    MTU = 1500

    def __init__(self,
                 crypto: Crypto,
                 tun_ip: str, tun_netmask: str = '255.255.255.0',
                 in_port=51001, out_port=51002):
        super().__init__()
        self.crypto = crypto

        self.in_port = in_port
        self.out_port = out_port

        self.connections = dict()
        self.running = True
        self.threads = []

        self.tun = TunTapDevice(flags=IFF_TUN)
        self.tun_up(tun_ip, tun_netmask)

        self.server_sock = create_server(("0.0.0.0", self.in_port))
        self.client_sock = None

    def connect(self, ip, port=None):
        conn = create_connection((ip, self.in_port if port is None else port))
        self.connections[ip] = conn
        self.threads.append(
            threading.Thread(target=self._process_sockets_incoming, args=(ip, conn), daemon=True)
        )
        self.threads[-1].start()

    def tun_up(self, ip, netmask):
        self.tun.addr = ip
        self.tun.netmask = netmask
        self.tun.mtu = self.MTU
        self.tun.up()

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
                threading.Thread(target=self._process_sockets_incoming, args=(addr[0], conn), daemon=True)
            )
            self.threads[-1].start()

    def _process_sockets_incoming(self, ip, conn):
        while self.running:
            data = conn.recv(self.MTU)
            if not data:
                break
            data = self.crypto.decrypt(data)
            self.emit(Bridge.EVENT_SOCKET_INCOMING, data)
            print(f"from {ip} in {self.in_port} data {data}")

    def _process_incoming_tunnel(self):
        while self.running:
            data = self.tun.read(self.tun.mtu)
            cap = pyshark.InMemCapture()
            res = cap.parse_packet(data)
            # cap = pyshark.LiveCapture(interface=self.tun.name, include_raw=True, use_json=True)
            # cap.sniff(timeout=3)
            # self.send_data(..., data)

    def send_data(self, target_ext_ip, data):
        conn = self.connections[self.dig(target_ext_ip)]
        data = self.crypto.encrypt(data)
        conn.send(data)

    def dig(self, target_ext_ip):
        return target_ext_ip

    def run(self):
        self.threads.append(threading.Thread(target=self._process_incoming_tunnel, daemon=True))
        self.threads.append(threading.Thread(target=self._process_sockets_accepts, daemon=True))
        [i.start() for i in self.threads]


def main():
    c0 = Crypto(KeyManager(directory=f'{getcwd()}/../data/alice'))
    c1 = Crypto(KeyManager(directory=f'{getcwd()}/../data/bob'))

    b0 = Bridge(c0, '10.10.10.1', in_port=51001)
    b1 = Bridge(c1, '10.10.10.2', in_port=51002)

    threading.Thread(target=b0.run, daemon=True).run()
    threading.Thread(target=b1.run, daemon=True).run()

    b1.connect('0.0.0.0', 51001)

    b1.send_data('0.0.0.0', b'123')
    sleep(1)
    b0.send_data('127.0.0.1', b'321')
    sleep(1)

    del b0
    del b1


if __name__ == '__main__':
    main()
