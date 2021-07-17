from dataclasses import dataclass

from dataclasses_json import dataclass_json

from src.sim.data.HardwareParams import HardwareParams

"""
Class for storing statistics data
"""


@dataclass_json
@dataclass
class StatisticsData:
    speed: float
    qber: float
    received_waves_count: int
    emitted_waves_count: int
    key_length: int

    params: HardwareParams

    @property
    def q(self):
        return self.received_waves_count / self.emitted_waves_count

    @property
    def r_sift(self):
        return self.q * self.params.laser_freq * 10e9
