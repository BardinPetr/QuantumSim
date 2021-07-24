from dataclasses import dataclass
from dataclasses_json import dataclass_json


@dataclass_json
@dataclass
class BobHardwareParams:
    pdc: float = 10 ** -6
    eff: float = 0.1
    dt: float = 1000
    fiber_length: float = 50
