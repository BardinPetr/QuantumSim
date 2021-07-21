import threading

from src.Bridge import Bridge
from src.sim.devices.Device import Device
from src.math.rand import rand_bin


class EndpointDevice(Device):
    MESSAGE_TYPE_SIZE = 5
    MESSAGE_CONNECTION_REMOVE = b'conrm'
    MESSAGE_ALICE_SWITCHED_WITHOUT_CHECKING_BASES = b'aswcb'
    MESSAGE_ALICE_LASER_PERIOD_REQUEST = b'alpre'
    MESSAGE_ALICE_LASER_PERIOD_INFO = b'alpin'
    MESSAGE_BOB_READY_TO_RECEIVE = b'rtrec'
    MESSAGE_ALICE_WAVES_BATCH = b'awavb'

    QUANTUM_BATCH_SEPARATOR = b'sep'

    EVENT_KEY_FINISHED = 'key_finished'

    def __init__(self, bridge: Bridge, name="Basic Device"):
        super().__init__(name)
        self.bases = []

        self.bridge = bridge
        threading.Thread(target=self.bridge.run, daemon=True).run()

        self.current_connection: EndpointDevice = None

    def choose_basis(self):
        basis = 0.5 if rand_bin() else 0
        self.bases.append(bool(basis))

        return basis
