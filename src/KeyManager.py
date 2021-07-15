import os

import numpy as np
from numpy.typing import NDArray

from src.sim.Utils.BinaryFile import BinaryFile


class KeyManager:
    KEY_PATH: str = 'key'
    TEMP_KEY_PATH: str = 'temp_key'
    PSK_PATH: str = 'psk'
    CTRL_PATH = 'ctrl'

    KEY_FRAME_SIZE = 50
    KEY_BLOCK_SIZE = 1000

    def __init__(self, directory: str):
        # files
        self.key_file = BinaryFile(path=os.path.join(directory, self.KEY_PATH))
        self.temp_key_file = BinaryFile(path=os.path.join(directory, self.TEMP_KEY_PATH))
        self.psk_path = os.path.join(directory, self.PSK_PATH)
        self.ctrl_path = os.path.join(directory, self.CTRL_PATH)

        if not os.path.isfile(self.ctrl_path) or os.path.getsize(self.ctrl_path) == 0:
            self.save_cur_pos(0, 0)

        self.cur_pos, self.cur_psk_pos = self.load_cur_pos()

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

    def get(self, length: int, bits=True):
        length = length if bits else length * 8
        key = self.key_file.read(self.cur_pos, self.cur_pos + length - 1)

        self.cur_pos += length
        self.save_cur_pos()

        return key if bits else np.packbits(key)

    def append(self, key: NDArray):
        self.temp_key_file.append(key)

        if len(self.temp_key_file) > self.KEY_FRAME_SIZE:
            self.key_file.append(self.postprocess_key(self.temp_key_file.read_all()))
            self.temp_key_file.clear()

    def postprocess_key(self, data):
        return data


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
