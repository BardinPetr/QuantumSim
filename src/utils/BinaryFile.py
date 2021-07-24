import os
from math import ceil, floor

import numpy as np
from numpy.typing import NDArray


class FileTooShort(Exception):
    pass


class BinaryFile:
    def __init__(self, path: str):
        self.path = path

        self.write_memory = np.array([], dtype='bool')

        if not os.path.isfile(self.path):
            open(self.path, 'wb').close()

    def read(self, start: int, end: int):
        start_byte = floor(start / 8)
        end_byte = ceil(end / 8)

        if end_byte * 8 > self.__len__():
            raise FileTooShort()

        with open(self.path, 'rb') as f:
            f.seek(start_byte)

            byte_content = bytearray(f.read(end_byte - start_byte))

        content = np.unpackbits(np.frombuffer(byte_content, dtype='uint8'))

        content = content[(start - start_byte * 8):(end - start_byte * 8 + 1)]

        return content

    def append(self, content: NDArray):
        content = np.concatenate((self.write_memory, content))

        if len(content) % 8:
            content, self.write_memory = np.split(content, [(content.size // 8) * 8])
        else:
            self.write_memory = np.array([], dtype='bool')

        packed_content = np.packbits(content)

        with open(self.path, 'ab') as f:
            f.write(packed_content.tobytes())

    def read_all(self):
        with open(self.path, 'rb') as f:
            byte_content = bytearray(f.read())

        return np.unpackbits(np.frombuffer(byte_content, dtype='uint8'))

    def clear(self):
        with open(self.path, 'w') as f:
            f.write("")

        self.write_memory = np.array([], dtype='bool')

    def __len__(self):
        return os.path.getsize(self.path) * 8


if __name__ == "__main__":
    file = BinaryFile(path='d:/Programs/PycharmProjects/QuantumSim/data/test.txt')

    file.clear()

    file.append(np.array([True, True, False, True]))
    file.append(np.array([True, True, False, True]))
    file.append(np.array([True, True, False, True]))
    file.append(np.array([True, True, False, True]))

    print(file.read(4, 5))
