import signal
from os import getcwd
from time import sleep

from src.connections.Bridge import Bridge
from src.crypto.KeyManager import KeyManager
from src.sim.data.HardwareParams import HardwareParams
from src.sim.devices.users.Bob import Bob
from src.sim.devices.users.EndpointDevice import EndpointDevice

peer_ip = '192.168.8.100'

km1 = KeyManager(directory=f'{getcwd()}/data/bob', is_bob=True)

b1 = Bridge(
    '192.168.8.101', '10.10.10.2', '255.255.255.0',
    data_port=58001, wave_port=58002,
    dlm_ports=(58003, 58004),
    user_mode=Bridge.USER_BOB
)

b1.subscribe(Bridge.EVENT_INCOMING_CRYPT, lambda x: print(x))
b1.register_connection(peer_ip, km1)
b1.run()

hp = HardwareParams(
    polarization=(1, 0),
)

session_size = 10 ** 4

bob = Bob(hp, session_size=session_size)
bob.subscribe(EndpointDevice.EVENT_KEY_FINISHED, lambda data: km1.append(data[0]))
bob.bind_bridge(peer_ip, b1)


def ex(*_):
    b1.stop()
    exit(0)


signal.signal(signal.SIGTERM, ex)
signal.signal(signal.SIGINT, ex)

while True:
    # b1.send_crypt('192.168.8.102', CryptMsg.MODE_EVT, b'hi_from_101')
    sleep(1)
    # b1.send_crypt('192.168.8.102', CryptMsg.MODE_EVT, b'hi_from_101')
