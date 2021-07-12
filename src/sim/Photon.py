from random import random

from QuantumState import QuantumState


class Photon:
    def __init__(self, state: QuantumState):
        self.state = state
        self.time = 0

    def split(self, count: int) -> list:
        parts = []

        for i in range(count):
            parts.append(PhotonPart(self))

        for part in parts:
            part.link(parts)

        return parts


class PhotonPart:
    parts: list     # ссылки на другие части этого фотона (включая самого себя)
    is_dead = False     # учитывается ли эта часть при измерениях и передачах
    probability: float      # вероятность того, что при измерении фотон окажется на месте этой части
    state: QuantumState     # состояние части фотона, которое может отличаться от основного

    def __init__(self, base_photon: Photon):
        self.base_photon = base_photon

    def link(self, parts: list):
        self.parts = parts

    def read(self):
        rand = random()

        for part in self.parts:
            if part == self:
                continue

            if self.probability is None or self.state is None:
                raise Exception('Set probability and state for photon part.')

            if rand <= part.probability:
                part.collapse_other()

                return part.state

            rand -= part.probability

    def collapse_other(self):
        for part in self.parts:
            if part == self:
                continue

            part.is_dead = True


qs = QuantumState((1, 0))
p = Photon(qs)

print(p.split(3)[0].parts)
