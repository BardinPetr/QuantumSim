from typing import Union
from src.sim.Wave import *


class Device:
    EVENT_IN = "wave_in"
    EVENT_OUT = "wave_out"

    def __init__(self, name="Basic Device"):
        self.events = dict()

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

        self.outputs[0](result)

    def process_full(self, wave: Wave) -> Union[Wave, None]:
        # print(f"Processed wave {photon}")
        return wave

    def forward_link(self, *devs, auto=True):
        for i in devs:
            self.outputs.append(i)
            if auto:
                i.back_link(self, auto=False)

    def back_link(self, *devs, auto=True):
        for i in devs:
            self.inputs.append(i)
            if auto:
                i.forward_link(self, auto=False)

    def subscribe(self, eid, cb):
        if eid not in self.events:
            self.events[eid] = dict()
        cb_id = len(self.events[eid])
        self.events[eid][cb_id] = cb
        return cb_id

    def unsubscribe(self, eid, cb_id):
        del self.events[eid][cb_id]

    def emit(self, eid, *args):
        for i in self.events.get(eid, {}).values():
            i(*args)


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
