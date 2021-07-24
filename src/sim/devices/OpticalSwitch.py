from typing import Union

from src.sim.devices.Device import Device
from src.sim.Wave import Wave


class OpticalSwitch(Device):
    def __init__(self):
        super().__init__()

        self.out_id = -1

    def switch(self, out_id=-1):
        self.out_id = out_id

    def __call__(self, wave_in: Union[Wave, None] = None):
        self.emit(Device.EVENT_IN, wave_in)

        if -1 < self.out_id < len(self.outputs):
            self.emit(Device.EVENT_OUT, wave_in)
            self.outputs[self.out_id](wave_in)
