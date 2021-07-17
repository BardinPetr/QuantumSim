import math

from src.sim.data.AliceHardwareParams import AliceHardwareParams
from src.sim.data.BobHardwareParams import BobHardwareParams


def h(x):
    if x <= 0 or x >= 1:
        return 0
    return -x * math.log2(x) - (1 - x) * math.log2(1 - x)


def simulate_bb84(
        alice_params: AliceHardwareParams,
        bob_params: BobHardwareParams,
        fiber_length: float = 50,
        delta_opt: float = 0.2,
        prob_opt: float = 0.05,
        f_ec: float = 1.2
):
    """
    dcr = 5  # в герцах теневой счет
    f = 5 * 10 ** 6  # частота генерации сигнала
    fiber_length = 50  # Длина проводов в км
    prob_opt = 0.05  # Вероятность прохождения фотона с учетом всех элементов
    n = 0.1  # Квантовая эффективность
    m = 0.2  # среднее число фотонов
    td = 5 * 10 ** -6  # длительность восстановления детектора
    """

    s_opt = delta_opt * fiber_length  # в ДБ степень затухания сигнала
    t = 10 ** (- s_opt / 10)  # Т оптическое
    Q = 2 * bob_params.pdc + 1 - math.e ** (-t * bob_params.eff * alice_params.mu)
    qber = (bob_params.pdc + prob_opt * (1 - math.e ** (-t * bob_params.eff * alice_params.mu))) / Q
    r_raw = alice_params.laser_freq * Q / (1 + bob_params.dt * alice_params.laser_freq * Q)
    r_sift = r_raw / 2

    Q1 = Q - 1 + (math.e ** (-alice_params.mu * bob_params.eff) - bob_params.eff * math.e ** (-alice_params.mu)) / max(1 - bob_params.eff, 10e-8)

    E1 = qber * Q / Q1

    r_sec = r_sift * (Q1 / Q * (1 - h(E1)) - f_ec * h(qber))

    return r_sift, qber, Q, r_sec
