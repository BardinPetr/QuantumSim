import os

import numpy as np
from numpy.typing import NDArray

from src.sim.Utils.BinaryFile import BinaryFile


class KeyManager:
    def __init__(self, path, psk_path, ctrl_path, remove_after_use=True):
        self.key_file = BinaryFile(path=path)
        self.psk_path = psk_path
        self.ctrl_path = ctrl_path
        self.remove_after_use = remove_after_use

        if not os.path.isfile(ctrl_path) or os.path.getsize(ctrl_path) == 0:
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

    def get(self, length: int):
        key = self.key_file.read(self.cur_pos, self.cur_pos + length - 1)

        self.cur_pos += length
        self.save_cur_pos()

        return key

    def append(self, key: NDArray):
        self.key_file.append(key)


if __name__ == '__main__':
    key = KeyManager(
        '../data/alice.key',
        '../data/alice.psk.key',
        '../data/ctrl.dat',
        False
    )

    key.clear()

    key.append(np.array([True, False, True, True], dtype='bool'))
    key.append(np.array([True, False, True, True, False], dtype='bool'))
    print(key.get(5))
    print(key.get(3))
    #
    # del key
    # c[0:5] = [0, 0, 0, 0, 0]
    # c.bin
    # print(c.bin)
