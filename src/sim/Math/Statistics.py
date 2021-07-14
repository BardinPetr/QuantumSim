import numpy as np

from src.sim.Data.HardwareParams import HardwareParams
from src.sim.MainDevices.Eventable import Eventable
from src.sim.Utils.StatisticsData import StatisticsData


class Statistics(Eventable):
    EVENT_RESULT = 'event_result'

    def __init__(self, params: HardwareParams):
        super().__init__()

        self.params = params
        self.clear()

    def clear(self):
        self.received_waves_count = 0
        self.emitted_waves_count = 0
        self.alice_key = None
        self.bob_key = None

    def check(self):
        if self.alice_key is not None and self.bob_key is not None:
            data = StatisticsData(
                self.alice_key,
                self.bob_key,
                self.count_qber(),
                self.received_waves_count,
                self.emitted_waves_count,
                self.params
            )

            self.emit(self.EVENT_RESULT, data, self.params)
            self.clear()

    def alice_update(self, data):
        self.alice_key, self.emitted_waves_count = data
        self.check()

    def bob_update(self, data):
        self.bob_key, self.received_waves_count = data
        self.check()

    def count_qber(self):
        return np.sum(self.alice_key != self.bob_key) / len(self.alice_key)

    @staticmethod
    def log_statistics(data: StatisticsData, params: HardwareParams):
        print()
        print('Generated key length:', len(data.alice_key))

        print()
        print('Practical:')
        print('QBER:', data.qber)
        print('Q(μ):', data.received_waves_count / data.emitted_waves_count)

        # (r_sift, qber_theoretical, Q), *_ = generate(params, data.emitted_waves_count)

        # print()
        # print('Theoretical:')
        # print('QBER:', qber_theoretical)
        # print('Q(μ):')
