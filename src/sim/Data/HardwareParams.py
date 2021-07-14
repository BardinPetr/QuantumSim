from dataclasses import dataclass


@dataclass
class HardwareParams:
    polarization: tuple = None
    laser_period: float = 5000
    mu: float = 0.1
    delta_opt: float = 0.2
    prob_opt: float = 0.05
    pdc: float = 10 ** -6
    eff: float = 0.1
    dt: float = 1000
    fiber_length: float = 50

    @property
    def laser_freq(self):
        return 1 / self.laser_period
