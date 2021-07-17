import math

import numpy as np
from numpy.typing import NDArray

from src.KeyManager import KeyManager
from src.sim.ClassicChannel import ClassicChannel
from src.sim.Wave import Wave
from src.sim.data.BB84ClassicChannelData import BB84ClassicChannelData
from src.sim.data.BobHardwareParams import BobHardwareParams
from src.sim.devices.Detector import Detector
from src.sim.devices.HalfWavePlate import HalfWavePlate
from src.sim.devices.users.EndpointDevice import EndpointDevice


class Bob(EndpointDevice):
    def __init__(self,
                 mac_address: str,
                 params: BobHardwareParams,
                 classic_channel: ClassicChannel,
                 key_manager: KeyManager,
                 name: str = "Bob"):
        super().__init__(mac_address, name)

        self.hard_params = params

        self.base_key = []

        # individual for every connection
        self.connections_laser_periods = {}

        self.last_wave_time = 0

        self.current_connection: str = None

        self.classic_channel = classic_channel
        self.classic_channel.subscribe(ClassicChannel.EVENT_ON_RECV, self.on_classic_recv)

        self.subscribe(Bob.EVENT_KEY_FINISHED, key_manager.append)

        self.gen_optic_scheme()

        self.subscribe(Bob.EVENT_AFTER_BACK_LINK, self.device_linked)

    def device_linked(self):
        for inp in self.inputs:
            if inp.mac_address not in self.connections_laser_periods:
                self.connections_laser_periods[inp.mac_address] = inp.hard_params.laser_period

        if self.current_connection is None:
            self.current_connection = self.inputs[0].mac_address
            self.last_wave_time = -self.connections_laser_periods[self.current_connection]

    def on_classic_recv(self, data):
        mac_address, data = data
        if mac_address != self.mac_address:
            return

        data: BB84ClassicChannelData = BB84ClassicChannelData.from_json(data.decode())

        self.fix_photon_statistics(len(data.bases) * self.connections_laser_periods[self.current_connection])

        print(len(self.base_key))

        alice_bases = np.array(data.bases, dtype='bool')
        bob_bases = np.array(self.bases, dtype='bool')

        same_bases_ids = np.where(alice_bases == bob_bases)[0]

        key: NDArray = np.array(self.base_key)[same_bases_ids]
        ids = np.where(key != 2)

        self.save_key(key[ids].astype('bool'))

        self.classic_channel.send(
            self.current_connection,
            BB84ClassicChannelData(
                save_ids=same_bases_ids[ids].tolist()
            ).to_json().encode('utf-8')
        )

        self.bases = []
        self.base_key = []

        self.last_wave_time = -self.connections_laser_periods[self.current_connection]

        self.detector.reset()

    def save_key(self, key):
        self.emit(EndpointDevice.EVENT_KEY_FINISHED, key)
        print('bob  ', *key[:25], sep='\t')

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
        current_laser_period = self.connections_laser_periods[self.current_connection]

        if self.last_wave_time < time - current_laser_period:
            missed_count = math.ceil(
                (time - self.last_wave_time) / current_laser_period
            ) - 1
            self.base_key += [2] * missed_count

    def on_detection(self, wave: Wave):
        self.fix_photon_statistics(wave.time)

        state = wave.state.read(self.hard_params.read_basis)
        self.base_key.append(state[1])

        self.last_wave_time = wave.time
