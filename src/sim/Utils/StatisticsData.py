from dataclasses import dataclass

from dataclasses_json import dataclass_json
from numpy.typing import NDArray

from src.sim.Data.HardwareParams import HardwareParams


@dataclass_json
@dataclass
class StatisticsData:
    alice_key: NDArray
    bob_key: NDArray

    qber: float
    received_waves_count: int
    emitted_waves_count: int

    params: HardwareParams
