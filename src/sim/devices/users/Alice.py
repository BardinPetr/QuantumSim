import random
from typing import Union

import numpy as np

from src.crypto.KeyManager import KeyManager
from src.math.rand import rand_bin
from src.sim.ClassicChannel import ClassicChannel
from src.sim.Clock import Clock
from src.sim.Wave import Wave
from src.sim.data.AliceHardwareParams import AliceHardwareParams
from src.sim.data.BB84ClassicChannelData import BB84ClassicChannelData
from src.sim.devices.HalfWavePlate import HalfWavePlate
from src.sim.devices.Laser import Laser
from src.sim.devices.users.EndpointDevice import EndpointDevice


class Alice(EndpointDevice):
    def __init__(self,
                 mac_address: str,
                 params: AliceHardwareParams,
                 classic_channel: ClassicChannel,
                 key_manager: KeyManager,
                 session_size: int = 10 ** 5,
                 name: str = "Alice"):
        super().__init__(mac_address, name)

        self.hard_params = params
        self.clock = Clock(params.laser_period)

        self.base_key = []

        self.session_size = session_size

        self.current_connection: int = None

        self.classic_channel = classic_channel
        self.classic_channel.subscribe(ClassicChannel.EVENT_ON_RECV, self.on_classic_recv)

        self.subscribe(Alice.EVENT_KEY_FINISHED, key_manager.append)
        self.subscribe(Alice.EVENT_AFTER_FORWARD_LINK, self.device_linked)

        self.gen_optic_scheme()

    def device_linked(self):
        if self.current_connection is None:
            self.current_connection = 0

    def on_classic_recv(self, data):
        mac_address, data = data
        if mac_address != self.mac_address:
            return

        data: BB84ClassicChannelData = BB84ClassicChannelData.from_json(data)

        key = np.array(self.base_key)[data.save_ids]
        self.save_key(key)

    def save_key(self, key):
        self.emit(EndpointDevice.EVENT_KEY_FINISHED, key)
        print(f'alice ({self.mac_address}) got key: ', *key[:25], sep='\t')

    def start(self, progress_bar=True):
        while True:
            self.base_key = []
            self.bases = []

            self.laser.start(self.session_size, progress_bar)
            self.check_bases()

            self.current_connection = random.randint(0, len(self.outputs) - 1)

    def check_bases(self):
        self.classic_channel.send(
            self.outputs[self.current_connection].mac_address,
            BB84ClassicChannelData(
                bases=self.bases
            ).to_json().encode('utf-8')
        )

    def get_bit(self):
        self.base_key.append(rand_bin())
        return self.base_key[-1]

    def gen_optic_scheme(self):
        self.laser = Laser(self.clock, polarization=self.hard_params.polarization, mu=self.hard_params.mu)

        self.hwp = HalfWavePlate(angle_control_cb=lambda _: np.pi * (self.get_bit() + self.choose_basis()) / 4)
        self.laser.forward_link(self.hwp)

        # отправляет волны в __call__ функцию
        self.hwp.forward_link(self)

    def __call__(self, wave_in: Union[Wave, None] = None):
        self.outputs[self.current_connection](wave_in)
