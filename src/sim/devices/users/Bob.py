import math

import numpy as np
from numpy.typing import NDArray

from src.Bridge import Bridge
from src.crypto.KeyManager import KeyManager
from src.sim.Wave import Wave
from src.sim.data.BB84ClassicChannelData import BB84ClassicChannelData
from src.sim.data.BobHardwareParams import BobHardwareParams
from src.sim.devices.Detector import Detector
from src.sim.devices.HalfWavePlate import HalfWavePlate
from src.sim.devices.users.EndpointDevice import EndpointDevice


class Bob(EndpointDevice):
    def __init__(self,
                 params: BobHardwareParams,
                 bridge: Bridge,
                 key_manager: KeyManager,
                 name: str = "Bob"):
        super().__init__(bridge, name)

        # параметры установок Боба
        self.hard_params = params

        # ключ, полученный в процессе генерации (без сверки базисов)
        self.base_key = []

        # внешний ip адрес текущего подключения
        self.current_connection: str = None

        # внешний ip адрес следующего подключения
        self.next_connection: str = None

        # период лазера Алисы, к которой сейчас подключен Боб
        self.current_connection_laser_period: int = None

        # время, когда пришёл последний сигнал от Алисы
        self.last_wave_time = 0

        self.bridge.subscribe(Bridge.EVENT_SOCKET_INCOMING, self.on_message)

        # добавляем ключ в KeyManager, когда он сгенерирован
        self.subscribe(Bob.EVENT_KEY_FINISHED, key_manager.append)

        # генерируем оптическую схему
        self.gen_optic_scheme()

    def switch_to_alice(self, alice_ip: str):
        # отправляет текущей Алисе сообщение о том, что пора заканчивать передачу.
        if self.current_connection is not None:
            self.bridge.send_data(
                self.current_connection,
                Bridge.HEADER_CLASSIC,
                EndpointDevice.MESSAGE_CONNECTION_REMOVE
            )
        else:
            self.next_connection = alice_ip

            self.reset()

        # ждёт конца передачи от Алисы
        # сверяет базисы
        # переключается на другую Алису
        # присылает этой Алисе команду, что пора начинать с ним работу
        # Алисы присылает в ответ частоту лазера
        # Боб присылает в ответ, что готов слушать

    def on_message(self, data: bytes):
        ip, data = data

        if data == self.MESSAGE_ALICE_SWITCHED_WITHOUT_CHECKING_BASES:
            self.reset()
        elif data.startswith(self.MESSAGE_ALICE_LASER_PERIOD_INFO):
            self.current_connection_laser_period = int.from_bytes(
                data[EndpointDevice.MESSAGE_TYPE_SIZE:],
                byteorder='big'
            )

            self.last_wave_time = -self.current_connection_laser_period

            self.bridge.send_data(
                ip,
                Bridge.HEADER_CLASSIC,
                EndpointDevice.MESSAGE_BOB_READY_TO_RECEIVE
            )
        elif data.startswith(EndpointDevice.MESSAGE_ALICE_WAVES_BATCH):
            data = data[EndpointDevice.MESSAGE_TYPE_SIZE:].split(EndpointDevice.QUANTUM_BATCH_SEPARATOR)

            for i in data:
                self(Wave.from_bin(i))
        else:
            data: BB84ClassicChannelData = BB84ClassicChannelData.from_json(data.decode('utf-8'))

            self.fix_photon_statistics(len(data.bases) * self.current_connection_laser_period)

            alice_bases = np.array(data.bases, dtype='bool')
            bob_bases = np.array(self.bases, dtype='bool')

            same_bases_ids = np.where(alice_bases == bob_bases)[0]

            key: NDArray = np.array(self.base_key)[same_bases_ids]
            ids = np.where(key != 2)

            self.save_key(key[ids].astype('bool'))

            self.bridge.send_data(
                ip,
                Bridge.HEADER_CLASSIC,
                BB84ClassicChannelData(
                    save_ids=same_bases_ids[ids].tolist()
                ).to_json().encode('utf-8')
            )

            self.reset()

    def save_key(self, key):
        self.emit(EndpointDevice.EVENT_KEY_FINISHED, key)
        print(f'bob ({self.bridge.external_ip}) got key: ', *key[:25], sep='\t')

    def reset(self):
        if self.next_connection is not None:
            self.current_connection = self.next_connection
            self.next_connection = None

            self.bridge.send_data(
                self.current_connection,
                Bridge.HEADER_CLASSIC,
                EndpointDevice.MESSAGE_ALICE_LASER_PERIOD_REQUEST
            )

        self.bases = []
        self.base_key = []

        self.last_wave_time = None

        self.detector.reset()

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
        if self.last_wave_time < time - self.current_connection_laser_period:
            missed_count = math.ceil(
                (time - self.last_wave_time) / self.current_connection_laser_period
            ) - 1
            self.base_key += [2] * missed_count

    def on_detection(self, wave: Wave):
        self.fix_photon_statistics(wave.time)

        state = wave.state.read(self.hard_params.read_basis)
        self.base_key.append(state[1])

        self.last_wave_time = wave.time
