from numpy import sin, cos, array


def rot_mat(angle):
    a, b = sin(angle), cos(angle)
    return array([
        [b, -a],
        [a, b]
    ])
