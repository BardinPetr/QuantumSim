import numpy as np

from src.sim.QuantumState import QuantumState


class Wave:
    def __init__(self, mu: float, state: QuantumState, time: int = 0, direction: int = 1):
        self.direction = direction
        self.mu = mu
        self.state = state
        self.time = time

        self.photons_count = None

        self.history = []

    def append_device_uuid(self, uuid: str):
        self.history.append(uuid)

    def get_photons_count(self):
        if self.photons_count is not None:
            return self.photons_count

        self.photons_count = np.random.poisson(self.mu)

        return self.photons_count

    def __str__(self):
        return f'Wave with state: {self.state} and average photons count: {self.mu}'
