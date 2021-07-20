from dataclasses import dataclass

from dataclasses_json import dataclass_json


@dataclass_json
@dataclass
class HardwareParams:
    polarization: tuple = None
    laser_period: float = 5000
    mu: float = 3 * 10e9
    attenuation: float = 104.7  # ослабление в дБ
    delta_opt: float = 0.2
    prob_opt: float = 0.05
    pdc: float = 10 ** -6
    eff: float = 0.1
    dt: float = 1000
    fiber_length: float = 50

    @property
    def laser_freq(self):
        return 1 / self.laser_period
