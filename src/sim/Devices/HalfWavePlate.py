from src.sim.Device import Device, PhotonPart
from src.sim.Particles.Photon import Photon
from src.sim.QuantumState import *
from src.utils.algebra import rot_mat


class HalfWavePlate(Device):
    def __init__(self, angle: float, angle_control_cb=None,
                 name='Half wave plate'):
        super().__init__(name)

        self.angle_control_cb = (lambda _: angle) if angle_control_cb is None else angle_control_cb
        self.name += f" with angle {angle} rad".replace('\n', '')

    def process_full(self, photon: Union[Photon, None] = None) -> Union[Photon, PhotonPart]:
        angle = self.angle_control_cb(photon.time)
        photon.state.apply_operator(rot_mat(angle))
        return photon


if __name__ == "__main__":
    qs = QuantumState((1, 0))

    p = Photon(qs)

    print(p.state.read(BASIS_HV))

    hwp = HalfWavePlate(math.pi / 2)
    p = hwp.process_full(p)

    print(p.state.read(BASIS_HV))
