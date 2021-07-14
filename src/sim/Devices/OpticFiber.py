from typing import Union

import numpy as np

from src.sim.Device import Device
from src.sim.QuantumState import QuantumState
from src.sim.Wave import Wave
from src.utils.algebra import rot_mat
from src.utils.rand import rand_bin


class OpticFiber(Device):
    def __init__(self, length, deltaopt=0, probopt=0, name="Optic fiber"):
        super().__init__(name)

        self.probopt = probopt
        self.deltaopt = deltaopt
        self.length = length

    def process_full(self, wave: Wave) -> Union[Wave, None]:
        wave.mu *= 10 ** (-self.deltaopt * self.length / 10)

        if rand_bin(self.probopt):
            wave.state.apply_operator(rot_mat(np.pi / 2))

        return wave
