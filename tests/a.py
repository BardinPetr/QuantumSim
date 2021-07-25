from os import getcwd
from time import sleep

from src.connections.Bridge import Bridge
from src.crypto.KeyManager import KeyManager

km0 = KeyManager(directory=f'{getcwd()}/../data/alice')
b0 = Bridge(
    '192.168.8.100', '10.10.10.1', '255.255.255.0',
    data_port=58001, wave_port=58002,
    dlm_ports=(58003, 58004),
    user_mode=Bridge.USER_ALICE
)
b0.subscribe(Bridge.EVENT_INCOMING_CRYPT, lambda x: print(x))
b0.connect('192.168.8.101', km0)

b0.run()

sleep(2)
while True:
    # b0.send_crypt('192.168.8.102', CryptMsg.MODE_EVT, b'hi_from_100')
    # b0.send_crypt('192.168.8.101', CryptMsg.MODE_EVT, b'hi_from_100')
    sleep(5)
