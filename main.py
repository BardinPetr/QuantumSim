from asyncio import run
from math import pi

from src.sim.Devices.Detector import Detector
from src.sim.Devices.HalfWavePlate import HalfWavePlate
from src.sim.Devices.Laser import *

clock = Clock(25)

l = Laser((1, 0), clock)
hwp = HalfWavePlate(pi)
d = Detector(photon_out_cb=print)

l.forward_link(hwp)
hwp.forward_link(d)

run(l.start())
