from typing import Union

from src.Eventable import Eventable
from src.sim.Wave import *


class Device(Eventable):
    EVENT_IN = "wave_in"
    EVENT_OUT = "wave_out"
    EVENT_AFTER_FORWARD_LINK = "after_forward_link"
    EVENT_AFTER_BACK_LINK = "after_back_link"

    def __init__(self, name="Basic Device"):
        super().__init__()

        self.outputs = list()
        self.inputs = list()
        self.name = name

    def __repr__(self):
        return self.name

    def __call__(self, wave_in: Union[Wave, None] = None):
        self.emit(Device.EVENT_IN, wave_in)

        result = self.process_full(wave_in)
        if result is None:
            return

        self.emit(Device.EVENT_OUT, result)

        if len(self.outputs) > 0:
            self.outputs[0](result)

    def process_full(self, wave: Wave) -> Union[Wave, None]:
        return wave

    def forward_link(self, *devs, auto=True):
        for i in devs:
            self.outputs.append(i)
            if auto:
                i.back_link(self, auto=False)

        self.emit(self.EVENT_AFTER_FORWARD_LINK)

    def back_link(self, *devs, auto=True):
        for i in devs:
            self.inputs.append(i)
            if auto:
                i.forward_link(self, auto=False)

        self.emit(self.EVENT_AFTER_BACK_LINK)


if __name__ == "__main__":
    ds = Device(name="1")
    d = Device(name="2")
    df = Device(name="3")

    ds.subscribe(Device.EVENT_OUT, lambda x: print(f"OUT1 {x}"))
    d.subscribe(Device.EVENT_OUT, lambda x: print(f"OUT2 {x}"))
    df.subscribe(Device.EVENT_OUT, lambda x: print(f"OUT3 {x}"))

    ds.forward_link(d)
    d.forward_link(df)
    # df.forward_link(ds)

    # print(ds.inputs, ds.outputs)
    # print(d.inputs, d.outputs)
    # print(df.inputs, df.outputs)

    ds(Wave(QuantumState((0, 0))))
