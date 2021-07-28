import time
from typing import Union

import numpy as np

from src.math.rand import rand_bin
from src.messages.Message import Message
from src.sim.Clock import Clock
from src.sim.Wave import Wave
from src.sim.data.HardwareParams import HardwareParams
from src.sim.devices.Attenuator import Attenuator
from src.sim.devices.HalfWavePlate import HalfWavePlate
from src.sim.devices.Laser import Laser
from src.sim.devices.OpticFiber import OpticFiber
from src.sim.devices.users.EndpointDevice import EndpointDevice


class Alice(EndpointDevice):
    def __init__(self,
                 params: HardwareParams,
                 session_size: int = 10 ** 3,
                 name: str = "Alice"):
        super().__init__(params, name)

        self.clock = Clock(params.laser_period)

        self.base_key = []

        self.session_size = session_size

        self.wave_send_batch = []
        self.max_wave_send_batch_size = 1000

        self.gen_optic_scheme()

        self.is_bob_processed_all_bases = False
        self.is_bob_processed_all_waves = False

    def on_classic_recv(self, msg: Message):
        if msg.payload.mode == 1:
            key = np.array(self.base_key)[msg.payload.data]
            self.save_key(key)

            print('receive remove lock request')

            self.is_bob_processed_all_bases = True

        elif msg.payload.mode == 2:
            self.is_bob_processed_all_waves = True

    def save_key(self, key):
        print("ALICE GOT KEY:", *key[:25].tolist(), sep="\t")
        self.emit(EndpointDevice.EVENT_KEY_FINISHED, (key, self.session_size))

    def start(self, progress_bar=True):
        while True:
            self.base_key = []
            self.bases = []

            self.laser.start(self.session_size, progress_bar)

            if len(self.wave_send_batch) != 0:
                self.send_waves_to_bob()

            while not self.is_bob_processed_all_waves:
                time.sleep(1e-3)

            print('move next')
            self.is_bob_processed_all_waves = False

            self.check_bases()

    def check_bases(self):
        self.send_classic_bind(self.bases, 0)

        while not self.is_bob_processed_all_bases:
            time.sleep(1e-3)

        self.is_bob_processed_all_bases = False

    def get_bit(self):
        self.base_key.append(rand_bin())
        return self.base_key[-1]

    def gen_optic_scheme(self):
        self.laser = Laser(self.clock, polarization=self.hard_params.polarization, mu=self.hard_params.mu)

        self.attenuator = Attenuator(self.hard_params.attenuation)
        self.laser.forward_link(self.attenuator)

        self.hwp = HalfWavePlate(angle_control_cb=lambda _: np.pi * (self.get_bit() + self.choose_basis()) / 4)
        self.attenuator.forward_link(self.hwp)

        self.of = OpticFiber(length=self.hard_params.fiber_length,
                             deltaopt=self.hard_params.delta_opt,
                             probopt=self.hard_params.prob_opt)

        self.hwp.forward_link(self.of)

        self.of.forward_link(self)

    def send_waves_to_bob(self):
        self.send_waves_bind(self.wave_send_batch)
        self.wave_send_batch = []

    def __call__(self, wave_in: Union[Wave, None] = None):
        self.wave_send_batch.append(wave_in.to_bin())

        if len(self.wave_send_batch) >= self.max_wave_send_batch_size:
            self.send_waves_to_bob()
