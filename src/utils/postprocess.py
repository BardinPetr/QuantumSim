import random
import time
from collections import deque

from numpy.typing import NDArray

from src.sim.Math.QBERGen import *


def count_parity(values, part_len: int, errors: list):
    size = len(values)
    part_count = math.ceil(size / part_len)

    c = values.copy()

    c.resize(part_count * part_len)
    c = c.reshape((part_count, part_len))

    if len(errors) != 0:
        errors = np.array(errors, copy=True)

        errors //= part_len

        errors = np.unique(errors)

        indexes = np.dstack([errors * part_len, (errors + 1) * part_len])[0]

        if errors[-1] == part_count - 1:
            indexes[-1, 1] = size

        return np.count_nonzero(c[errors], axis=1) % 2, indexes

    indexes = np.dstack([np.arange(0, size, part_len), np.arange(part_len, size + part_len, part_len)])[0]
    indexes[-1, 1] = size

    return np.count_nonzero(c, axis=1) % 2, indexes


def apply_permutations(values: NDArray, permutations: list, dtype: str = 'bool'):  # 0.25
    new_values = np.zeros(values.shape, dtype=dtype)

    for permutation in permutations:
        new_values[permutation] = values

        values = new_values.copy()

    return values


def get_error_bits(
        values,
        parts_len: int,
        errors: list,
        iteration: int,
        send_cascade_data_cb: callable,
        wait_for_result_cb: callable
):
    # ищем, в каком из БЛОКОВ у нас допущена ошибка
    parts_parity, parts_indexes = count_parity(values, parts_len, errors)

    pid = send_cascade_data_cb(iteration, parts_indexes)
    alice_parts_parity = wait_for_result_cb(pid)

    wrong_parts = np.where(alice_parts_parity != parts_parity)[0]

    working_parts_count = len(wrong_parts)

    wrong_bit_indexes = []
    parts_indexes = parts_indexes[wrong_parts]

    while working_parts_count > 0:
        ready_indexes = []

        middles = np.sum(parts_indexes, axis=1) // 2

        pid = send_cascade_data_cb(iteration, np.stack([parts_indexes[:, 0], middles], axis=1))
        alice_parities = wait_for_result_cb(pid)

        for i in range(len(alice_parities)):
            parity = np.count_nonzero(values[parts_indexes[i, 0]:middles[i]]) % 2

            if parity != alice_parities[i]:
                parts_indexes[i, 1] = middles[i]
            else:
                parts_indexes[i, 0] = middles[i]

            if parts_indexes[i, 1] - parts_indexes[i, 0] == 1:
                wrong_bit_indexes.append(parts_indexes[i, 0])
                working_parts_count -= 1

                ready_indexes.append(i)

        parts_indexes = np.delete(parts_indexes, ready_indexes, axis=0)

    return wrong_bit_indexes


def postprocess_key(
        key: NDArray,
        qber: float,
        send_cascade_seed_cb: callable,
        send_cascade_data_cb: callable,
        wait_for_result_cb: callable
):
    data = key.copy().astype('bool')

    block_size = max(1, int(0.73 / qber))

    max_seed = 2 ** 32 - 1
    seed = random.randint(0, max_seed)

    # отпарвляем сид перестановки Алисе
    pid = send_cascade_seed_cb(seed)

    time.sleep(5)

    np.random.seed(seed)

    permutations = []
    reversed_permutations = deque()
    for i in range(3):
        permutations.append(np.random.permutation(len(data)))
        reversed_permutations.appendleft(
            apply_permutations(
                np.arange(len(data)),
                [permutations[-1]],
                dtype=('uint32' if len(data) > 2 ** 16 - 1 else 'uint16')
            )
        )

    i = 0
    errors = []

    wait_for_result_cb(pid)

    while i < 4:
        errors = get_error_bits(data, block_size, errors, i, send_cascade_data_cb, wait_for_result_cb)

        data[errors] = ~data[errors]

        print(len(errors))

        if len(errors) == 0 or i == 0:
            if i == 3:
                break

            data = apply_permutations(data, [permutations[i]])
            errors = []
            block_size *= 2

            i += 1
        else:
            block_size //= 2

            data = apply_permutations(data, [reversed_permutations[-i]])
            errors = reversed_permutations[-i][errors]

            i -= 1

    return data


def count_qber(key, another_key):
    return np.sum(key != another_key) / len(key)
