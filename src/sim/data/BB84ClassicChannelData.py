from dataclasses import dataclass
from typing import Union

from dataclasses_json import dataclass_json


@dataclass_json
@dataclass
class BB84ClassicChannelData:
    sender_uuid: str
    bases: Union[None, list[int, ...]] = None
    save_ids: Union[None, list[int, ...]] = None
