from typing import Union

from src.sim.Device import Device
from src.sim.Particles.Photon import Photon
from src.utils.rand import rand_bin


class Detector(Device):
    photons = []

    def __init__(self,
                 dcr=0, eff=1, dt=0, batch_size=10,
                 batch_end_cb=None, detection_cb=None, photon_in_cb=None, photon_out_cb=None,
                 name="Detector"):
        super().__init__(photon_in_cb, photon_out_cb, name)

        self.batch_end_cb = batch_end_cb
        self.detection_cb = detection_cb
        self.dcr = dcr
        self.eff = eff
        self.dt = dt
        self.batch_size = batch_size
        self.dead_time = 0

    def process_full(self, photon: Union[Photon, None] = None) -> Union[Photon, None]:
        if rand_bin(1 - self.eff):
            return

        self.photons.append(photon)

        if len(self.photons) >= self.batch_size:
            self.process_batch()

    def process_batch(self):
        photons = sorted(self.photons, key=lambda p: p.time)
        self.photons = []

        photons_with_detector_dt = []

        for photon in photons:
            if self.dead_time <= photon.time:
                self.dead_time = photon.time + self.dt

                photons_with_detector_dt += [photon]
                if self.detection_cb is not None:
                    self.detection_cb(photon)

        if self.batch_end_cb is not None:
            self.batch_end_cb(photons_with_detector_dt)
