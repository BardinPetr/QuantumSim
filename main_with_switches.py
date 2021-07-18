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
    cc = ClassicChannel(ClassicChannel.MODE_LOCAL)

    km_alice = KeyManager(directory=f'{os.getcwd()}/data/alice')

    km_bob1 = KeyManager(directory=f'{os.getcwd()}/data/bob1')
    km_bob2 = KeyManager(directory=f'{os.getcwd()}/data/bob2')

    alice = Alice('alice', ahp, classic_channel=cc, key_manager=km_alice, session_size=10 ** 4)

    bob1 = Bob('bob1', bhp, classic_channel=cc, key_manager=km_bob1)
    alice.forward_link(bob1)

    bob2 = Bob('bob2', bhp, classic_channel=cc, key_manager=km_bob2)
    alice.forward_link(bob2)

    threading.Thread(target=lambda: alice.start(progress_bar=False), daemon=True).run()

    while True:
        pass


if __name__ == "__main__":
    main()
