import os
import threading

from src.KeyManager import KeyManager
from src.StatWriter import StatWriter
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
        # mu=2,
        # delta_opt=0,
        # prob_opt=0,
        # pdc=10 ** -5,
        # eff=1,
        # dt=1000,
        # fiber_length=0
    )

    sw = StatWriter(f'{os.getcwd()}/data/statistics.json')

    km_alice = KeyManager(directory=f'{os.getcwd()}/data/alice')
    # alice_c = Crypto(km_alice)
    # alice_b = Bridge(alice_c, '0.0.0.0', '10.10.10.1', in_port=51001)
    # threading.Thread(target=alice_b.run, daemon=True).run()

    km_bob = KeyManager(directory=f'{os.getcwd()}/data/bob')
    # bob_c = Crypto(km_bob)
    # bob_b = Bridge(bob_c, '127.0.0.1', '10.10.10.2', in_port=51002)
    # threading.Thread(target=bob_b.run, daemon=True).run()
    #
    # bob_b.connect('0.0.0.0', 51001)

    cc = ClassicChannel(ClassicChannel.MODE_LOCAL)

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

    # def send():
    #     sleep(5)
    #
    #     def recv(x):
    #         print("$" * 20)
    #         with open('res.bmp', 'wb') as f:
    #             f.write(x)
    #
    #     alice_b.subscribe(Bridge.EVENT_SOCKET_INCOMING, recv)
    #
    #     bob_b.send_crypt('0.0.0.0', open('poem.txt', 'rb').read())
    #
    # threading.Thread(target=send, daemon=True).run()
    threading.Thread(target=lambda: alice.start(progress_bar=False), daemon=True).run()

    while True:
        pass


if __name__ == "__main__":
    main()
