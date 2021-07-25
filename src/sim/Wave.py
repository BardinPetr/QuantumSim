import struct
from typing import Optional

import numpy as np

from src.sim.QuantumState import QuantumState


class Wave:
    PACK_FORMAT = 'fffffQq?'  # mu, quantum state, time, photons count, is collapsed

    def __init__(self, mu: float, state: QuantumState, time: int = 0):
        self.mu: float = mu
        self.state: QuantumState = state
        self.time: int = time

        self.photons_count: Optional[int] = None

    def get_photons_count(self):
        if self.photons_count is not None:
            return self.photons_count

        self.photons_count = np.random.poisson(self.mu)

        return self.photons_count

    def __str__(self):
        return f'Wave with state: {self.state} and average photons count: {self.mu}'

    @staticmethod
    def from_bin(data: bytes):
        mu, qs0_real, qs0_imag, qs1_real, qs1_imag, time, photons_count, is_collapsed = struct.unpack(Wave.PACK_FORMAT,
                                                                                                      data)

        wave = Wave(
            mu,
            QuantumState((qs0_real + qs0_imag * 1j, qs1_real + qs1_imag * 1j)),
            time
        )

        if is_collapsed:
            wave.photons_count = photons_count

        return wave

    def to_bin(self):
        return struct.pack(
            Wave.PACK_FORMAT,
            self.mu,
            np.real(self.state.state[0]),
            np.imag(self.state.state[0]),
            np.real(self.state.state[1]),
            np.imag(self.state.state[1]),
            self.time,
            self.photons_count if self.photons_count is not None else 0,
            self.photons_count is not None
        )
