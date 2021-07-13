import time
from typing import Tuple

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

    async def start(self, time_limit=None):
        start_time = time.time()
        async for i in self.clock.work():
            if self.polarization is not None:
                self(Wave(self.mu, QuantumState(self.polarization), i))
            else:
                self(Wave(self.mu, QuantumState.random(), i))

            if time_limit and time.time() - start_time > time_limit:
                break
