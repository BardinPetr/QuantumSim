import random
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
from src.sim.devices.Device import Device
from src.sim.devices.HalfWavePlate import HalfWavePlate
from src.sim.devices.Laser import Laser
from src.sim.devices.users.Bob import Bob
from src.sim.devices.users.EndpointDevice import EndpointDevice


class Alice(EndpointDevice):
    def __init__(self,
                 params: AliceHardwareParams,
                 bridge: Bridge,
                 key_manager: KeyManager,
                 session_size: int = 10 ** 5,
                 name: str = "Alice"):
        super().__init__(name)

        # параметры устройств Алисы
        self.hard_params = params

        # часы для работы лазера
        self.clock = Clock(params.laser_period)

        # сгенерированный ключ (до сверки базисов)
        self.base_key = []

        # размер сессии (TODO: возможно переложить эту обязанность на центральный узел)
        self.session_size = session_size

        # текущее подключение
        self.current_connection: Bob = None

        # следующее в очереди подключение
        self.next_connection: Bob = None

        # словарь, в котором индексы - внешние ip адреса, а значения - выходы из Алисы
        self.output_ips = {}

        # излучает ли Алиса волны
        self.emit_waves = False

        # мост для связи по классическому каналу
        self.bridge = bridge
        self.bridge.subscribe(Bridge.EVENT_SOCKET_INCOMING, self.on_message)

        # вызов KeyManager, когда ключ завершён и обработан
        self.subscribe(Alice.EVENT_KEY_FINISHED, key_manager.append)
        self.subscribe(Alice.EVENT_AFTER_FORWARD_LINK, self.device_linked)

        # создание оптической схемы
        self.gen_optic_scheme()

    def connect_to_bob(self, bob: Bob):
        self.bridge.connect(bob.bridge.external_ip)

    def device_linked(self):
        if self.current_connection is None:
            self.current_connection = self.outputs[0]

        # auto discover connected bob external ips
        for (index, output) in enumerate(self.outputs):
            current_device: Device = output

            while not isinstance(current_device, Bob) and len(current_device.outputs) != 1:
                current_device = list(filter(
                    lambda x: x != current_device,
                    current_device.outputs
                ))[0]

            if len(current_device.outputs) == 1:
                return

            self.output_ips[current_device.bridge.external_ip] = index

    def on_message(self, data):
        ip, data = data

        if data == EndpointDevice.MESSAGE_CONNECTION_REMOVE:
            self.emit_waves = False
            self.next_connection = self.output_ips[ip]
            return

        if data == EndpointDevice.MESSAGE_ALICE_START_SEND_WAVES_REQUEST:
            self.emit_waves = True
            threading.Thread(target=self.start, daemon=True).run()
            return

        data: BB84ClassicChannelData = BB84ClassicChannelData.from_json(data)

        key = np.array(self.base_key)[data.save_ids]
        self.save_key(key)

    def save_key(self, key):
        self.emit(EndpointDevice.EVENT_KEY_FINISHED, key)
        print(f'alice ({self.uuid}) got key: ', *key[:25], sep='\t')

    def start(self):
        self.base_key = []
        self.bases = []

        for time in self.clock.work():
            self.laser.emit_wave(time)

            if not self.emit_waves:
                break

        self.check_bases()

        if self.next_connection is not None:
            self.current_connection = self.next_connection
            self.next_connection = None

    def check_bases(self):
        self.bridge.send_data(
            self.current_connection.bridge.external_ip,
            Bridge.HEADER_CLASSIC,
            BB84ClassicChannelData(
                bases=self.bases
            ).to_bytes().encode('utf-8')
        )

    def get_bit(self):
        self.base_key.append(rand_bin())
        return self.base_key[-1]

    def gen_optic_scheme(self):
        self.laser = Laser(polarization=self.hard_params.polarization, mu=self.hard_params.mu)

        self.hwp = HalfWavePlate(angle_control_cb=lambda _: np.pi * (self.get_bit() + self.choose_basis()) / 4)
        self.laser.forward_link(self.hwp)

        # отправляет волны в __call__ функцию
        self.hwp.forward_link(self)

    def __call__(self, wave_in: Union[Wave, None] = None):
        self.outputs[
            self.output_ips[self.current_connection.bridge.external_ip]
        ](wave_in)
