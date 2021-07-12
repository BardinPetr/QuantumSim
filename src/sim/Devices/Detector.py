from typing import Union

from src.sim.Device import Device
from src.sim.Particles.Photon import Photon
from random import random


class Detector(Device):
    photons = []

    def __init__(self, dcr=0, eff=1, dt=0, batch_size=100, photons_batch_ends_cbs=None, photon_in_cb=None, photon_out_cb=None, name="Detector"):
        super().__init__(photon_in_cb, photon_out_cb, name)
        self.photons_batch_ends_cbs = list() if photons_batch_ends_cbs is None else [photons_batch_ends_cbs]
        self.dcr = dcr
        self.eff = eff
        self.dt = dt
        self.batch_size = batch_size

    def process_full(self, photon: Union[Photon, None] = None) -> Union[Photon, None]:
        if random() > self.eff:
            return  # детектор по ошибке не задетектировал фотон

        self.photons.append(photon)

        if len(self.photons) >= self.batch_size:
            self.process_batch()

    def process_batch(self):
        photons = sorted(self.photons, key=lambda p: p.time)
        self.photons = []

        photons_with_detector_dt = []

        dead_time = -1
        for photon in photons:
            if dead_time <= photon.time:
                dead_time = photon.time + self.dt

                photons_with_detector_dt += [photon]

        for cb in self.photons_batch_ends_cbs:
            cb(photons_with_detector_dt)
