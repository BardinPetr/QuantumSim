from random import random
from typing import Tuple

import numpy as np

BASIS_VERTICAL = (0, 1)
BASIS_HORIZONTAL = (1, 0)
BASIS_DIAGONAL = (0.5 ** 0.5, 0.5 ** 0.5)
BASIS_ANTIDIAGONAL = (0.5 ** 0.5, -(0.5 ** 0.5))
BASIS_RIGHT = (0.5 ** 0.5, (0.5 ** 0.5) * 1j)
BASIS_LEFT = (0.5 ** 0.5, -(0.5 ** 0.5) * 1j)


class QuantumState:
    def __init__(self, state: Tuple[complex, ...]):
        self.state = state

    def apply_operator(self, operator):
        self.state = np.dot(self.state, operator)

    def read(self, basis) -> tuple:
        probability = np.absolute(
            self.get_probability_amplitude_for_basis(basis[0])
        ) ** 2

        self.state = basis[0] if random() < probability else basis[1]

        return self.state

    def get_probability_amplitude_for_basis(self, basis) -> complex:
        return np.dot(
            np.conjugate(basis),
            self.state
        )

    def __str__(self):
        return str(self.state)
