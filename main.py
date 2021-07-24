import os
import threading

from PIL import Image
from src.sim.MainDevices.ClassicChannel import ClassicChannel

from src.connections.Bridge import Bridge
from src.crypto.Crypto import Crypto
from src.crypto.KeyManager import KeyManager
from src.sim.data.HardwareParams import HardwareParams
from src.sim.devices.OpticFiber import OpticFiber
from src.sim.devices.users.Alice import Alice
from src.sim.devices.users.Bob import Bob
from src.sim.devices.users.EndpointDevice import EndpointDevice
from src.statistics.StatisticsWriter import StatisticsWriter

i = 1


# TODO: replace classic channel with Bridge
def main():
    hp = HardwareParams(
        polarization=(1, 0),
        # laser_period=5000,
        # mu=1,
        # delta_opt=0,
        # prob_opt=0,
        # pdc=10 ** -5,
        # eff=0.1,
        # dt=1000,
        # fiber_length=50
    )

    sw = StatisticsWriter(f'{os.getcwd()}/data/statistics.json')

    km_alice = KeyManager(directory=f'{os.getcwd()}/data/alice')
    alice_c = Crypto(km_alice)
    alice_b = Bridge('0.0.0.0', '10.10.10.1', in_port=50001)
    alice_b.register_crypto('127.0.0.1', alice_c)
    threading.Thread(target=alice_b.run, daemon=True).run()

    km_bob = KeyManager(directory=f'{os.getcwd()}/data/bob')
    bob_c = Crypto(km_bob)
    bob_b = Bridge('127.0.0.1', '10.10.10.2', in_port=50002)
    bob_b.register_crypto('0.0.0.0', bob_c)
    threading.Thread(target=bob_b.run, daemon=True).run()

    bob_b.connect('0.0.0.0', 50001)

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
    bob.subscribe(EndpointDevicdde.EVENT_KEY_FINISHED, lambda data: km_bob.append(data[0]))

    of.forward_link(bob)

    def send():
        i = 14
        im = Image.open(f"cat{i}.jpg")
        # im = im.crop(())
        im = im.resize((300, 300))
        im.show()
        k = im.tobytes()  # open('poem.txt', 'rb').read()
        print(len(k) * 8)

        def recv(x):
            global i
            print(len(x))
            im = Image.frombytes('RGB', (300, 300), x)
            im.save(f'res{i}.jpg')
            im.show()
            i += 1
            km_alice.cur_pos = 0
            km_bob.cur_pos = 0
            km_alice.save_cur_pos()
            km_bob.save_cur_pos()
            # send()
            # with open('res_poem.txt', 'wb') as f:
            # f.write(x)
            # print(np.sum(BinaryFile('poem.txt').read_all() != BinaryFile('res_poem.txt').read_all()) / (len(x) * 8))

        alice_b.subscribe(Bridge.EVENT_SOCKET_INCOMING, recv)

        bob_b.send_crypt('0.0.0.0', k)

    # threading.Thread(target=send, daemon=True).run()
    threading.Thread(target=lambda: alice.start(progress_bar=False), daemon=True).run()

    while True:
        pass


if __name__ == "__main__":
    main()
