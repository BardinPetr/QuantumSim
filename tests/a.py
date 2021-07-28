import signal
from os import getcwd
from time import sleep

from src.connections.Bridge import Bridge
from src.crypto.KeyManager import KeyManager
from src.sim.data.HardwareParams import HardwareParams
from src.sim.devices.users.Alice import Alice
from src.sim.devices.users.EndpointDevice import EndpointDevice

peer_ip = '192.168.8.101'

km0 = KeyManager(directory=f'{getcwd()}/data/alice')
b0 = Bridge(
    '192.168.8.100', '10.10.10.1', '255.255.255.0',
    data_port=58001, wave_port=58002,
    dlm_ports=(58003, 58004),
    user_mode=Bridge.USER_ALICE
)
b0.subscribe(Bridge.EVENT_INCOMING_CRYPT, lambda x: print(x))
b0.connect(peer_ip, km0)

b0.run()

hp = HardwareParams(
    polarization=(1, 0),
)

session_size = 10 ** 4

alice = Alice(hp, session_size=session_size)
alice.subscribe(EndpointDevice.EVENT_KEY_FINISHED, lambda data: km0.append(data[0]))
alice.bind_bridge(peer_ip, b0)


# Thread(target=lambda: alice.start(progress_bar=True), daemon=True).start()

def ex(*_):
    b0.stop()
    exit(0)


signal.signal(signal.SIGTERM, ex)
signal.signal(signal.SIGINT, ex)

while True:
    sleep(5)
