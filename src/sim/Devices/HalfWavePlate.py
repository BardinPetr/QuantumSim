import math

from src.sim.Device import Device
from src.sim.Particles.Photon import Photon
from src.sim.QuantumState import *


class HalfWavePlate(Device):
    def __init__(self, angle: float,
                 photon_in_cb=None, photon_out_cb=None,
                 name='Half wave plate'):
        super().__init__(photon_in_cb, photon_out_cb, name)

        sin = math.sin(angle)
        cos = math.cos(angle)

        self.operator = np.array([
            [cos, sin],
            [-sin, cos]
        ])  # TODO: разобраться зачем там фазовый множитель

    def process_full(self, photon: Union[Photon, None] = None) -> Union[Photon, None]:
        photon.state.apply_operator(self.operator)

        return photon


if __name__ == "__main__":
    qs = QuantumState((1, 0))

    p = Photon(qs)

    print(p.state.read([
        BASIS_VERTICAL, BASIS_HORIZONTAL
    ]))

    hwp = HalfWavePlate(math.pi / 2)
    p = hwp.process_full(p)

    print(p.state.read([
        BASIS_VERTICAL, BASIS_HORIZONTAL
    ]))
