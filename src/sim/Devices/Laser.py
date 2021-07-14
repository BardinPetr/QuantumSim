import time
from typing import Tuple

from tqdm import tqdm

from src.Clock import Clock
from src.sim.Device import *
from src.sim.Wave import Wave


class Laser(Device):
    def __init__(self, clock: Clock, polarization: Union[Tuple[complex, complex], None] = None,
                 mu: float = 1, name='Laser'):
        super().__init__(name)

        self.mu = mu
        self.polarization = polarization
        self.clock = clock

    async def start(self, impulse_count=None):
        pbar = tqdm(total=impulse_count) if impulse_count else None

        async for i in self.clock.work():
            if self.polarization is not None:
                self(Wave(self.mu, QuantumState(self.polarization), i))
            else:
                self(Wave(self.mu, QuantumState.random(), i))

            if pbar is not None:
                if impulse_count <= i // self.clock.period:
                    break

                pbar.update(1)
