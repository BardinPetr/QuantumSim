import logging as L
import selectors
import threading
from os import getcwd
from socket import create_connection, create_server, socket
from time import sleep
from typing import Optional, Any, Union
from uuid import uuid4

import networkx as nx
from numpy.typing import NDArray
from pytun import TunTapDevice, IFF_TUN
from scapy.layers.inet import IP, TCP
from scapy.layers.tuntap import LinuxTunPacketInfo
from scapy.packet import Raw
from scapy.sendrecv import sniff

from src.KeyManager import KeyManager
from src.msgs.Message import Message
from src.msgs.Payloads import DiscoverMsg, CryptMsg, RPCMsg
from src.sim.MainDevices.Eventable import Eventable
from src.sim.Math.QBERGen import key_gen, key_with_mist_gen
from src.utils.ConnectionManager import ConnectionManager
from src.utils.DistributedLock import LockServer, LockClient

L.basicConfig(encoding='utf-8', level=L.DEBUG)
L.getLogger('matplotlib.font_manager').disabled = True

import selectors


class Bridge(Eventable):
    EVENT_INCOMING_SOCKET = 'inc_soc'
    EVENT_INCOMING_WAVES = 'inc_waves'
    EVENT_INCOMING_CRYPT = 'inc_crypt'
    EVENT_INCOMING_CLASSIC = 'inc_classic'

    EVENT_PROC_CASCADE_SEED = 'casc_s'
    EVENT_PROC_CASCADE_CALL = 'casc_c'

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

        # node name->ext_ip, params->{'ext_ip', 'int_ip', 'socket_d', 'socket_w', 'manager'}
        self.conn_graph = nx.Graph()

        self.conn_graph.add_node(ext_ip, int_ip=tun_ip)

        assert (self.PACKET_LENGTH + 20) < self.SOCKET_MTU
        assert (self.TUN_MTU + 20) < self.SOCKET_MTU

    def connect(self, ip: str, key_manager: KeyManager, d_port=None, w_port=None, dlm_ports=None):
        self.data_conn = create_connection((ip, self.data_port if d_port is None else d_port))
        self.wave_conn = create_connection((ip, self.wave_port if w_port is None else w_port))
        self.register_connection(ip, key_manager, self.data_conn, self.wave_conn, dlm_ports)

    def register_connection(self, ext_ip: str,
                            key_manager: KeyManager = None,
                            socket_d: socket = None, socket_w: socket = None,
                            dlm_ports=None):
        node = self.get_node(ext_ip)
        if node is None:
            self.conn_graph.add_node(
                ext_ip,
                int_ip=None,
                ext_ip=ext_ip
            )
            self.conn_graph.add_edge(self.ext_ip, ext_ip)
            node = self.get_node(ext_ip)

        if key_manager is not None:
            dlm_ports = self.dlm_ports if dlm_ports is None else dlm_ports
            dlmc = LockClient((ext_ip if self.user_mode == Bridge.USER_ALICE else self.ext_ip),
                              *dlm_ports,
                              identity=ext_ip)
            node['manager'] = ConnectionManager(self.ext_ip, ext_ip, key_manager, dlmc)
            node['manager'].set_bridge_methods(self)

        if socket_d is not None:
            socket_d.setblocking(False)
            node['socket_d'] = socket_d
            self.selector.register(socket_d, selectors.EVENT_READ | selectors.EVENT_WRITE,
                                   lambda *args: self._process_socket(*args, peer_ip=ext_ip))

        if socket_w is not None:
            node['socket_w'] = socket_w
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
                self.send_crypt(ip, CryptMsg.MODE_TUN, raw)

        self.tun_sniff = sniff(count=0, iface=self.tun.name, prn=proc)

    def _process_accept_socket(self, sock, mask, sock_name):
        if mask & selectors.EVENT_READ:
            conn, addr = sock.accept()
            self.register_connection(addr[0], **{sock_name: conn})

    def _process_incoming_waves(self, conn: socket):
        while self.running:
            data = conn.recv(self.SOCKET_MTU)
            if data:
                print("WAVE", data)
                self.emit(Bridge.EVENT_INCOMING_WAVES, data, threaded=True)
            else:
                conn.close()

    def _process_socket(self, conn: socket, mask, peer_ip):
        try:
            if mask & selectors.EVENT_READ:
                self._process_incoming_socket(conn, peer_ip)
            if mask & selectors.EVENT_WRITE:
                self._process_outgoing_packets(conn, peer_ip)
        except Exception as ex:
            L.error(ex)

    def _process_select_events(self):
        while self.running:
            for key, mask in self.selector.select():
                key.data(key.fileobj, mask)

    def _process_outgoing_packets(self, conn, peer_ip):
        man = self.get_conn_man(peer_ip)
        if man is None:
            return
        res: Optional[Message] = man.pop_outgoing_msg()
        if res is None:
            return
        print(f"SEND {res}")
        conn.send(res.serialize())

    def _process_incoming_socket(self, conn: socket, peer_ip):
        data = conn.recv(self.SOCKET_MTU)
        if data:
            msg: Optional[Message] = Message.deserialize(data, peer_ip)
            if msg is None:
                return
            if msg.source_ip == self.ext_ip:
                return

            L.debug(f"Received {msg}")

            if msg.header_mode == Message.HEADER_CRYPT:
                man = self.get_conn_man(peer_ip)
                if man is None:
                    return

                if msg.destination_ip == self.ext_ip:
                    res, new_msg = man.decrypt(msg)
                    if msg.payload.mode == CryptMsg.MODE_EVT:
                        self.emit(Bridge.EVENT_INCOMING_CRYPT, new_msg)
                    elif msg.payload.mode == CryptMsg.MODE_TUN:
                        self.tun.write(res)
                else:
                    res, new_msg = man.decrypt(msg, True)
                    self.send_crypt_msgs_pack([new_msg])
                return

            if msg.header_mode == Message.HEADER_DISCOVER:
                payload: DiscoverMsg = msg.payload
                self.conn_graph.add_node(msg.source_ip,
                                         ext_ip=msg.source_ip,
                                         int_ip=payload.int_ip)
                self.conn_graph.add_edges_from([(msg.source_ip, i) for i in payload.connections])
                # L.debug(f"DISCOVERED {msg.source_ip} -> {payload.connections}")
                # nx.draw(self.conn_graph, with_labels=True)
                # plt.show()

            if msg.destination_ip != self.ext_ip:
                self.send_msg(msg)
                return

            if msg.header_mode == Message.HEADER_RPC:
                payload: RPCMsg = msg.payload

                if payload.is_req:
                    self.emit(payload.proc_name, payload.data,
                              on_response=lambda x: self._send_rpc_resp(msg.source_ip,
                                                                        payload.proc_name,
                                                                        payload.req_id,
                                                                        payload.data),
                              threaded=True)
                else:
                    self.set_proc_result(payload.req_id, payload.data)
        else:
            self.selector.unregister(conn)
            conn.close()

    # Low-level sending methods

    def send_waves(self, ip: str, waves: bytes):
        s = self.get_socket(ip, 'w')
        if s is not None:
            s.send(waves)

    def _create_msg(self, dest_ip: str, header: int, payload: Any):
        return Message(header, self.ext_ip, dest_ip, self.ext_ip, payload)

    def _send_msg(self, peer_ip: str, data: Message):
        data.from_ip = self.ext_ip
        man = self.get_conn_man(peer_ip)
        if man is not None:
            man.push_outgoing_msg(data)

    def send_msg(self, data: Message):
        peer_ips = self.next_hop(data.destination_ip, force_one=False)
        if peer_ips is None:
            return False
        [self._send_msg(i, data) for i in peer_ips if i not in [self.ext_ip, data.from_ip, data.source_ip]]

    def broadcast(self, data: Message):
        data.destination_ip = Bridge.BROADCAST_IP
        self.send_msg(data)

    # High-level sending methods

    def send_crypt_msgs_pack(self, msgs: list[Message]):
        peer_ip = self.next_hop(msgs[0].destination_ip)
        if peer_ip is None:
            return
        man = self.get_conn_man(peer_ip)
        if man is None:
            return
        man.push_outgoing_crypt_msgs(msgs)

    def send_crypt(self, dest_ip: str, mode: int, data: bytes, crypt_start: int = 0, crypt_end: int = None):
        peer_ip = self.next_hop(dest_ip)
        if peer_ip is None:
            return
        man = self.get_conn_man(peer_ip)
        if man is None:
            return
        self.send_crypt_msgs_pack([
            self._create_msg(dest_ip, Message.HEADER_CRYPT, i)
            for i in man.encrypt_prepare(mode, data, self.ext_ip, crypt_start, crypt_end)
        ])

    # RPC

    def call_rpc(self, ip, p_name, data):
        pid = uuid4().hex
        self.send_msg(self._create_msg(ip, Message.HEADER_RPC, RPCMsg(pid, p_name, True, data)))
        return pid

    def _send_rpc_resp(self, ip, p_name, pid, data):
        self.send_msg(self._create_msg(ip, Message.HEADER_RPC, RPCMsg(pid, p_name, False, data)))

    # Cascade

    def send_cascade_seed(self, ip, seed):
        return self.call_rpc(ip, RPCMsg.CASCADE_SEED, seed)

    def send_cascade_data(self, ip, idx, data: NDArray):
        return self.call_rpc(ip, RPCMsg.CASCADE_REQUEST, [idx, data.tolist()])

    def get_cascade_funcs(self, ip):
        return {
            'send_cascade_seed': lambda a: self.send_cascade_seed(ip, a),
            'send_cascade_data': lambda *args: self.send_cascade_data(ip, *args),
            'wait_for_result':   self.wait_for_result
        }

    # Auto discovery

    def _process_discover(self):
        while self.running:
            payload = DiscoverMsg(0, self.tun_ip, self.get_connections_param_map('ext_ip'))
            self.broadcast(self._create_msg("", Message.HEADER_DISCOVER, payload))
            sleep(10)

    # Connection graph methods

    def get_conn_man(self, ip) -> ConnectionManager:
        n = self.get_node(ip)
        return n.get('manager', None) if n is not None else None

    def get_socket(self, ip, mode='d') -> socket:
        n = self.get_node(ip)
        return n.get(f'socket_{mode}', None) if n is not None else None

    def get_node(self, dst_ip) -> Optional[dict]:
        if dst_ip in self.conn_graph:
            return self.conn_graph.nodes[dst_ip]
        return None

    def get_nodes(self) -> list[dict]:
        return [self.conn_graph.nodes[dst_ip] for dst_ip in self.conn_graph]

    def get_connections(self, ip=None):
        return [self.get_node(i) for i in self.conn_graph.adj[self.ext_ip if ip is None else ip].keys()]

    def get_connections_param_map(self, param, ip=None):
        return [i.get(param, None) for i in self.get_connections(ip)]

    def get_connection_by_param(self, p_name, p_val, ip=None):
        return next(filter(lambda x: x.get(p_name, None) == p_val, self.get_connections(ip)))

    def get_node_by_param(self, p_name, p_val):
        return next(iter(filter(lambda x: x.get(p_name, None) == p_val, self.get_nodes())))

    def next_hop(self, ip, force_one=True) -> Optional[Union[list[str], str]]:
        conns = self.get_connections_param_map('ext_ip')
        res = []
        if ip == Bridge.BROADCAST_IP:
            res = conns
        else:
            try:
                path = nx.shortest_path(self.conn_graph, self.ext_ip, ip)
                res = [path[1]]
            except:
                pass
        if len(res) == 0:
            return None
        return res[0] if force_one else res

    # Threading

    def add_thread(self, target: callable, **kwargs):
        thr = threading.Thread(target=target, daemon=True, **kwargs)
        self.threads.append(thr)
        thr.start()

    def run(self):
        for i in [
            self._process_select_events,
            # self._process_discover
        ]:
            self.add_thread(i)


def main():
    km0 = KeyManager(directory=f'{getcwd()}/../data/alice')
    b0 = Bridge(
        '127.0.0.1', '10.10.10.1', '255.255.255.0',
        data_port=58001, wave_port=58002,
        dlm_ports=(58003, 58004),
        user_mode=Bridge.USER_ALICE
    )
    b0.subscribe(Bridge.EVENT_INCOMING_CRYPT, lambda x: print(x))
    # b0.subscribe(Bridge.EVENT_INCOMING_WAVES, lambda x: print("W", x))

    km1 = KeyManager(directory=f'{getcwd()}/../data/bob', is_bob=True)
    b1 = Bridge(
        '127.0.0.2', '10.10.10.2', '255.255.255.0',
        data_port=59001, wave_port=59002,
        dlm_ports=(58003, 58004),
        user_mode=Bridge.USER_BOB
    )
    b1.subscribe(Bridge.EVENT_INCOMING_CRYPT, lambda x: print(x))

    b0.connect(b1.ext_ip, km0, 59001, 59002)
    b1.register_connection(b0.ext_ip, km1)

    b0.run()
    b1.run()

    km0.append(key_without_errors)
    km1.append(key_with_errors)

    while True:
        sleep(1)


if __name__ == '__main__':
    main()
