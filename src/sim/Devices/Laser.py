from src.sim.Device import *


class Laser(Device):
    def __init__(self, polarization):
        super().__init__(name='Laser')

        self.polarization = polarization

    def process_full(self, photon: Union[Photon, None] = None) -> Union[Photon, None]:
        qs = QuantumState(self.polarization)
        photon = Photon(qs)

        return photon
