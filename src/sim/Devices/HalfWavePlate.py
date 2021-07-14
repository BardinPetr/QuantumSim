import numpy as np

from src.sim.Device import Device
from src.sim.Wave import Wave
from src.sim.QuantumState import *
from src.utils.algebra import rot_mat


class HalfWavePlate(Device):
    def __init__(self, angle: float, angle_control_cb=None,
                 name='Half wave plate'):
        super().__init__(name)

        self.angle_control_cb = (lambda _: angle) if angle_control_cb is None else angle_control_cb
        self.name += f" with angle {angle} rad".replace('\n', '')

    def process_full(self, wave: Union[Wave, None] = None) -> Union[Wave]:
        angle = self.angle_control_cb(wave.time)

        wave.state.apply_operator(rot_mat(angle * 2))  # * np.exp(-1j * np.pi / 2)
        return wave


if __name__ == "__main__":
    qs = QuantumState((1, 0))

    p = Wave(1, qs)

    print(p.state.read(BASIS_HV))

    hwp = HalfWavePlate(math.pi / 8)
    p = hwp.process_full(p)

    print(p.state.read(BASIS_HV))
