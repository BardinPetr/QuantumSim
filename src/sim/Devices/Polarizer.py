from src.sim.Device import Device
from src.sim.Particles.Photon import Photon
from src.sim.QuantumState import *
from src.utils.algebra import rot_mat


class Polarizer(Device):
    def __init__(self, angle: float, basis=BASIS_HV,
                 photon_in_cb=None, photon_out_cb=None, angle_control_cb=None,
                 name='Linear polarizer'):
        super().__init__(photon_in_cb, photon_out_cb, name)

        self.basis_base = basis
        self.angle_control_cb = (lambda _: angle) if angle_control_cb is None else angle_control_cb

        self.name += f" with basis {self._get_basis(angle)}".replace('\n', '')

    def _get_basis(self, angle):
        return rot_mat(angle).dot(self.basis_base)

    def process_full(self, photon: Photon) -> Union[Photon, None]:
        basis = self._get_basis(self.angle_control_cb(photon.time))
        state = photon.state.read(basis)
        if np.allclose(state, basis[0], rtol=10e-6):
            return photon
        else:
            return None
