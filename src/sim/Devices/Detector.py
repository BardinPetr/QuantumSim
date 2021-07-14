from typing import Union

from src.sim.MainDevices.Device import Device
from src.sim.QuantumState import QuantumState
from src.sim.Wave import Wave
from src.utils.rand import rand_bin


class Detector(Device):
    EVENT_DETECTION = 'event_detection'

    def __init__(self, pdc=0, eff=1, dt=0, name="Detector"):
        super().__init__(name)

        self.pdc = pdc
        self.eff = eff
        self.dt = dt
        self.dead_time = 0

    def process_full(self, wave: Union[Wave] = None) -> None:
        if rand_bin(2 * self.pdc):
            return self.emit(self.EVENT_DETECTION, Wave(1, QuantumState.random(), wave.time))

        n = wave.get_photons_count()

        if rand_bin((1 - self.eff) ** n) or self.dead_time > wave.time:
            return

        self.dead_time = wave.time + self.dt

        self.emit(self.EVENT_DETECTION, wave)
