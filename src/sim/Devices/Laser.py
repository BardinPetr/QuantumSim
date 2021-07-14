from typing import Tuple, Union

from tqdm import tqdm

from src.sim.Devices.Clock import Clock
from src.sim.MainDevices.Device import Device
from src.sim.QuantumState import QuantumState
from src.sim.Wave import Wave


class Laser(Device):
    def __init__(self, clock: Clock, polarization: Union[Tuple[complex, complex], None] = None,
                 mu: float = 1, name='Laser'):
        super().__init__(name)

        self.mu = mu
        self.polarization = polarization
        self.clock = clock

    def start(self, impulse_count=None, progress_bar=True):
        # print("\n")
        progress_bar = progress_bar and (impulse_count is not None)
        if progress_bar:
            pbar = tqdm(total=impulse_count, smoothing=0.1)

        for i in self.clock.work():
            if self.polarization is not None:
                self(Wave(self.mu, QuantumState(self.polarization), i))
            else:
                self(Wave(self.mu, QuantumState.random(), i))

            if impulse_count is not None:
                if impulse_count <= i // self.clock.period + 1:
                    break
            if progress_bar:
                pbar.update(1)
