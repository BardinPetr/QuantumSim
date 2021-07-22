from collections import deque

import matplotlib.pyplot as plt
import numpy as np
from numpy.typing import NDArray

from src.sim.Math.QBERGen import *


def count_parity(values, part_len: int):
    parts_parity = []
    last_part_index = 0
    parts_indexes = []
    parity = 0

    for (index, value) in enumerate(values):
        parity += value

        if not (index + 1) % part_len:
            parts_parity.append(parity % 2)
            parts_indexes.append([last_part_index, index + 1])
            parity = 0

            last_part_index = index + 1

    if len(values) % part_len:
        parts_parity.append(parity % 2)
        parts_indexes.append([last_part_index, len(values)])

    return parts_parity, parts_indexes


def get_alice_parity(indexes: list):
    global alice_key

    return np.sum(alice_key[indexes]) % 2


def apply_permutations(values: NDArray, permutations: list, dtype: str = 'bool'):
    new_values = np.zeros(values.shape, dtype=dtype)

    for permutation in permutations:
        new_values[permutation] = values
        values = np.copy(new_values)

    return values


def apply_permutations_on_indexes(indexes: list, permutations: list):
    for permutation in permutations:
        indexes = permutation[indexes]

    return indexes


def get_error_bits(values, begin, end, parts_len: int, permutations: list, reversed_permutations: list):
    parts_parity, parts_indexes = count_parity(values[begin:end], parts_len)

    parts_parity = np.array(parts_parity)

    alice_parts_parity = []
    for start, end in parts_indexes:
        alice_parts_parity.append(
            get_alice_parity(
                apply_permutations_on_indexes(
                    list(range(begin + start, begin + end)),
                    reversed_permutations
                )
            )
        )

    wrong_parts = np.where(alice_parts_parity != parts_parity)[0]

    if parts_len == 1:
        return (begin + wrong_parts).tolist()

    wrong_bits = []

    for wrong_part in wrong_parts:
        next_begin = begin + wrong_part * parts_len
        next_end = next_begin + parts_len

        wrong_bits += get_error_bits(values, next_begin, next_end, int(parts_len / 2), permutations,
                                     reversed_permutations)

    return wrong_bits


def postprocess_key(key: NDArray, qber):
    data = key

    block_size = max(1, int(0.73 / qber))

    permutations = []
    reversed_permutations = deque()

    for i in range(4):
        errors = get_error_bits(data, 0, len(data), block_size, permutations, reversed_permutations)

        data[errors] = ~data[errors]

        permutations.append(np.random.permutation(len(data)))
        reversed_permutations.appendleft(
            apply_permutations(np.arange(len(data)), [permutations[-1]], dtype='uint32')
        )

        data = apply_permutations(data, [permutations[-1]])

    return apply_permutations(data, reversed_permutations)


def count_qber(key, another_key):
    return np.sum(key != another_key) / len(key)


if __name__ == '__main__':
    errors_count = []
    step = 0.05

    for qber in np.arange(step, 0.5, step):
        length = 500000

        key_without_errors = key_gen(length)
        key_with_errors = key_with_mist_gen(key_without_errors, qber)

        print('qber:', count_qber(key_with_errors, key_without_errors))

        alice_key = key_without_errors

        corrected_key = postprocess_key(key_with_errors, qber)

        print('errors count:', np.sum(corrected_key != key_without_errors))
        errors_count.append(np.sum(corrected_key != key_without_errors))

    plt.plot(np.arange(step, 0.5, step), errors_count)
    plt.show()
