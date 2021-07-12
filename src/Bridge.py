from socket import create_server, create_connection

from pytun import TunTapDevice, IFF_TUN


class Bridge:
    connections = dict()
    running = False
    mtu = 1500

    def __int__(self, crypto, tunnel, key_manager, in_port=51001, out_port=51002):
        self.crypto = crypto
        self.tunnel = tunnel
        self.key_manager = key_manager

        self.tun = TunTapDevice(flags=IFF_TUN)
        self.server_sock = create_server(("", in_port))
        self.client_sock = None
        self.out_port = out_port

    def connect(self, ip):
        self.out_sock = create_connection((ip, self.out_port))

    def tun_up(self, ip, netmask='255.255.255.0'):
        self.running = True
        self.tun.addr = ip
        # self.tun.dstaddr =
        self.tun.mtu = self.mtu
        self.tun.up()

    def __del__(self):
        self.tun.down()
        self.tun.close()
        self.server_sock.close()
        if self.out_sock is not None:
            self.out_sock.close()

    async def _process_incoming_sockets(self):
        pass

    async def listen_conn(self):
        while self.running:
            conn, addr = self.server_sock.accept()
            self.connections[addr] = conn

    async def _process_incoming_tunnel(self):
        while self.running:
            data = self.tun.read(self.tun.mtu)
            res = self.crypto.encrypt(data)

    async def run(self):
        # return asyncio.
        pass
