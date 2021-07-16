from typing import Union

import numpy as np
from numpy.typing import NDArray

from src.KeyManager import KeyManager


class Crypto:
    def __init__(self, km: KeyManager):
        self.km = km

    @staticmethod
    def _preprocess(data: Union[NDArray, list, tuple, bytes, bytearray]) -> NDArray:
        if not isinstance(data[0], bool):
            data = bytearray(data)
        if isinstance(data, bytes) or isinstance(data, bytearray):
            return np.frombuffer(data, dtype='uint8')
        return np.array(data)

    def _postprocess(self, data: NDArray) -> bytes:
        return data.tobytes()

    def encrypt(self, data: Union[NDArray, list, tuple, bytes, bytearray], psk=False):
        return self._postprocess(self._preprocess(data) ^ self.km.get(len(data), bits=False, psk=psk))

    def decrypt(self, data: Union[NDArray, list, tuple, bytes, bytearray], psk=False):
        return self.encrypt(data, psk)
