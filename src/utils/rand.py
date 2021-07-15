from random import SystemRandom

from numpy.linalg import norm
from numpy.random import *

ur = SystemRandom()


def rand_uni():
    return ur.uniform(0, 1)


def rand_bin(prob=0.5):
    return rand_uni() < prob


def rand_nsphere(n):
    v = normal(size=n)
    return v / norm(v)
