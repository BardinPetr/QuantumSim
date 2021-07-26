from os import getcwd
from time import sleep

from src.connections.Bridge import Bridge
from src.crypto.KeyManager import KeyManager

km1 = KeyManager(directory=f'{getcwd()}/data/bob', is_bob=True)
km2 = KeyManager(directory=f'{getcwd()}/data/bob', is_bob=True)

b1 = Bridge(
    '192.168.8.101', '10.10.10.2', '255.255.255.0',
    data_port=58001, wave_port=58002,
    dlm_ports=(58003, 58004),
    user_mode=Bridge.USER_BOB
)
b1.subscribe(Bridge.EVENT_INCOMING_CRYPT, lambda x: print(x))
b1.register_connection('192.168.8.100', km1)
b1.register_connection('192.168.8.102', km2)

b1.run()
while True:
    # b1.send_crypt('192.168.8.102', CryptMsg.MODE_EVT, b'hi_from_101')
    sleep(1)
    # b1.send_crypt('192.168.8.102', CryptMsg.MODE_EVT, b'hi_from_101')
