import numpy as np

from src.messages.Message import Message
from src.sim.data.HardwareParams import HardwareParams
from src.sim.devices.Attenuator import Attenuator
from src.sim.Clock import Clock
from src.sim.devices.HalfWavePlate import HalfWavePlate
from src.sim.devices.Laser import Laser
from src.sim.devices.users.EndpointDevice import EndpointDevice
from src.math.rand import rand_bin


class Alice(EndpointDevice):
    def __init__(self,
                 params: HardwareParams,
                 session_size: int = 10 ** 5,
                 name: str = "Alice"):
        super().__init__(params, name)

        self.clock = Clock(params.laser_period)

        self.base_key = []

        self.session_size = session_size

        self.gen_optic_scheme()

    def on_classic_recv(self, msg: Message):
        if msg.payload.mode == 0:
            return

        key = np.array(self.base_key)[msg.payload.data]
        self.save_key(key)

    def save_key(self, key):
        self.emit(EndpointDevice.EVENT_KEY_FINISHED, (key, self.session_size))
        # print("ALICE GOT KEY:", *key[:25].tolist(), sep="\t")

    def start(self, progress_bar=True):
        while True:
            self.base_key = []
            self.bases = []

            self.laser.start(self.session_size, progress_bar)
            self.check_bases()
            return

    def check_bases(self):
        self.send_classic_bind(self.bases, 0)

    def get_bit(self):
        self.base_key.append(rand_bin())
        return self.base_key[-1]

    def gen_optic_scheme(self):
        self.laser = Laser(self.clock, polarization=self.hard_params.polarization, mu=self.hard_params.mu)

        self.attenuator = Attenuator(self.hard_params.attenuation)
        self.laser.forward_link(self.attenuator)

        self.hwp = HalfWavePlate(angle_control_cb=lambda _: np.pi * (self.get_bit() + self.choose_basis()) / 4)
        self.attenuator.forward_link(self.hwp)

        self.hwp.forward_link(self)
