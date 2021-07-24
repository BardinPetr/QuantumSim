from src.sim.data.HardwareParams import HardwareParams
from src.sim.devices.Device import Device
from src.math.rand import rand_bin


class EndpointDevice(Device):
    EVENT_KEY_FINISHED = 'key_finished'

    def __init__(self, params: HardwareParams, name="Basic Device"):
        super().__init__(name)
        self.hard_params = params
        self.bases = []

    def choose_basis(self):
        basis = 0.5 if rand_bin() else 0
        self.bases.append(bool(basis))

        return basis
