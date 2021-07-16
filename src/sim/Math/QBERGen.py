import math

import numpy as np

from src.sim.Data.HardwareParams import HardwareParams


def h(x):
    if x <= 0 or x >= 1:
        return 0
    return -x * math.log2(x) - (1 - x) * math.log2(1 - x)


def key_gen(length):
    rand_arr = np.array(np.random.rand(length) > 0.5, dtype='int8')
    return rand_arr


def key_with_mist_gen(base_key, qber):
    mist_arr = np.array(np.random.rand(len(base_key)) < qber, dtype='int8')
    mist_arr = mist_arr + base_key
    mist_arr = mist_arr % 2
    return mist_arr


def simulate_bb84(params: HardwareParams, f_ec: float = 1.2):
    """
    dcr = 5  # в герцах теневой счет
    f = 5 * 10 ** 6  # частота генерации сигнала
    line_length = 50  # Длина проводов в км
    Popt = 0.05  # Вероятность прохождения фотона с учетом всех элементов
    n = 0.1  # Квантовая эффективность
    m = 0.2  # среднее число фотонов
    td = 5 * 10 ** -6  # длительность восстановления детектора
    """
    s_opt = params.delta_opt * params.fiber_length  # в ДБ степень затухания сигнала
    t = 10 ** (- s_opt / 10)  # Т оптическое, transmission
    Q = 2 * params.pdc + 1 - math.e ** (-t * params.eff * params.mu)
    qber = (params.pdc + params.prob_opt * (1 - math.e ** (-t * params.eff * params.mu))) / Q
    r_raw = params.laser_freq * Q / (1 + params.dt * params.laser_freq * Q)
    r_sift = r_raw / 2

    Q1 = Q - 1 + (math.e ** (-params.mu * params.eff) - params.eff * math.e ** (-params.mu)) / (1 - params.eff)
    E1 = qber * Q / Q1

    r_sec = r_sift * (Q1 / Q * (1 - h(E1)) - f_ec * h(qber))

    return r_sift, qber, Q, r_sec


if __name__ == "__main__":
    # generate()
    pass
