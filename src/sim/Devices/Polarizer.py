import math

from src.sim.Device import Device
from src.sim.Particles.Photon import Photon
from src.sim.QuantumState import *
from src.utils.math import rot_mat


class Polarizer(Device):
    def __init__(self, angle: float):
        super().__init__(name='Linear polarizer')

        self.basis = BASIS_HV * rot_mat(angle)
        self.name += f" with basis {self.basis}".replace('\n', '')

    def process_full(self, photon: Photon) -> Union[Photon, None]:
        state = photon.state.read(self.basis)
        if np.allclose(state, self.basis[0], rtol=10e-6):
            return photon
        else:
            return None


if __name__ == "__main__":
    st = QuantumState((1 / math.sqrt(2), 1 / math.sqrt(2)))
    p = Photon(st)

    # print(p.state.read(np.array([BASIS_VERTICAL, BASIS_HORIZONTAL])))
    print(p.state)

    dev = Polarizer(0)
    print(dev)

    p = dev.process_full(p)

    print(p.state)

    print(p.state.read(np.array([BASIS_VERTICAL, BASIS_HORIZONTAL])))
