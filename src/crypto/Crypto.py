from hashlib import blake2b
from hmac import compare_digest
from typing import Union

import numpy as np
from numpy.typing import NDArray

from src.crypto.KeyManager import KeyManager


class Crypto:
    SIGNATURE_SPLITTER = b'\x24\xfa\x52\xa3'

    SIGN_MODE_BLAKE2B = 0
    SIGN_MODE_CHACHA20_POLY1305 = 1

    def __init__(self, km: KeyManager, sign_mode=SIGN_MODE_BLAKE2B):
        self.km = km
        self.count = 0
        self.sign_mode = sign_mode

    @staticmethod
    def _preprocess(data: Union[NDArray, list, tuple, bytes, bytearray]) -> NDArray:
        if not isinstance(data[0], bool):
            data = bytearray(data)
        if isinstance(data, bytes) or isinstance(data, bytearray):
            return np.frombuffer(data, dtype='uint8')
        return np.array(data)

    @staticmethod
    def _postprocess(data: NDArray) -> bytes:
        return data.tobytes() if len(data) > 0 else b''

    def encrypt(self, data: Union[NDArray, list, tuple, bytes, bytearray], psk=False, crypt_start=0, crypt_end=None):
        crypt_end = len(data) if crypt_end is None else crypt_end
        ln = (crypt_end - crypt_start)
        key = self.km.get(ln * 8, return_bits=False, psk=psk)
        self.count += 1
        return \
            data[:crypt_start] + \
            (self._postprocess(self._preprocess(data[crypt_start:crypt_end]) ^ key) if ln > 0 else b'') + \
            data[crypt_end:]

    def decrypt(self, data: Union[NDArray, list, tuple, bytes, bytearray], psk=False, crypt_start=0, crypt_end=None):
        return self.encrypt(data, psk, crypt_start, crypt_end)

    def _sign_blake(self, data: bytes):
        key = self.km.get(64, return_bits=False, psk=True)
        h = blake2b(key=key)
        h.update(data)
        res = h.hexdigest().encode('utf-8')
        return res

    @staticmethod
    def split_sign(data: bytes):
        return data.split(Crypto.SIGNATURE_SPLITTER)

    def sign(self, msg: bytes):
        sign = b''
        if self.sign_mode == Crypto.SIGN_MODE_BLAKE2B:
            sign = self._sign_blake(msg)
        return Crypto.SIGNATURE_SPLITTER.join([msg, sign])

    def verify(self, msg: bytes):
        data, sign = self.split_sign(msg)
        if self.sign_mode == Crypto.SIGN_MODE_BLAKE2B:
            sign_base = self._sign_blake(data)
            return compare_digest(sign, sign_base)
