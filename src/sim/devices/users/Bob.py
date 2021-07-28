import math
import time

import numpy as np
from numpy.typing import NDArray

from src.messages.Message import Message
from src.sim.QuantumState import BASIS_HV
from src.sim.Wave import Wave
from src.sim.data.HardwareParams import HardwareParams
from src.sim.devices.Detector import Detector
from src.sim.devices.HalfWavePlate import HalfWavePlate
from src.sim.devices.users.EndpointDevice import EndpointDevice


class Bob(EndpointDevice):
    ACTION_SEND_BRIDGE_CLASSIC = 'a_evt_bridge_cls'

    def __init__(self,
                 params: HardwareParams,
                 read_basis: NDArray = BASIS_HV,
                 session_size: int = 10 ** 5,
                 name: str = "Bob"):
        super().__init__(params, name)

        self.session_size = session_size
        self.read_basis = read_basis

        self.base_key = []
        self.last_wave_time = -params.laser_period
        self.received_waves_count = 0

        self.gen_optic_scheme()

        self.processing_waves_batch = False

        self.waves_buffer = b''

    def on_waves_recv(self, raw: bytes):
        self.waves_buffer += raw

        while self.processing_waves_batch:
            time.sleep(1e-3)
        # print(len(self.waves_buffer))
        if len(self.waves_buffer) < 41000:
            return
        msgs = self.waves_buffer[:41000]
        self.waves_buffer = self.waves_buffer[41000:]
        # print('reset ', len(self.waves_buffer))

        self.processing_waves_batch = True

        size = Wave.get_struct_size()
        for i in range(0, len(msgs), size):
            self(Wave.from_bin(msgs[i:i + size]))

        if len(self.bases) == self.session_size:
            print('send remove lock request')
            self.send_classic_bind([], 2)

        self.processing_waves_batch = False

    def on_classic_recv(self, msg: Message):
        print('here!')
        print(msg.payload.mode)

        if msg.payload.mode != 0:
            return

        self.fix_photon_statistics(len(msg.payload.data) * self.hard_params.laser_period)

        alice_bases = np.array(msg.payload.data, dtype='bool')
        bob_bases = np.array(self.bases, dtype='bool')

        same_bases_ids = np.where(alice_bases == bob_bases)[0]

        key: NDArray = np.array(self.base_key)[same_bases_ids]
        ids = np.where(key != 2)

        print('saving key')

        self.save_key(key[ids].astype('bool'))

        print('saved key')

        self.bases = []
        self.base_key = []
        self.last_wave_time = -self.hard_params.laser_period
        self.received_waves_count = 0
        self.detector.reset()

        print('sending message')

        self.send_classic_bind(same_bases_ids[ids].tolist(), 1)

    def save_key(self, key):
        print("\nBOB GOT KEY:", *key[:25], sep="\t")
        self.emit(EndpointDevice.EVENT_KEY_FINISHED, (key, self.received_waves_count))

    def gen_optic_scheme(self):
        self.hwp = HalfWavePlate(angle_control_cb=lambda _: -np.pi * self.choose_basis() / 4)
        self.forward_link(self.hwp)

        self.detector = Detector(
            pdc=self.hard_params.pdc,
            eff=self.hard_params.eff,
            dt=self.hard_params.dt
        )
        self.detector.subscribe(Detector.EVENT_DETECTION, self.on_detection)

        self.hwp.forward_link(self.detector)

    def fix_photon_statistics(self, time):
        if self.last_wave_time < time - self.hard_params.laser_period:
            missed_count = math.ceil((time - self.last_wave_time) / self.hard_params.laser_period) - 1
            self.base_key += [2] * missed_count

    def on_detection(self, wave: Wave):
        self.fix_photon_statistics(wave.time)

        state = wave.state.read(self.read_basis)

        self.base_key.append(state[1])

        self.last_wave_time = wave.time
        self.received_waves_count += 1
