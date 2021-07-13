import math

from src.sim.Device import Device
from src.sim.Particles.Photon import Photon
from src.sim.QuantumState import *
from src.utils.algebra import rot_mat


class HalfWavePlate(Device):
    def __init__(self, angle: float,
                 photon_in_cb=None, photon_out_cb=None,
                 name='Half wave plate'):
        super().__init__(photon_in_cb, photon_out_cb, name)

        self.operator = rot_mat(angle)
        self.name += f" with angle {angle} rad".replace('\n', '')

    def process_full(self, photon: Union[Photon, None] = None) -> Union[Photon, None]:
        photon.state.apply_operator(self.operator)

        return photon


if __name__ == "__main__":
    qs = QuantumState((1, 0))

    p = Photon(qs)

    print(p.state.read(BASIS_HV))

    hwp = HalfWavePlate(math.pi / 2)
    p = hwp.process_full(p)

    print(p.state.read(BASIS_HV))
