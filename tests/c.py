from os import getcwd
from time import sleep

from src.Bridge import Bridge
from src.KeyManager import KeyManager
from src.msgs.Payloads import CryptMsg

km1 = KeyManager(directory=f'{getcwd()}/data/bob')
b1 = Bridge(
    '192.168.8.102', '10.10.10.3', '255.255.255.0',
    data_port=58001, wave_port=58002,
    dlm_ports=(58003, 58004),
    user_mode=Bridge.USER_ALICE
)
b1.subscribe(Bridge.EVENT_INCOMING_CRYPT, lambda x: print(x))
b1.connect('192.168.8.101', km1)

b1.run()
while True:
    sleep(1.2)
    # b1.send_crypt('192.168.8.100', CryptMsg.MODE_EVT, b'hi_from_102')
    # b1.send_crypt('192.168.8.101', CryptMsg.MODE_EVT, b'hi_from_102')
