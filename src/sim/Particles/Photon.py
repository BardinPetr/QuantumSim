# from random import random
from src.sim.QuantumState import QuantumState


class Photon:
    def __init__(self, state: QuantumState, time: int = 0):
        self.state = state
        self.time = time

    # def split(self, count: int) -> list:
    #     parts = []
    #
    #     for i in range(count):
    #         parts.append(PhotonPart(self))
    #
    #     for part in parts:
    #         part.link(parts)
    #
    #     return parts

    def __str__(self):
        return f'Photon with state: {self.state}'
