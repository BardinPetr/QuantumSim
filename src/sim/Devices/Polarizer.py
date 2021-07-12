from src.sim.Device import Device
from src.sim.Particles.Photon import Photon
from src.sim.QuantumState import *
from src.utils.algebra import rot_mat


class Polarizer(Device):
    def __init__(self, angle: float,
                 photon_in_cb=None, photon_out_cb=None,
                 name='Linear polarizer'):
        super().__init__(photon_in_cb, photon_out_cb, name)

        self.basis = rot_mat(angle).dot(BASIS_HV)
        self.name += f" with basis {self.basis}".replace('\n', '')

    def process_full(self, photon: Photon) -> Union[Photon, None]:
        state = photon.state.read(self.basis)
        if np.allclose(state, self.basis[0], rtol=10e-6):
            return photon
        else:
            return None
