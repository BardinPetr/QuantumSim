from numpy.random import uniform


def rand_uni():
    return uniform(0, 1)


def rand_bin(prob):
    return rand_uni() < prob
