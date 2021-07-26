import random
import time
from collections import deque
from typing import Optional

from numpy.typing import NDArray

from src.math.QBERGen import *


class Postprocessing:
    EVENT_PROC_CASCADE_SEED = 'casc_s'
    EVENT_PROC_CASCADE_CALL = 'casc_c'
    EVENT_PROC_CASCADE_OPEN = 'casc_o'
    EVENT_PROC_CASCADE_END = 'casc_e'

    def __init__(self, bridge: 'Bridge', peer_ip: str, is_alice: bool):
        self.bridge = bridge
        self.peer_ip = peer_ip
        self.is_alice = is_alice

        self.key: Optional[NDArray] = None
        self.is_bob_process_key = False

        self.bridge.subscribe(self.EVENT_PROC_CASCADE_OPEN, self.response_to_calc_qber)
        self.bridge.subscribe(self.EVENT_PROC_CASCADE_END, self.bob_processing_finished)

    def bob_processing_finished(self, _):
        self.is_bob_process_key = True

    # def apply_toeplitz(self):

    def count_qber(self, percent_send=0.1):
        index_count = int(len(self.key) * percent_send)
        indexes = np.random.choice(self.key, index_count, replace=False)

        pid = self.bridge.call_rpc(self.peer_ip, self.EVENT_PROC_CASCADE_OPEN, indexes.tolist())
        alice_values = np.array(self.bridge.wait_for_result(pid))
        print(alice_values)
        bob_values = self.key[indexes]
        self.key = np.delete(self.key, indexes)

        return np.sum(alice_values != bob_values) / index_count

    def response_to_calc_qber(self, indexes):
        values = self.key[indexes]
        self.key = np.delete(self.key, indexes)
        print(values)
        return values.tolist()

    @staticmethod
    def count_parity(values: NDArray, part_len: int, errors: list):
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

    @staticmethod
    def apply_permutations(values: NDArray, permutations: list, dtype: str = 'bool'):
        new_values = np.zeros(values.shape, dtype=dtype)

        for permutation in permutations:
            new_values[permutation] = values

            values = new_values.copy()

        return values

    def get_error_bits(self, values, parts_len: int, errors: list, iteration: int):
        # ищем, в каком из БЛОКОВ у нас допущена ошибка
        parts_parity, parts_indexes = self.count_parity(values, parts_len, errors)

        pid = self.bridge.send_cascade_data(self.peer_ip,
                                            iteration, parts_indexes)
        alice_parts_parity = self.bridge.wait_for_result(pid)

        wrong_parts = np.where(alice_parts_parity != parts_parity)[0]

        working_parts_count = len(wrong_parts)

        wrong_bit_indexes = []
        parts_indexes = parts_indexes[wrong_parts]

        while working_parts_count > 0:
            ready_indexes = []

            middles = np.sum(parts_indexes, axis=1) // 2

            pid = self.bridge.send_cascade_data(self.peer_ip,
                                                iteration, np.stack([parts_indexes[:, 0], middles], axis=1))
            alice_parities = self.bridge.wait_for_result(pid)

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

    def postprocess_key(self, key: NDArray):
        self.key = key

        # print('here')

        if self.is_alice:
            while not self.is_bob_process_key:
                time.sleep(1e-3)

            self.is_bob_process_key = False

            return self.key

        data = key.copy().astype('bool')

        block_size = max(1, int(0.73 / self.count_qber()))

        max_seed = 2 ** 32 - 1
        seed = random.randint(0, max_seed)

        # отправляем сид перестановки Алисе
        pid = self.bridge.send_cascade_seed(self.peer_ip, seed)

        np.random.seed(seed)

        permutations = []
        reversed_permutations = deque()
        for i in range(3):
            permutations.append(np.random.permutation(len(data)))
            reversed_permutations.appendleft(
                self.apply_permutations(
                    np.arange(len(data)),
                    [permutations[-1]],
                    dtype=('uint32' if len(data) > 2 ** 16 - 1 else 'uint16')
                )
            )

        i = 0
        errors = []

        self.bridge.wait_for_result(pid)

        while i < 4:
            errors = self.get_error_bits(data, block_size, errors, i)

            data[errors] = ~data[errors]

            print(len(errors))

            if len(errors) == 0 or i == 0:
                if i == 3:
                    break

                data = self.apply_permutations(data, [permutations[i]])
                errors = []
                block_size *= 2

                i += 1
            else:
                block_size //= 2

                data = self.apply_permutations(data, [reversed_permutations[-i]])
                errors = reversed_permutations[-i][errors]

                i -= 1

        self.bridge.call_rpc(self.peer_ip, self.EVENT_PROC_CASCADE_END, [])

        return data
