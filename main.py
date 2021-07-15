from multiprocessing import Queue, Pool, Manager

from src.sim.Data.HardwareParams import HardwareParams
from src.sim.Devices.OpticFiber import OpticFiber
from src.sim.MainDevices.ClassicChannel import ClassicChannel
from src.sim.MainDevices.EndpointDevice import EndpointDevice
from src.sim.MainDevices.Users.Alice import Alice
from src.sim.MainDevices.Users.Bob import Bob
from src.sim.Math.StatAggregator import StatAggregator
from src.sim.Math.Statistics import Statistics
import logging

logging.basicConfig(filename='log.log', encoding='utf-8', level=logging.DEBUG)

hp = HardwareParams(
    polarization=(1, 0),
    laser_period=5000,
    # mu=0.1,
    # delta_opt=0,
    # prob_opt=0,
    # pdc=10 ** -5,
    eff=0.6,
    # dt=1000,
    fiber_length=0
)


def proc(data):
    mode, conn = data
    if mode == 1:
        return monitor(conn)

    cc = ClassicChannel(ClassicChannel.MODE_LOCAL)

    stat = Statistics(hp)
    # stat.subscribe(Statistics.EVENT_RESULT, Statistics.log_statistics)
    stat.subscribe(Statistics.EVENT_RESULT, lambda x, y: conn.put((x, y)))

    alice = Alice(hp, classic_channel=cc, session_size=5 * 10 ** 4)
    alice.subscribe(EndpointDevice.EVENT_KEY_FINISHED, stat.alice_update)

    of = OpticFiber(length=hp.fiber_length, deltaopt=hp.delta_opt, probopt=hp.prob_opt)
    alice.forward_link(of)

    bob = Bob(hp, classic_channel=cc)
    bob.subscribe(EndpointDevice.EVENT_KEY_FINISHED, stat.bob_update)

    of.forward_link(bob)

    alice.start(progress_bar=False)


def monitor(conn: Queue):
    def update(x):
        key_a, _, speed, dk = x
        print(f"{'*' * 20}\nSpeed:\t{round(speed, 3)} bit/s\tSize: {len(key_a)} bit")

    aggr = StatAggregator()
    aggr.subscribe(StatAggregator.EVENT_UPDATE, update)
    while True:
        data, params = conn.get()
        aggr.update(data, params)


def main():
    n = 2
    with Pool(processes=n + 1) as pool:
        m = Manager()
        q = m.Queue()
        pool.map(proc, ([(1, q)] + [(0, q)] * n))


if __name__ == "__main__":
    main()
