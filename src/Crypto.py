from typing import Union

import numpy as np
from numpy.typing import NDArray

from src.KeyManager import KeyManager


class Crypto:
    def __init__(self, km: KeyManager):
        self.km = km
        self.count = 0

    @staticmethod
    def _preprocess(data: Union[NDArray, list, tuple, bytes, bytearray]) -> NDArray:
        if not isinstance(data[0], bool):
            data = bytearray(data)
        if isinstance(data, bytes) or isinstance(data, bytearray):
            return np.unpackbits(np.frombuffer(data, dtype='uint8'))
        return np.array(data)

    @staticmethod
    def _postprocess(data: NDArray) -> bytes:
        if len(data):
            return np.packbits(data).tobytes()

    def encrypt(self, data: Union[NDArray, list, tuple, bytes, bytearray], psk=False, crypt_start=0, crypt_end=None):
        crypt_end = len(data) if crypt_end is None else crypt_end
        ln = (crypt_end - crypt_start)
        key = self.km.get(ln * 8, bits=True, psk=psk)
        # print(self.count, key)
        self.count += 1
        return \
            data[:crypt_start] + \
            (self._postprocess(self._preprocess(data[crypt_start:crypt_end]) ^ key) if ln > 0 else b'') + \
            data[crypt_end:]

    def decrypt(self, data: Union[NDArray, list, tuple, bytes, bytearray], psk=False, crypt_start=0, crypt_end=None):
        return self.encrypt(data, psk, crypt_start, crypt_end)
