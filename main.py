import asyncio
import time

from src.Clock import Clock
from src.sim.Devices.HalfWavePlate import HalfWavePlate
from src.sim.Devices.Laser import *

clock = Clock(25)


def p(photon: Photon):
    print(photon)


l = Laser((1, 0))
hwp = HalfWavePlate(90)

l.forward_link(hwp)


def main(t):
    print(t)
    l()


clock.work(main)
