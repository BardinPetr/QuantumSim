import os

from src.FileWriter import FileWriter
from src.KeyManager import KeyManager
from src.sim.Data.HardwareParams import HardwareParams
from src.sim.Devices.OpticFiber import OpticFiber
from src.sim.MainDevices.ClassicChannel import ClassicChannel
from src.sim.MainDevices.EndpointDevice import EndpointDevice
from src.sim.MainDevices.Users.Alice import Alice
from src.sim.MainDevices.Users.Bob import Bob
from src.sim.Math.Statistics import Statistics


def main():
    hp = HardwareParams(
        polarization=(1, 0),
        # laser_period=5000,
        mu=0.5,
        # delta_opt=0,
        # prob_opt=0,
        # pdc=10 ** -5,
        # eff=0.1,
        # dt=1000,
        fiber_length=10
    )

    fw = FileWriter(f'{os.getcwd()}/data/statistics.json', [
        KeyManager(directory=f'{os.getcwd()}/data/alice'),
        KeyManager(directory=f'{os.getcwd()}/data/bob')
    ])

    cc = ClassicChannel(ClassicChannel.MODE_LOCAL)

    stat = Statistics(hp)
    stat.subscribe(Statistics.EVENT_RESULT, fw.write)

    alice = Alice(hp, classic_channel=cc, session_size=10 ** 4)
    alice.subscribe(EndpointDevice.EVENT_KEY_FINISHED, stat.alice_update)
    alice.subscribe(EndpointDevice.EVENT_KEY_FINISHED, lambda data: fw.append_key(0, data[0]))

    of = OpticFiber(length=hp.fiber_length, deltaopt=hp.delta_opt, probopt=hp.prob_opt)
    alice.forward_link(of)

    bob = Bob(hp, classic_channel=cc)
    bob.subscribe(EndpointDevice.EVENT_KEY_FINISHED, stat.bob_update)
    bob.subscribe(EndpointDevice.EVENT_KEY_FINISHED, lambda data: fw.append_key(1, data[0]))

    of.forward_link(bob)

    alice.start(progress_bar=False)


if __name__ == "__main__":
    main()
