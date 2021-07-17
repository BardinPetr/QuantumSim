from dataclasses import dataclass
from dataclasses_json import dataclass_json
from numpy.typing import NDArray

from src.sim.QuantumState import BASIS_HV


@dataclass_json
@dataclass
class BobHardwareParams:
    pdc: float = 10 ** -6
    eff: float = 0.1
    dt: float = 1000

    read_basis: NDArray = BASIS_HV
