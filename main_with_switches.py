import os
import threading

from src.crypto.KeyManager import KeyManager
from src.sim.ClassicChannel import ClassicChannel
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

    # channel for public messages (TODO: replace with Bridge)
    alice_cc = ClassicChannel('alice')
    bob1_cc = ClassicChannel('bob1')
    bob2_cc = ClassicChannel('bob2')

    bob1_cc.connect(alice_cc)
    bob2_cc.connect(alice_cc)

    km_alice = KeyManager(directory=f'{os.getcwd()}/data/alice')

    km_bob1 = KeyManager(directory=f'{os.getcwd()}/data/bob1')
    km_bob2 = KeyManager(directory=f'{os.getcwd()}/data/bob2')

    alice = Alice(ahp, classic_channel=alice_cc, key_manager=km_alice, session_size=10 ** 4)

    bob1 = Bob(bhp, classic_channel=bob1_cc, key_manager=km_bob1)
    alice.forward_link(bob1)

    bob2 = Bob(bhp, classic_channel=bob2_cc, key_manager=km_bob2)
    alice.forward_link(bob2)

    threading.Thread(target=lambda: alice.start(progress_bar=False), daemon=True).run()

    while True:
        pass


if __name__ == "__main__":
    main()
