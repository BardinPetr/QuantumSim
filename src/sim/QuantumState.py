from random import random
from typing import Union, List, Tuple

import numpy as np
from numpy.typing import NDArray

BASIS_VERTICAL = (0, 1)
BASIS_HORIZONTAL = (1, 0)
BASIS_DIAGONAL = (0.5 ** 0.5, 0.5 ** 0.5)
BASIS_ANTIDIAGONAL = (0.5 ** 0.5, -(0.5 ** 0.5))
BASIS_RIGHT = (0.5 ** 0.5, (0.5 ** 0.5) * 1j)
BASIS_LEFT = (0.5 ** 0.5, -(0.5 ** 0.5) * 1j)

BASIS_HV = np.array([BASIS_HORIZONTAL, BASIS_VERTICAL])
BASIS_DA = np.array([BASIS_DIAGONAL, BASIS_ANTIDIAGONAL])
BASIS_RL = np.array([BASIS_RIGHT, BASIS_LEFT])

class QuantumState:
    def __init__(self, state: Union[NDArray, Tuple[complex, complex]]):
        self.state = np.array(state) if isinstance(state, List) else state

    def apply_operator(self, operator: NDArray):
        self.state = np.dot(self.state, operator)

    def read(self, basis: NDArray) -> NDArray:
        probability = np.absolute(
            self.get_probability_amplitude_for_basis(basis[0])
        ) ** 2

        self.state = basis[0] if random() < probability else basis[1]
        return self.state

    def get_probability_amplitude_for_basis(self, basis: NDArray) -> complex:
        return np.dot(
            np.conjugate(basis),
            self.state
        )

    def __str__(self):
        return str(self.state)
