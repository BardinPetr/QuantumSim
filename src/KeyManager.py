import os

import numpy as np
import queue
from numpy.typing import NDArray

from src.sim.MainDevices.Eventable import Eventable
from src.sim.Utils.BinaryFile import BinaryFile
from src.utils.postprocess import postprocess_key, apply_permutations


class KeyManager(Eventable):
    EVENT_NOT_ENOUGH_PSK = 'enep'
    EVENT_UPDATED_KEY = 'key_updated'

    KEY_PATH: str = 'key'
    TEMP_KEY_PATH: str = 'temp_key'
    PSK_PATH: str = 'psk'
    CTRL_PATH = 'ctrl'

    KEY_FRAME_SIZE = 10 ** 4
    PSK_SIZE = 5000

    def __init__(self, directory: str, is_bob=False):
        super().__init__()
        self.is_bob = is_bob

        # files
        self.key_file = BinaryFile(path=os.path.join(directory, self.KEY_PATH))
        self.temp_key_file = BinaryFile(path=os.path.join(directory, self.TEMP_KEY_PATH))
        self.psk_file = BinaryFile(path=os.path.join(directory, self.PSK_PATH))
        # self.psk_path = os.path.join(directory, self.PSK_PATH)
        self.ctrl_path = os.path.join(directory, self.CTRL_PATH)

        self.bridge_methods = {}

        if not os.path.isfile(self.ctrl_path) or os.path.getsize(self.ctrl_path) == 0:
            self.save_cur_pos(0, 0)

        self.cur_pos, self.cur_psk_pos = self.load_cur_pos()

        self.key = queue.Queue()

        self.leaked_bits_count = 0
        self.permutations = []
        self.key_after_iterations = []

    def get_parity(self, data):
        iteration, indexes = data[0], np.array(data[1])

        self.leaked_bits_count += 1

        parities = []
        for begin, end in indexes:
            parities.append(np.count_nonzero(self.key_after_iterations[iteration][begin:end]) % 2)

        # print('alice', parities)

        return parities

    def update_permutations(self, seed):
        key = self.key.get()

        np.random.seed(seed)

        self.key_after_iterations.append(key)

        for i in range(3):
            self.permutations.append(np.random.permutation(len(key)))

            self.key_after_iterations.append(apply_permutations(key, self.permutations))

        self.key_file.append(self.key_after_iterations[-1])

    def calc_qber(self):
        return 0.05

    def set_bridge_methods(self, cb: dict):
        self.bridge_methods = cb

    def load_cur_pos(self):
        with open(self.ctrl_path, 'r+') as f:
            return [int(i) for i in f.readlines()]

    def save_cur_pos(self, a=None, b=None):
        a = self.cur_pos if a is None else a
        b = self.cur_psk_pos if b is None else b
        with open(self.ctrl_path, 'w+') as f:
            f.write(f"{a}\n{b}\n")

    def clear(self):
        self.key_file.clear()

    def get(self, length_bits: int, return_bits=True, psk=False):
        # key = np.zeros(length_bits, dtype='uint8')
        # return key if return_bits else np.packbits(key)

        if psk:
            key = self.psk_file.read(self.cur_psk_pos, self.cur_psk_pos + length_bits - 1)
            self.cur_psk_pos += length_bits
            self.check_psk()
        else:
            key = self.key_file.read(self.cur_pos, self.cur_pos + length_bits - 1)
            self.cur_pos += length_bits

        self.save_cur_pos()

        return key if return_bits else np.packbits(key)

    def append(self, key: NDArray):
        self.temp_key_file.append(key)

        if len(self.temp_key_file) > self.KEY_FRAME_SIZE:
            key_part = self.temp_key_file.read_all()
            self.temp_key_file.clear()
            for i in range(0, len(key_part), self.KEY_FRAME_SIZE):
                if i + self.KEY_FRAME_SIZE <= len(key_part):
                    if self.is_bob:
                        self.key_file.append(
                            postprocess_key(
                                key_part[i:i + self.KEY_FRAME_SIZE],
                                self.calc_qber(),
                                self.bridge_methods['send_cascade_seed'],
                                self.bridge_methods['send_cascade_data'],
                                self.bridge_methods['wait_for_result']
                            )
                        )
                    else:
                        self.key.put(key_part[i:i + self.KEY_FRAME_SIZE])
                else:
                    self.temp_key_file.append(key_part[i:])
                    break
        self.emit(KeyManager.EVENT_UPDATED_KEY)

    def available(self, psk=False):
        # return 12321312312
        return len(self.psk_file if psk else self.key_file) - (self.cur_psk_pos if psk else self.cur_pos)

    def update_psk(self, length):
        self.psk_file.append(self.get(length))

    def check_psk(self):
        if len(self.psk_file) <= self.cur_psk_pos:
            self.emit(KeyManager.EVENT_NOT_ENOUGH_PSK, KeyManager.PSK_SIZE)


if __name__ == '__main__':
    key = KeyManager('/home/petr/Desktop/QuantumLink/data/alice/')

    # key.clear()
    # print()
    # key.append(np.random.uniform(0, 1, 10000) > 0.5)
    # key.append(np.array([True, False, True, True], dtype='bool'))
    # key.append(np.array([True, False, True, True, False], dtype='bool'))
    # print(key.get(5))
    # print(key.get(3))
    #
    # del key
    # c[0:5] = [0, 0, 0, 0, 0]
    # c.bin
    # print(c.bin)

    # print(key.get(10))
