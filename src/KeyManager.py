import os
from math import ceil

import numpy as np
from bitstring import BitArray, BitStream
from numpy.typing import NDArray


class KeyManager:
    def __init__(self, path, psk_path, ctrl_path, remove_after_use=True):
        self.path = path
        self.psk_path = psk_path
        self.ctrl_path = ctrl_path
        self.remove_after_use = remove_after_use

        self.write_memory = np.array([], dtype='bool')
        self.read_memory = np.array([], dtype='bool')

        if not os.path.isfile(ctrl_path) or os.path.getsize(ctrl_path) == 0:
            self.save_cur_pos(0, 0)

        self.cur_pos, self.cur_psk_pos = self.load_cur_pos()

    def load_cur_pos(self):
        with open(self.ctrl_path, 'r') as f:
            return [int(i) for i in f.readlines()]

    def save_cur_pos(self, a=None, b=None):
        a = self.cur_pos if a is None else a
        b = self.cur_psk_pos if b is None else b
        with open(self.ctrl_path, 'w') as f:
            f.write(f"{a}\n{b}\n")

    def clear(self):
        if os.path.isfile(self.path):
            os.unlink(self.path)

    def get(self, length: int):
        with open(self.path, 'rb') as f:
            self.cur_pos += len(self.read_memory)
            f.seek(self.cur_pos // 8)
            self.cur_pos += length - len(self.read_memory)

            byte_array = bytearray(f.read(ceil(length / 8)))
            key = np.concatenate((self.read_memory, np.unpackbits(np.frombuffer(byte_array, dtype='uint8')))

            key, self.read_memory = np.split(byte_array, [length])
            self.save_cur_pos()
            return key

    def append(self, key: NDArray):
        key = np.concatenate((self.write_memory, key))

        if len(key) % 8:
            key, self.write_memory = np.split(key, [(key.size // 8) * 8])
        else:
            self.write_memory = np.array([], dtype='bool')

        packed_key = np.packbits(key)

        with open(self.path, 'ab') as f:
            f.write(packed_key.tobytes())


if __name__ == '__main__':
    key = KeyManager(
        '/home/petr/Desktop/QuantumLink/data/alice.key',
        '/home/petr/Desktop/QuantumLink/data/alice.psk.key',
        '/home/petr/Desktop/QuantumLink/data/ctrl.dat',
        False
    )




    # key.clear()
    #
    # key.append(np.array([True, False, True, True], dtype='bool'))
    # key.append(np.array([True, False, True, True, False], dtype='bool'))
    #
    # print(key.memory)
    # print(key.get())
    #
    # del key
    c = BitStream(filename=key.path)
    # c[0:5] = [0, 0, 0, 0, 0]
    # c.bin
    print(c.bin)