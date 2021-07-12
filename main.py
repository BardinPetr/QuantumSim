from math import pi

from src.Clock import Clock
from src.sim.Devices.Detector import Detector
from src.sim.Devices.HalfWavePlate import HalfWavePlate
from src.sim.Devices.Laser import *
from asyncio import run


clock = Clock(25)

l = Laser((1, 0), clock)
hwp = HalfWavePlate(pi)
d = Detector(photon_out_cb=print)

l.forward_link(hwp)
hwp.forward_link(d)

run(l.start())