from typing import Tuple

from src.Clock import Clock
from src.sim.Device import *
from src.sim.Particles.Photon import Photon


class Laser(Device):
    def __init__(self, clock: Clock, polarization: Union[Tuple[complex, complex], None] = None,
                 name='Laser'):
        super().__init__(name)

        self.polarization = polarization
        self.clock = clock

    async def start(self):
        async for i in self.clock.work():
            if self.polarization is not None:
                self(Photon(QuantumState(self.polarization), i))
            else:
                self(Photon(QuantumState.random(), i))
