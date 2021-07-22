import logging as L
import threading
from os import getcwd
from socket import create_connection, create_server, socket
from time import sleep
from typing import Optional

import networkx as nx
from pytun import TunTapDevice, IFF_TUN
from scapy.layers.inet import IP, TCP
from scapy.layers.tuntap import LinuxTunPacketInfo
from scapy.packet import Raw
from scapy.sendrecv import sniff

from src.KeyManager import KeyManager
from src.Message import Message
from src.sim.MainDevices.Eventable import Eventable
from src.utils.ConnectionManager import ConnectionManager
from src.utils.DistributedLock import LockServer, LockClient

L.basicConfig(encoding='utf-8', level=L.DEBUG)

import selectors


class Bridge(Eventable):
    EVENT_SOCKET_INCOMING = 's_inc'
    EVENT_INCOMING_WAVES = 'waves'

    USER_ALICE = 0
    USER_BOB = 1

    BROADCAST_IP = '255.255.255.255'

    TUN_MTU = 3000
    PACKET_LENGTH = 30000
    SOCKET_MTU = 65000

    def __init__(self,
                 ext_ip: str,
                 tun_ip: str, tun_netmask: str = '255.255.255.0',
                 data_port=58001, wave_port=58002,
                 dlm_ports=(58003, 58004),
                 user_mode=USER_ALICE):
        super().__init__()

        self.threads = []
        self.sockets = []
        self.running = True
        self.wave_conn = None
        self.data_conn = None

        self.ext_ip = ext_ip
        self.user_mode = user_mode
        self.data_port = data_port
        self.wave_port = wave_port

        self.tun_ip = tun_ip
        self.tun = TunTapDevice(flags=IFF_TUN)
        self.tun_up(tun_ip, tun_netmask)

        self.dlm_server = None
        self.dlm_ports = dlm_ports
        if user_mode == Bridge.USER_BOB:
            self.dlm_server = LockServer(*dlm_ports)

        self.server_sock_d = create_server(("0.0.0.0", data_port))
        self.server_sock_d.setblocking(False)
        self.server_sock_w = create_server(("0.0.0.0", wave_port))

        self.selector = selectors.DefaultSelector()
        self.selector.register(self.server_sock_d, selectors.EVENT_READ,
                               lambda *args: self._process_accept_socket(*args, sock_name='socket_d'))
        self.selector.register(self.server_sock_w, selectors.EVENT_READ,
                               lambda *args: self._process_accept_socket(*args, sock_name='socket_w'))

        # node name->ext_ip, params->{'ext_ip', 'int_ip', 'socket', 'socket_w', 'manager'}
        self.conn_graph = nx.Graph()

        self.conn_graph.add_node(ext_ip, int_ip=tun_ip)

        assert (self.PACKET_LENGTH + 20) < self.SOCKET_MTU
        assert (self.TUN_MTU + 20) < self.SOCKET_MTU

    def connect(self, ip: str, key_manager: KeyManager, d_port=None, w_port=None):
        self.data_conn = create_connection((ip, self.data_port if d_port is None else d_port))
        self.wave_conn = create_connection((ip, self.wave_port if w_port is None else w_port))
        self.register_connection(ip, key_manager, self.data_conn, self.wave_conn)

    def register_connection(self, ext_ip: str,
                            key_manager: KeyManager = None,
                            socket_d: socket = None, socket_w: socket = None):
        if key_manager is not None:
            dlmc = LockClient((ext_ip if self.user_mode == Bridge.USER_ALICE else self.ext_ip), *self.dlm_ports)
            self.conn_graph.add_node(
                ext_ip,
                int_ip=None,
                ext_ip=ext_ip,
                socket_d=socket_d,
                socket_w=socket_w,
                manager=ConnectionManager(key_manager, dlmc)
            )
        if socket_d is not None:
            socket_d.setblocking(False)
            self.conn_graph.nodes[ext_ip]['socket_d'] = socket_d
            self.selector.register(socket_d, selectors.EVENT_READ | selectors.EVENT_WRITE,
                                   self._process_socket)

        if socket_w is not None:
            self.conn_graph.nodes[ext_ip]['socket_w'] = socket_w
            self.add_thread(self._process_incoming_waves, args=(socket_w,))

    def __del__(self):
        self.running = False

        try:
            self.tun.down()
            self.tun.close()
        except:
            pass

        if self.server_sock_d is not None:
            self.server_sock_d.close()
        if self.server_sock_w is not None:
            self.server_sock_w.close()
        if self.dlm_server is not None:
            del self.dlm_server

    def tun_up(self, ip, netmask):
        self.tun.addr = ip
        self.tun.netmask = netmask
        self.tun.mtu = self.TUN_MTU
        self.tun.up()
        self.add_thread(self._process_incoming_tunnel)

    def _process_incoming_tunnel(self):
        def proc(x):
            if x.haslayer(TCP):
                try:
                    ip = self.get_node_by_param('int_ip', x.getlayer(IP).dst)['ext_ip']
                except:
                    return
                raw = (LinuxTunPacketInfo() / x).convert_to(Raw).load
                self.send_crypt(ip, raw, mode=Message.MODE_TUN)

        self.tun_sniff = sniff(count=0, iface=self.tun.name, prn=proc)

    def _process_accept_socket(self, sock, mask, sock_name):
        conn, addr = sock.accept()
        self.register_connection(addr[0], **{sock_name: conn})

    def _process_incoming_waves(self, conn: socket):
        while self.running:
            data = conn.recv(self.SOCKET_MTU)
            if data:
                print("WAVE", data)
                self.emit(Bridge.EVENT_INCOMING_WAVES, data, threaded=True, wait_response=False)
            else:
                conn.close()

    def _process_socket(self, conn: socket, mask):
        try:
            if mask & selectors.EVENT_READ:
                self._process_incoming_socket(conn)
            if mask & selectors.EVENT_WRITE:
                self._process_outgoing_packets(conn)
        except Exception as ex:
            L.error(ex)

    def _process_incoming_socket(self, conn: socket):
        data = conn.recv(self.SOCKET_MTU)
        from_ip = conn.getsockname()[0]
        if data:
            msg: Message = Message.deserialize(data, from_ip)
            print(msg)
        else:
            self.selector.unregister(conn)
            conn.close()

    def _process_outgoing_packets(self, conn):
        peer_ip = conn.getpeername()[0]
        res: Optional[Message] = self.get_conn_man(peer_ip).pop_outgoing_msg()
        if res is None:
            return
        self.get_socket(peer_ip).send(res.serialize())

    def _process_select_events(self):
        while self.running:
            for key, mask in self.selector.select():
                key.data(key.fileobj, mask)

    # Low-level sending methods

    def send_waves(self, ip: str, waves: bytes):
        self.get_socket(ip, 'w').send(waves)

    def send_msg(self, data: Message):
        peer_ip = self.next_hop(data.destination_ip)
        self.get_conn_man(peer_ip).push_outgoing_msg(data)

    # High-level sending methods

    def send_crypt(self, ip: str, data: bytes, mode=None,
                   crypt_start=0, crypt_end=None,
                   target_ip=None, source_ip=None):
        pass

    def broadcast(self, header: int, data):
        return
        # self.send_data(self.BROADCAST_IP, header, data)

    # Auto discovery

    def broadcast_discover(self):
        pass

    def _process_discover(self):
        while self.running:
            self.broadcast_discover()
            sleep(10)

    # Connection graph methods

    def get_conn_man(self, ip) -> ConnectionManager:
        n = self.get_node(ip)
        return n['manager'] if n is not None else None

    def get_socket(self, ip, mode='d') -> socket:
        n = self.get_node(ip)
        return n[f'socket_{mode}'] if n is not None else None

    def get_node(self, dst_ip) -> Optional[dict]:
        if dst_ip in self.conn_graph:
            return self.conn_graph.nodes[dst_ip]
        return None

    def get_connections(self, ip=None):
        return [self.get_node(i) for i in self.conn_graph.adj[self.ext_ip if ip is None else ip].keys()]

    def get_connections_param(self, param, ip=None):
        return [i[param] for i in self.get_connections(ip)]

    def get_connection_by_param(self, p_name, p_val, ip=None):
        return next(filter(lambda x: x[p_name] == p_val, self.get_connections(ip)))

    def get_node_by_param(self, p_name, p_val):
        return next(filter(lambda x: x[p_name] == p_val, self.conn_graph.nodes))

    def next_hop(self, ip):
        try:
            path = nx.shortest_path(self.conn_graph, self.ext_ip, ip)
            ip = path[1]
        except:
            pass
        if ip in self.get_connections_param('ext_ip'):
            return ip
        return None

    # Threading

    def add_thread(self, target: callable, **kwargs):
        thr = threading.Thread(target=target, daemon=True, **kwargs)
        self.threads.append(thr)
        thr.start()

    def run(self):
        for i in [self._process_select_events,
                  self._process_discover]:
            self.add_thread(i)


def main():
    km0 = KeyManager(directory=f'{getcwd()}/../data/alice')
    b0 = Bridge(
        '0.0.0.0', '10.10.10.1', '255.255.255.0',
        data_port=58001, wave_port=58002,
        dlm_ports=(58003, 58004)
    )

    km1 = KeyManager(directory=f'{getcwd()}/../data/bob')
    b1 = Bridge(
        '127.0.0.1', '10.10.10.2', '255.255.255.0',
        data_port=59001, wave_port=59002,
        dlm_ports=(59003, 59004)
    )

    b0.connect(b1.ext_ip, km0)
    b1.register_connection(b0.ext_ip, km1)

    threading.Thread(target=b0.run, daemon=True).start()
    threading.Thread(target=b1.run, daemon=True).start()

    sleep(1)
    b0.conn_graph.add_edge('0.0.0.0', '127.0.0.1')
    b1.conn_graph.add_edge('0.0.0.0', '127.0.0.1')
    sleep(1)

    print("START")

    while True:
        b0.send_msg(Message(11, b0.ext_ip, b1.ext_ip, b0.ext_ip, b'01921084'))
        sleep(1)


if __name__ == '__main__':
    main()
