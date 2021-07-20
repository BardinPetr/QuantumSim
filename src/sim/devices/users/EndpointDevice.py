from src.sim.devices.Device import Device
from src.math.rand import rand_bin


class EndpointDevice(Device):
    MESSAGE_CONNECTION_REMOVE = b'111'
    MESSAGE_ALICE_START_SEND_WAVES_REQUEST = b'222'
    MESSAGE_ALICE_SWITCHED_WITHOUT_CHECKING_BASES = b'333'
    MESSAGE_ALICE_LASER_PERIOD = b'444'
    MESSAGE_BOB_READY_TO_LISTEN = b'555'

    EVENT_KEY_FINISHED = 'key_finished'

    def __init__(self, name="Basic Device"):
        super().__init__(name)
        self.bases = []

        self.current_connection: EndpointDevice = None

    def choose_basis(self):
        basis = 0.5 if rand_bin() else 0
        self.bases.append(bool(basis))

        return basis
