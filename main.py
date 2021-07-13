import asyncio

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


# function for Alice and Bob that give basis and write it to bases array
def choose_basis(i):
    basis = 1 / 2 if rand_bin(0.5) else 0

    bases[i].append(basis)

    return basis


clock = Clock(25, real_period=10e-6)

# information, that Alice will send to Bob
alice_bit = 0
# photons, that Alice sent
alice_photons_time = []

# scheme
laser = Laser(clock, (1, 0))
laser.subscribe(Laser.EVENT_OUT, lambda w: alice_photons_time.append(w.time))

alice_hwp = HalfWavePlate(0, angle_control_cb=lambda _: np.pi * (alice_bit + choose_basis(0)) / 4)
laser.forward_link(alice_hwp)

bob_hwp = HalfWavePlate(0, angle_control_cb=lambda _: -np.pi * choose_basis(1) / 4)
alice_hwp.forward_link(bob_hwp)

detector = Detector(eff=0.5)
bob_hwp.forward_link(detector)

# information, that bob receive from Alice
bob_photons_time = []
bob_info = []


def bob_detect_wave(wave: Wave):
    state = wave.state.read(BASIS_HV)

    bob_photons_time.append(wave.time)
    bob_info.append(state[1] == 1)


detector.subscribe(Detector.EVENT_DETECTION, bob_detect_wave)

# first argument is time, that laser will emit light
asyncio.run(laser.start(10))

# Uncomment for tests
# alice_photons_time = [1, 2, 3, 4, 5, 6]
# bob_photons_time = [1, 3, 4, 5]
#
# bases = [
#     [0, 0, 0, 0, 0, 0],
#     [0, 1, 1, 0, 1, 0]
# ]
#
# bob_info = [False, False, False, True]

# sift key
sifted_info = []
bob_index = 0
for (i, t) in enumerate(alice_photons_time):
    if bases[0][i] != bases[1][i]:
        continue

    while bob_photons_time[bob_index] < t and bob_index < len(bob_photons_time) - 1:
        bob_index += 1

    if bob_photons_time[bob_index] == t:
        sifted_info.append(bob_info[bob_index])


# write statistics
print("Time, when waves was emitted and received")
print(alice_photons_time)
print(bob_photons_time)

print()

print("Bases, that Bob and Alice chose for measurement")
print(bases[0])
print(bases[1])

print()

print("Information, that Bob receive from waves")
print(bob_info)

print()

print("Sifted key")
print(sifted_info)

print()

print("E(μ):", len(alice_photons_time))
print("Q(μ):", len(bob_info) / len(alice_photons_time))
