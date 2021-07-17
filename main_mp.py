import logging

import psutil
import ray
from ray.util.queue import Queue

from src.sim.data.HardwareParams import HardwareParams
from src.sim.devices.OpticFiber import OpticFiber
from src.sim.ClassicChannel import ClassicChannel
from src.sim.devices.users.EndpointDevice import EndpointDevice
from src.sim.devices.users.Alice import Alice
from src.sim.devices.users.Bob import Bob
from src.sim.Math.StatAggregator import StatAggregator
from src.statistics.Statistics import Statistics

logging.basicConfig(filename='log.log', encoding='utf-8', level=logging.DEBUG)

num_cpus = psutil.cpu_count(logical=False)
ray.init(num_cpus=num_cpus)


@ray.remote
def proc(data):
    mode, conn = data
    if mode == 1:
        return monitor(conn)

    hp = HardwareParams(
        polarization=(1, 0),
        # laser_period=5000,
        # mu=0.1,
        # delta_opt=0,
        # prob_opt=0,
        # pdc=10 ** -5,
        # eff=0.1,
        # dt=1000,
        # fiber_length=50
    )

    cc = ClassicChannel(ClassicChannel.MODE_LOCAL)

    stat = Statistics(hp)
    # stat.subscribe(Statistics.EVENT_RESULT, Statistics.log_statistics)
    stat.subscribe(Statistics.EVENT_RESULT, lambda x, y: conn.put((x, y)))

    alice = Alice(hp, classic_channel=cc, session_size=4 * 10 ** 4)
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
        print(f"{'*' * 20}\nSpeed:\t{round(speed, 3)} bit/s\tSize: {len(key_a)} bit\tAdded: {dk} bit")

    aggr = StatAggregator()
    aggr.subscribe(StatAggregator.EVENT_UPDATE, update)
    while True:
        data, params = conn.get()
        aggr.update(data, params)


def main():
    # n = 4
    # q = multiprocessing.Manager().Queue()
    num_cpus = 3
    queue = Queue(maxsize=100)

    # os.system("taskset -p 0xff %d" % os.getpid())

    ray.get([proc.remote((0, queue)) for i in range(num_cpus - 1)] + [proc.remote((1, queue))])

    # with multiprocessing.Pool(processes=n + 1) as pool:
    #     m = multiprocessing.Manager()
    #     q = m.Queue()
    #     pool.map(proc, ([(1, q)] + [(0, q)] * n))

    # q = multiprocessing.Manager().Queue()
    # threads = [multiprocessing.Process(target=proc, args=((0, q),)) for _ in range(n)]
    # threads.append(multiprocessing.Process(target=proc, args=((1, q),)))
    # [i.start() for i in threads]

    # summ = 0
    # t = time()
    # while True:
    #     w: StatisticsData = q.get()[0]
    #     summ += len(w.alice_key)
    #     print(summ, len(w.alice_key), summ / (time() - t))

    # [i.join() for i in threads]


if __name__ == "__main__":
    main()
