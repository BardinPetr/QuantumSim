from dataclasses import dataclass
from dataclasses_json import dataclass_json


@dataclass_json
@dataclass
class AliceHardwareParams:
    polarization: tuple = None
    laser_period: float = 5000
    mu: float = 0.1

    @property
    def laser_freq(self):
        return 1 / self.laser_period
