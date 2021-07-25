from src.math.rand import rand_bin
from src.messages.Payloads import ClassicMsg
from src.sim.data.HardwareParams import HardwareParams
from src.sim.devices.Device import Device


class EndpointDevice(Device):
    EVENT_KEY_FINISHED = 'key_finished'
    MESSAGE_BOB_RECIEVED_ALL_WAVES = b'mbraw'

    def __init__(self, params: HardwareParams, name="Basic Device"):
        super().__init__(name)
        self.hard_params = params
        self.bases = []
        self.send_classic_bind = None

    def on_classic_recv(self, msg: ClassicMsg):
        pass

    def on_waves_recv(self, data: bytes):
        pass

    def bind_bridge(self, peer_ip: str, bridge: 'Bridge'):
        bridge.subscribe(bridge.EVENT_INCOMING_CLASSIC, self.on_classic_recv)
        bridge.subscribe(bridge.EVENT_INCOMING_WAVES, self.on_waves_recv)
        self.send_classic_bind = lambda data, mode: bridge.send_classic(peer_ip, data, mode)
        self.send_waves_bind = lambda data: bridge.send_waves(peer_ip, data)

    def choose_basis(self):
        basis = 0.5 if rand_bin() else 0
        self.bases.append(bool(basis))

        return basis
