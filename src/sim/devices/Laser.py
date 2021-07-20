from typing import Tuple, Union

from tqdm import tqdm

from src.sim.Clock import Clock
from src.sim.devices.Device import Device
from src.sim.QuantumState import QuantumState
from src.sim.Wave import Wave


class Laser(Device):
    def __init__(self, polarization: Union[Tuple[complex, complex], None] = None,
                 mu: float = 1, name='Laser'):
        super().__init__(name)

        self.mu = mu
        self.polarization = polarization

    def emit_wave(self, time):
        if self.polarization is not None:
            self(Wave(self.mu, QuantumState(self.polarization), time))
        else:
            self(Wave(self.mu, QuantumState.random(), time))
