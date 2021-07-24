import math

import numpy as np
from numpy.typing import NDArray
from src.sim.MainDevices.ClassicChannel import ClassicChannel

from src.sim.QuantumState import BASIS_HV
from src.sim.Wave import Wave
from src.sim.data.BB84ClassicChannelData import BB84ClassicChannelData
from src.sim.data.HardwareParams import HardwareParams
from src.sim.devices.Detector import Detector
from src.sim.devices.HalfWavePlate import HalfWavePlate
from src.sim.devices.users.EndpointDevice import EndpointDevice


# TODO: replace classic channel with Bridge
class Bob(EndpointDevice):
    def __init__(self,
                 params: HardwareParams,
                 classic_channel: ClassicChannel,
                 read_basis: NDArray = BASIS_HV,
                 name: str = "Bob"):
        super().__init__(params, name)

        self.read_basis = read_basis

        self.base_key = []
        self.last_wave_time = -params.laser_period
        self.received_waves_count = 0

        self.classic_channel = classic_channel
        self.classic_channel.subscribe(ClassicChannel.EVENT_ON_RECV, self.on_classic_recv)

        self.gen_optic_scheme()

    def on_classic_recv(self, data: bytes):
        data: BB84ClassicChannelData = BB84ClassicChannelData.from_json(data.decode())
        if data.message_type == 1:
            return

        self.fix_photon_statistics(len(data.bases) * self.hard_params.laser_period)

        alice_bases = np.array(data.bases, dtype='bool')
        bob_bases = np.array(self.bases, dtype='bool')

        same_bases_ids = np.where(alice_bases == bob_bases)[0]

        key: NDArray = np.array(self.base_key)[same_bases_ids]
        ids = np.where(key != 2)

        self.save_key(key[ids].astype('bool'))

        self.classic_channel.send(
            BB84ClassicChannelData(
                message_type=1,
                save_ids=same_bases_ids[ids].tolist()
            ).to_json().encode('utf-8')
        )

        self.bases = []
        self.base_key = []
        self.last_wave_time = -self.hard_params.laser_period
        self.received_waves_count = 0
        self.detector.reset()

    def save_key(self, key):
        self.emit(EndpointDevice.EVENT_KEY_FINISHED, (key, self.received_waves_count))
        # print("\nBOB GOT KEY:", *key[:25], sep="\t")

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
