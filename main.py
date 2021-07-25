import threading
from os import getcwd
from time import sleep

from src.connections.Bridge import Bridge
from src.crypto.KeyManager import KeyManager
from src.math.QBERGen import key_gen, key_with_mist_gen
from src.sim.data.HardwareParams import HardwareParams
from src.sim.devices.OpticFiber import OpticFiber
from src.sim.devices.users.Alice import Alice
from src.sim.devices.users.Bob import Bob
from src.sim.devices.users.EndpointDevice import EndpointDevice
from src.statistics.StatisticsAggregator import StatisticsAggregator


def main():
    km0 = KeyManager(directory=f'{getcwd()}/data/alice')
    b0 = Bridge(
        '127.0.0.1', '10.10.10.1', '255.255.255.0',
        data_port=58001, wave_port=58002,
        dlm_ports=(58003, 58004),
        user_mode=Bridge.USER_ALICE
    )
    b0.subscribe(Bridge.EVENT_INCOMING_CRYPT, lambda x: print(x))
    # b0.subscribe(Bridge.EVENT_INCOMING_WAVES, lambda x: print("W", x))

    km1 = KeyManager(directory=f'{getcwd()}/data/bob', is_bob=True)
    b1 = Bridge(
        '127.0.0.2', '10.10.10.2', '255.255.255.0',
        data_port=59001, wave_port=59002,
        dlm_ports=(58003, 58004),
        user_mode=Bridge.USER_BOB
    )
    b1.subscribe(Bridge.EVENT_INCOMING_CRYPT, lambda x: print(x))

    b0.connect(b1.ext_ip, km0, 59001, 59002)
    b1.register_connection(b0.ext_ip, km1)

    b0.run()
    b1.run()

    # Optics
    hp = HardwareParams(
        polarization=(1, 0),
        attenuation=0,
        delta_opt=0
    )

    stat = StatisticsAggregator(hp)
    stat.subscribe(StatisticsAggregator.EVENT_RESULT, stat.log_statistics)

    alice = Alice(hp, session_size=10 ** 2)
    alice.subscribe(EndpointDevice.EVENT_KEY_FINISHED, stat.alice_update)
    alice.subscribe(EndpointDevice.EVENT_KEY_FINISHED, lambda data: km0.append(data[0]))
    alice.bind_bridge(b1.ext_ip, b0)

    bob = Bob(hp, session_size=10 ** 2)
    bob.subscribe(EndpointDevice.EVENT_KEY_FINISHED, stat.bob_update)
    bob.subscribe(EndpointDevice.EVENT_KEY_FINISHED, lambda data: km1.append(data[0]))
    bob.bind_bridge(b0.ext_ip, b1)

    threading.Thread(target=lambda: alice.start(progress_bar=True), daemon=True).run()

    sleep(1)

    length = 10 ** 4 + 8
    qber = 0.05

    key_without_errors = key_gen(length)
    key_with_errors = key_with_mist_gen(key_without_errors, qber)

    km0.append(key_without_errors)
    km1.append(key_with_errors)

    print('successful!')

    while True:
        sleep(1)


if __name__ == '__main__':
    main()
