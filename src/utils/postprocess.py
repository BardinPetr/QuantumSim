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


def get_error_bits(values, parts_len: int, errors: list, iteration: int):
    global alice

    # ищем, в каком из БЛОКОВ у нас допущена ошибка
    parts_parity, parts_indexes = count_parity(values, parts_len, errors)

    alice_parts_parity = alice.get_parity(parts_indexes, iteration)

    wrong_parts = np.where(alice_parts_parity != parts_parity)[0]

    working_parts_count = len(wrong_parts)

    wrong_bit_indexes = []
    parts_indexes = parts_indexes[wrong_parts]

    while working_parts_count > 0:
        ready_indexes = []

        middles = np.sum(parts_indexes, axis=1) // 2

        alice_parities = alice.get_parity(np.stack([parts_indexes[:, 0], middles], axis=1), iteration)

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


def postprocess_key(key: NDArray, qber: float):
    data = key.copy().astype('bool')

    block_size = max(1, int(0.73 / qber))

    max_seed = 2 ** 32 - 1
    seed = random.randint(0, max_seed)

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

    # отпарвляем сид перестановки Алисе
    alice.send_permutations_to_alice(seed)

    i = 0
    errors = []
    i2 = 0

    while i < 4:
        # print(f'iteration #{i}')
        errors = get_error_bits(data, block_size, errors, i)

        data[errors] = ~data[errors]

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

        i2 += 1

    print(i2)

    return data


def count_qber(key, another_key):
    return np.sum(key != another_key) / len(key)


if __name__ == '__main__':
    qber = 0.05
    length = 10 ** 7

    key_without_errors = key_gen(length).astype('bool')
    key_with_errors = key_with_mist_gen(key_without_errors, qber).astype('bool')
    #                              0  1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27
    # key_with_errors =    np.array([0, 0, 0, 0, 0, 0, 1, 1], dtype='bool')
    # key_without_errors = np.array([0, 0, 0, 1, 0, 0, 1, 0], dtype='bool')

    print('errors count:', np.sum(key_with_errors != key_without_errors))
    print('qber:', count_qber(key_with_errors, key_without_errors))

    alice = Bridge(key_without_errors.copy())

    t = time.time()
    corrected_key = postprocess_key(key_with_errors, qber)
    print(time.time() - t)

    print('errors count:', np.sum(corrected_key != alice.key_after_iterations[-1]))
    print('qber:', np.sum(corrected_key != alice.key_after_iterations[-1]) / len(corrected_key))

    print('leaked bits:', alice.leaked_bits_count)
