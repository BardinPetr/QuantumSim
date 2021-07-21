import threading
from typing import Union

import numpy as np

from src.Bridge import Bridge
from src.crypto.KeyManager import KeyManager
from src.math.rand import rand_bin
from src.sim.Clock import Clock
from src.sim.Wave import Wave
from src.sim.data.AliceHardwareParams import AliceHardwareParams
from src.sim.data.BB84ClassicChannelData import BB84ClassicChannelData
from src.sim.devices.HalfWavePlate import HalfWavePlate
from src.sim.devices.Laser import Laser
from src.sim.devices.users.EndpointDevice import EndpointDevice


class Alice(EndpointDevice):
    def __init__(self,
                 params: AliceHardwareParams,
                 bridge: Bridge,
                 key_manager: KeyManager,
                 session_size: int = 10 ** 5,
                 name: str = "Alice"):
        super().__init__(bridge, name)

        # параметры устройств Алисы
        self.hard_params = params

        # часы для работы лазера
        self.clock = Clock(params.laser_period)

        # излучает ли в данный момент Алиса волны
        self.emit_waves = False

        # сгенерированный ключ (до сверки базисов)
        self.base_key = []

        # размер сессии (TODO: возможно переложить эту обязанность на центральный узел)
        self.session_size = session_size

        # внешний ip адрес текущего подключения
        self.current_connection: str = None

        # внешний ip адрес следующего подключения
        self.next_connection: str = None

        self.bridge.subscribe(Bridge.EVENT_SOCKET_INCOMING, self.on_message)

        # вызов KeyManager, когда ключ завершён и обработан
        self.subscribe(Alice.EVENT_KEY_FINISHED, key_manager.append)

        # массив волн для отправки
        self.wave_send_batch = []

        self.max_wave_send_batch_size = 1000

        # создание оптической схемы
        self.gen_optic_scheme()

    def forward_link(self, *devs: EndpointDevice):
        for dev in devs:
            self.bridge.connect(dev.bridge.external_ip, dev.bridge.in_port)

    def on_message(self, data):
        ip, data = data

        if data == EndpointDevice.MESSAGE_CONNECTION_REMOVE:
            if not self.emit_waves:
                self.bridge.send_data(
                    ip, Bridge.HEADER_CLASSIC, EndpointDevice.MESSAGE_ALICE_SWITCHED_WITHOUT_CHECKING_BASES
                )

            self.emit_waves = False
        elif data == EndpointDevice.MESSAGE_ALICE_LASER_PERIOD_REQUEST:
            if not self.emit_waves:
                self.current_connection = ip

                self.bridge.send_data(
                    ip,
                    Bridge.HEADER_CLASSIC,
                    EndpointDevice.MESSAGE_ALICE_LASER_PERIOD_INFO +
                    int(self.hard_params.laser_period).to_bytes(2, byteorder='big')
                )
            else:
                self.emit_waves = False
                self.next_connection = ip
        elif data == EndpointDevice.MESSAGE_BOB_READY_TO_RECEIVE:
            self.emit_waves = True
            self.current_connection = ip
            threading.Thread(target=self.start, daemon=True).start()
        else:
            data: BB84ClassicChannelData = BB84ClassicChannelData.from_json(data)

            key = np.array(self.base_key)[data.save_ids]
            self.save_key(key)

            if self.next_connection is not None:
                self.current_connection = self.next_connection
                self.next_connection = None

                self.bridge.send_data(
                    ip,
                    Bridge.HEADER_CLASSIC,
                    EndpointDevice.MESSAGE_ALICE_LASER_PERIOD_INFO +
                    int(self.hard_params.laser_period).to_bytes(2, byteorder='big')
                )

    def save_key(self, key):
        self.emit(EndpointDevice.EVENT_KEY_FINISHED, key)
        print(f'alice ({self.bridge.external_ip}) got key: ', *key[:25], sep='\t')

    def start(self):
        self.base_key = []
        self.bases = []

        for time in self.clock.work():
            self.laser.emit_wave(time)

            if not self.emit_waves:
                break

        self.check_bases()

    def check_bases(self):
        self.bridge.send_data(
            self.current_connection,
            Bridge.HEADER_CLASSIC,
            BB84ClassicChannelData(
                bases=self.bases
            ).to_bytes().encode('utf-8')
        )

    def get_bit(self):
        self.base_key.append(rand_bin())
        return self.base_key[-1]

    def gen_optic_scheme(self):
        self.laser = Laser(polarization=self.hard_params.polarization, mu=1000000000)

        self.hwp = HalfWavePlate(angle_control_cb=lambda _: np.pi * (self.get_bit() + self.choose_basis()) / 4)
        self.laser.forward_link(self.hwp)

        # отправляет волны в __call__ функцию
        self.hwp.forward_link(self)

    def __call__(self, wave_in: Union[Wave, None] = None):
        self.wave_send_batch.append(wave_in.to_bin())

        if len(self.wave_send_batch) >= self.max_wave_send_batch_size:
            self.bridge.send_data(
                self.current_connection,
                Bridge.HEADER_CLASSIC,
                EndpointDevice.MESSAGE_ALICE_WAVES_BATCH +
                EndpointDevice.QUANTUM_BATCH_SEPARATOR.join(self.wave_send_batch)
            )

            self.wave_send_batch = []
