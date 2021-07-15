from time import time

from src.sim.Data.HardwareParams import HardwareParams
from src.sim.MainDevices.Eventable import Eventable
from src.sim.Utils.StatisticsData import StatisticsData


class StatAggregator(Eventable):
    EVENT_UPDATE = 'stat_update'

    def __init__(self):
        super().__init__()

        self.key_a = []
        self.key_b = []

        self.speed = 0
        self.time_start = time()

    def update(self, data: StatisticsData, params: HardwareParams):
        # logging.debug(data.alice_key.tolist())
        # logging.debug(data.bob_key.tolist())
        # logging.debug('------------------')

        self.key_a.extend(data.alice_key)
        self.key_b.extend(data.bob_key)
        self.speed = len(self.key_a) / (time() - self.time_start)
        self.emit(StatAggregator.EVENT_UPDATE, (self.key_a, self.key_b, self.speed, len(data.alice_key)))
