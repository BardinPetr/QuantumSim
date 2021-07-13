import asyncio
import time
from math import pi

from src.sim.Devices.Detector import Detector
from src.sim.Devices.Laser import *
from src.sim.Devices.Polarizer import Polarizer

cnts = [[0, 0], [0, 0]]
LOG = False


def L(*args, **kwargs):
    if LOG:
        print(*args, **kwargs)


def cnt(x, exp, i, log=0):
    L(f"{log} {x}")
    global cnts
    cnts[exp][i] += 1


clock = Clock(25, real_period=10e-6)
# clock = Clock(25, real_period=10)


laser1 = Laser(clock)
laser1.subscribe(Laser.EVENT_PH_IN, lambda x: cnt(x, 0, 0, 0))

polarizer11 = Polarizer(0)
laser1.forward_link(polarizer11)

polarizer12 = Polarizer(pi / 2)
polarizer11.forward_link(polarizer12)

detector1 = Detector()
detector1.subscribe(Detector.EVENT_DETECTION, lambda x: cnt(x, 0, 1, 4))
polarizer12.forward_link(detector1)

laser2 = Laser(clock)
laser2.subscribe(Laser.EVENT_PH_IN, lambda x: cnt(x, 1, 0, 0))

polarizer21 = Polarizer(0)
laser2.forward_link(polarizer21)

polarizer22 = Polarizer(pi / 4, angle_control_cb=lambda x: pi / 4 if x > 100000 else 0)
polarizer21.forward_link(polarizer22)

polarizer23 = Polarizer(pi / 2)
polarizer22.forward_link(polarizer23)

detector2 = Detector()
detector2.subscribe(Detector.EVENT_DETECTION, lambda x: cnt(x, 1, 1, 4))
polarizer23.forward_link(detector2)


def check():
    while True:
        print("%.5f %.5f" % (cnts[0][1] / cnts[0][0] if cnts[0][0] > 0 else 0,
                             cnts[1][1] / cnts[1][0] if cnts[1][0] > 0 else 0), cnts)
        time.sleep(1)


async def main():
    await asyncio.gather(asyncio.to_thread(check), laser1.start(), laser2.start())


asyncio.run(main())
