import threading
from time import sleep

from src.Bridge import Bridge
from src.crypto.Crypto import Crypto
from src.crypto.KeyManager import KeyManager
from src.sim.data.AliceHardwareParams import AliceHardwareParams
from src.sim.data.BobHardwareParams import BobHardwareParams
from src.sim.devices.users.Alice import Alice
from src.sim.devices.users.Bob import Bob


def main():
    # parameters of system
    ahp = AliceHardwareParams(
        polarization=(1, 0),
    )
    bhp = BobHardwareParams()

    # Alice init
    alice_km = KeyManager(directory='data/alice')
    alice_bridge = Bridge(Crypto(alice_km), '127.0.0.1', '10.10.10.1', in_port=51001)

    alice = Alice(ahp, bridge=alice_bridge, key_manager=alice_km, session_size=10 ** 4)

    # first Bob init
    bob1_km = KeyManager(directory='data/bob1')
    bob1_bridge = Bridge(Crypto(alice_km), '127.0.0.2', '10.10.10.2', in_port=51002)

    bob1 = Bob(bhp, bridge=bob1_bridge, key_manager=bob1_km)

    # second Bob init
    # bob2_km = KeyManager(directory='data/bob2')
    # bob2_bridge = Bridge(Crypto(alice_km), '127.0.0.3', '10.10.10.3')
    #
    # bob2 = Bob(bhp, bridge=bob2_bridge, key_manager=bob2_km)

    # connections
    alice.forward_link(bob1)
    # alice.forward_link(bob2)

    alice_bridge.connect('127.0.0.2', 51002)

    threading.Thread(target=lambda: alice.start(progress_bar=False), daemon=True).run()

    sleep(1)

    alice.set_bob(bob1.bridge.external_ip)

    while True:
        pass


if __name__ == "__main__":
    main()
