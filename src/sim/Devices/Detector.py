from typing import Union

from src.sim.Device import Device
from src.sim.Particles.Photon import Photon


class Detector(Device):
    def __init__(self, dcr=0, eff=1, dt=0, photon_in_cb=None, photon_out_cb=None, name="Detector"):
        super().__init__(photon_in_cb, photon_out_cb, name)
        self.dcr = dcr
        self.eff = eff
        self.dt = dt

    def process_full(self, photon: Union[Photon, None] = None) -> Union[Photon, None]:
        return super().process_full(photon)
