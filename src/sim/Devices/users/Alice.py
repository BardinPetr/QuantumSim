import numpy as np

from src.sim.data.HardwareParams import HardwareParams
from src.sim.devices.Attenuator import Attenuator
from src.sim.Clock import Clock
from src.sim.devices.HalfWavePlate import HalfWavePlate
from src.sim.devices.Laser import Laser
from src.sim.MainDevices.ClassicChannel import ClassicChannel
from src.sim.devices.users.EndpointDevice import EndpointDevice
from src.sim.data.BB84ClassicChannelData import BB84ClassicChannelData
from src.math.rand import rand_bin


# TODO: replace classic channel with Bridge
class Alice(EndpointDevice):
    def __init__(self,
                 params: HardwareParams,
                 classic_channel: ClassicChannel,
                 session_size: int = 10 ** 5,
                 name: str = "Alice"):
        super().__init__(params, name)

        self.clock = Clock(params.laser_period)

        self.base_key = []

        self.session_size = session_size
        self.classic_channel = classic_channel
        self.classic_channel.subscribe(ClassicChannel.EVENT_ON_RECV, self.on_classic_recv)

        self.gen_optic_scheme()

    def on_classic_recv(self, data):
        data: BB84ClassicChannelData = BB84ClassicChannelData.from_json(data)

        if data.message_type == 0:
            return

        key = np.array(self.base_key)[data.save_ids]
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

    def check_bases(self):
        self.classic_channel.send(
            BB84ClassicChannelData(
                message_type=0,
                bases=self.bases
            ).to_json().encode('utf-8')
        )

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

