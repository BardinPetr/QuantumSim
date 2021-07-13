from typing import Union, List

from src.sim.Device import Device
from src.sim.Particles.Photon import Photon
from src.utils.rand import rand_bin


class Detector(Device):
    EVENT_DETECTION = 'event_detection'
    EVENT_BATCH_END = 'event_batch'

    photons = []

    def __init__(self,
                 dcr=0, eff=1, dt=0, batch_size=10,
                 name="Detector"):
        super().__init__(name)

        self.dcr = dcr
        self.eff = eff
        self.dt = dt
        self.batch_size = batch_size
        self.dead_time = 0

    def process_full(self, photon: Union[Photon, None] = None) -> None:
        if rand_bin(1 - self.eff):
            return None

        self.photons.append(photon)

        if len(self.photons) >= self.batch_size:
            self.process_batch()

        return None

    def process_batch(self):
        photons = sorted(self.photons, key=lambda p: p.time)
        self.photons = []

        photons_with_detector_dt = []

        for photon in photons:
            if self.dead_time <= photon.time:
                self.dead_time = photon.time + self.dt

                photons_with_detector_dt += [photon]
                self.emit(Detector.EVENT_DETECTION, photon)

        self.emit(Detector.EVENT_BATCH_END, photons_with_detector_dt)
