from typing import Union, List, Tuple

import numpy as np
from numpy.typing import NDArray

from src.math.rand import *

BASIS_VERTICAL = np.array([0, 1])
BASIS_HORIZONTAL = np.array([1, 0])
BASIS_DIAGONAL = np.array([0.5 ** 0.5, 0.5 ** 0.5])
BASIS_ANTIDIAGONAL = np.array([0.5 ** 0.5, -(0.5 ** 0.5)])
BASIS_RIGHT = np.array([0.5 ** 0.5, (0.5 ** 0.5) * 1j])
BASIS_LEFT = np.array([0.5 ** 0.5, -(0.5 ** 0.5) * 1j])

BASIS_HV = np.array([BASIS_HORIZONTAL, BASIS_VERTICAL])
BASIS_DA = np.array([BASIS_DIAGONAL, BASIS_ANTIDIAGONAL])
BASIS_RL = np.array([BASIS_RIGHT, BASIS_LEFT])


class QuantumState:
    def __init__(self, state: Union[NDArray, Tuple[complex, complex]]):
        self.state = np.array(state) if isinstance(state, List) else state

    @staticmethod
    def random():
        nums = rand_nsphere(4)

        return QuantumState((
            nums[0] + nums[1] * 1j,
            nums[2] + nums[3] * 1j,
        ))

    def apply_operator(self, operator):
        self.state = np.dot(operator, self.state)

    def read(self, basis: NDArray) -> NDArray:
        probability = np.absolute(
            self.get_probability_amplitude_for_basis(basis[0])
        ) ** 2
        self.state = basis[0] if rand_bin(probability) else basis[1]
        return self.state

    def get_probability_amplitude_for_basis(self, basis: NDArray) -> complex:
        return np.dot(
            np.conjugate(basis),
            self.state
        )

    def __str__(self):
        return str(self.state)
