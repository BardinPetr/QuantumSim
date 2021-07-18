import os
import threading
from src.crypto.KeyManager import KeyManager
from src.statistics.StatWriter import StatWriter
from src.sim.data.HardwareParams import HardwareParams
from src.sim.devices.OpticFiber import OpticFiber
from src.sim.ClassicChannel import ClassicChannel
from src.sim.devices.users.EndpointDevice import EndpointDevice
from src.sim.devices.users.Alice import Alice
from src.sim.devices.users.Bob import Bob
from src.statistics.Statistics import Statistics


def main():
    hp = HardwareParams(
        polarization=(1, 0),
        # laser_period=5000,
        mu=2,
        # delta_opt=0,
        # prob_opt=0,
        # pdc=10 ** -5,
        eff=1,
        # dt=1000,
        # fiber_length=0
    )

    sw = StatWriter(f'{os.getcwd()}/data/statistics.json')

    km_alice = KeyManager(directory=f'{os.getcwd()}/data/alice')
    km_bob = KeyManager(directory=f'{os.getcwd()}/data/bob')

    cc = ClassicChannel(ClassicChannel.MODE_LOCAL)
    cc.subscribe(ClassicChannel.EVENT_ON_RECV, print)

    stat = Statistics(hp)
    stat.subscribe(Statistics.EVENT_RESULT, sw.write)
    stat.subscribe(Statistics.EVENT_RESULT, stat.log_statistics)

    alice = Alice(hp, classic_channel=cc, session_size=10 ** 4)
    alice.subscribe(EndpointDevice.EVENT_KEY_FINISHED, stat.alice_update)
    alice.subscribe(EndpointDevice.EVENT_KEY_FINISHED, lambda data: km_alice.append(data[0]))

    of = OpticFiber(length=hp.fiber_length, deltaopt=hp.delta_opt, probopt=hp.prob_opt)
    alice.forward_link(of)

    bob = Bob(hp, classic_channel=cc)
    bob.subscribe(EndpointDevice.EVENT_KEY_FINISHED, stat.bob_update)
    bob.subscribe(EndpointDevice.EVENT_KEY_FINISHED, lambda data: km_bob.append(data[0]))

    of.forward_link(bob)

    threading.Thread(target=lambda: alice.start(progress_bar=False), daemon=True).run()

    while True:
        pass


if __name__ == "__main__":
    main()
