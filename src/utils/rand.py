import math
import random

import numpy as np
from numpy.random import *


def rand_uni():
    return uniform(0, 1)


def rand_bin(prob):
    return rand_uni() < prob


def rand_nsphere(n):
    v = normal(size=n)
    return v / np.linalg.norm(v)
