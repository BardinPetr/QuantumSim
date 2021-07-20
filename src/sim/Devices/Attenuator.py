from src.sim.MainDevices.Device import Device
from src.sim.QuantumState import *
from src.sim.Wave import Wave


class Attenuator(Device):
    def __init__(self, attenuation: float, name='Attenuation'):
        super().__init__(name)

        self.attenuation = attenuation

    def process_full(self, wave: Union[Wave, None] = None) -> Union[Wave]:
        wave.mu *= 10 ** (-self.attenuation / 10)
        return wave
