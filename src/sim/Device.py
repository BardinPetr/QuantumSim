from typing import List, Any, Union

from src.sim.Particles.Photon import Photon
from src.sim.QuantumState import QuantumState


class PhotonPart:
    def __init__(self, base_photon: Photon):
        self.base_photon = base_photon

    @staticmethod
    def split(photon: Photon, n):
        return [PhotonPart(photon)] * n


class Device:
    EVENT_PH_IN = "photon_in"
    EVENT_PH_OUT = "photon_out"

    def __init__(self, name="Basic Device"):
        self.events = dict()

        self.outputs = list()
        self.inputs = list()
        self.name = name

    def __repr__(self):
        return self.name

    def __call__(self, photon: Union[Photon, PhotonPart]) -> List[Any]:
        if len(self.inputs) > 1:
            raise NotImplementedError()

        self.emit(Device.EVENT_PH_IN, photon)

        if isinstance(photon, Photon):
            result = self.process_full(photon)
            if result is None:
                return []
            if not isinstance(result, list):
                result = [result]
        else:
            # photon = self.process_part(photon)
            raise NotImplementedError()

        self.emit(Device.EVENT_PH_OUT, result)

        if len(self.outputs) == 1:
            if len(result) == len(self.outputs):
                return [i(j) for i, j in zip(self.outputs, result)]
            else:
                raise NotImplementedError()

    def process_full(self, photon: Photon) -> List[Union[Photon, PhotonPart, None]]:
        # print(f"Processed photon {photon}")
        return [photon]

    def process_part(self, photon: PhotonPart):
        print(f"Processed photon part {photon}")
        raise NotImplementedError()

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

    ds.subscribe(Device.EVENT_PH_OUT, lambda x: print(f"OUT1 {x}"))
    d.subscribe(Device.EVENT_PH_OUT, lambda x: print(f"OUT2 {x}"))
    df.subscribe(Device.EVENT_PH_OUT, lambda x: print(f"OUT3 {x}"))

    ds.forward_link(d)
    d.forward_link(df)
    # df.forward_link(ds)

    # print(ds.inputs, ds.outputs)
    # print(d.inputs, d.outputs)
    # print(df.inputs, df.outputs)

    ds(Photon(QuantumState((0, 0))))
