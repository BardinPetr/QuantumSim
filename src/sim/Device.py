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
    def __init__(self, photon_in_cb=None, photon_out_cb=None, name="Basic Device"):
        self.photon_out_cbs = list() if photon_out_cb is None else [photon_out_cb]
        self.photon_in_cbs = list() if photon_in_cb is None else [photon_in_cb]
        self.outputs = list()
        self.inputs = list()
        self.name = name

    def __repr__(self):
        return self.name

    def __call__(self, photon: Union[Photon, PhotonPart]) -> List[Any]:
        for i in self.photon_in_cbs:
            i(photon)

        if isinstance(photon, Photon):
            photon = self.process_full(photon)
        else:
            raise NotImplementedError()
            # photon = self.process_part(photon)

        for i in self.photon_out_cbs:
            i(photon)

        if len(self.outputs) == 1:
            return self.outputs[0](photon)
        elif len(self.outputs) > 1:
            raise NotImplementedError()
            # for i in PhotonPart.split(photon):
            # return [i(PhotonPart(photon)) for i in self.outputs]

    def process_full(self, photon: Photon) -> Union[Photon, None]:
        # print(f"Processed photon {photon}")
        return photon

    def process_part(self, photon: PhotonPart) -> Photon:
        print(f"Processed photon part {photon}")
        return Photon(QuantumState((complex(0, 0), complex(0, 0))))

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

    def append_out_cb(self, cb):
        self.photon_out_cbs.append(cb)

    def remove_out_cb(self, num):
        self.photon_out_cbs.pop(num)

    def append_in_cb(self, cb):
        self.photon_in_cbs.append(cb)

    def remove_in_cb(self, num):
        self.photon_in_cbs.pop(num)


if __name__ == "__main__":
    ds = Device(name="1")
    d = Device(name="2")
    df = Device(name="3")

    ds.append_out_cb(lambda x: print(f"OUT1 {x}"))
    d.append_out_cb(lambda x: print(f"OUT2 {x}"))
    df.append_out_cb(lambda x: print(f"OUT3 {x}"))

    ds.forward_link(d)
    d.forward_link(df)
    df.forward_link(ds)

    # print(ds.inputs, ds.outputs)
    # print(d.inputs, d.outputs)
    # print(df.inputs, df.outputs)

    ds(Photon(QuantumState((0, 0))))
