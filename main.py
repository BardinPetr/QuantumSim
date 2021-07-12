import threading
from math import pi

from src.sim.Devices.Detector import Detector
from src.sim.Devices.Laser import *
from asyncio import run

clock = Clock(25)


# TODO: заменить эту штуку на нормальную
class Polarizer(Device):
    def __init__(self, angle, photon_in_cb=None, photon_out_cb=None, name="Polarizer"):
        super().__init__(photon_in_cb, photon_out_cb, name)


# В теории, эта схема должна заработать сразу же после добавления Polarizer. Она запускает в 2 потока 2 лазера
laser1 = Laser((0, 1), clock)
polarizer11 = Polarizer(pi / 4)
polarizer12 = Polarizer(pi / 2)
detector1 = Detector(photons_batch_ends_cbs=lambda photons: print(f'Detected {len(photons)}% of photons on detector 1'))

laser1.forward_link(polarizer11)
polarizer11.forward_link(polarizer12)
polarizer12.forward_link(detector1)

laser2 = Laser((0, 1), clock)
polarizer21 = Polarizer(pi / 2)
detector2 = Detector(photons_batch_ends_cbs=lambda photons: print(f'Detected {len(photons)}% of photons on detector 2'))

laser2.forward_link(polarizer21)
polarizer21.forward_link(detector2)

threading.Thread(target=lambda: run(laser1.start())).start()
threading.Thread(target=lambda: run(laser2.start())).start()
