import numpy as np


def rot_mat(angle):
    a, b = np.sin(angle), np.cos(angle)
    return np.array([
        [b, -a],
        [a, b]
    ])
