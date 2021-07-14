import asyncio

import numpy as np

from src.sim.Devices.Detector import Detector
from src.sim.Devices.HalfWavePlate import HalfWavePlate
from src.sim.Devices.Laser import *
from src.sim.QuantumState import BASIS_HV
from src.utils.rand import rand_bin

# bases for Alice's and Bob's measurements
bases = [
    [],
    []
]

laser_period = 10


# function for Alice and Bob that give basis and write it to bases array
def choose_basis(i):
    basis = 1 / 2 if rand_bin(0.5) else 0

    bases[i].append(basis)

    return basis


clock = Clock(laser_period, real_period=10e-6)

# information, that Alice will send to Bob
alice_bits = np.random.randint(2, size=500)
alice_bits_pointer = -1


# get Alice bit for transmission
def get_alice_bit():
    global alice_bits_pointer
    alice_bits_pointer += 1

    return alice_bits[alice_bits_pointer]


# scheme
laser = Laser(clock, (1, 0), mu=1)

alice_hwp = HalfWavePlate(0, angle_control_cb=lambda _: np.pi * (get_alice_bit() + choose_basis(0)) / 4)
laser.forward_link(alice_hwp)

bob_hwp = HalfWavePlate(0, angle_control_cb=lambda _: -np.pi * choose_basis(1) / 4)
alice_hwp.forward_link(bob_hwp)

detector = Detector()
bob_hwp.forward_link(detector)

# information, that bob receive from Alice
bob_last_wave_time = -laser_period
bob_info = []


def bob_detect_wave(wave: Wave):
    global bob_info, bob_last_wave_time

    if bob_last_wave_time < wave.time - laser_period:
        missed_count = (wave.time - bob_last_wave_time) // laser_period - 1

        bob_info += [3] * missed_count

    state = wave.state.read(BASIS_HV)
    bob_info.append(state[1])

    bob_last_wave_time = wave.time


detector.subscribe(Detector.EVENT_DETECTION, bob_detect_wave)

# first argument is time, that laser will emit light
asyncio.run(laser.start(1))

# sift key
alice_sifted_key = []
bob_sifted_key = []

for i in range(len(bob_info)):
    if bases[0][i] != bases[1][i] or bob_info[i] == 3:
        continue

    bob_sifted_key.append(bob_info[i])
    alice_sifted_key.append(alice_bits[i])

# write statistics
print("Bases, that Bob and Alice chose for measurement")
print(bases[0])
print(bases[1])

print()

print("Information, that Bob receive from waves")
print(bob_info)

print()

print("Bob's sifted key:  ", bob_sifted_key[:25])
print("Alice's sifted key:", alice_sifted_key[:25])

print()

print("E(μ):", len(bob_info))
print("Q(μ):", len(list(filter(lambda x: x != 3, bob_info))) / len(bob_info))
