from typing import List, Any, Union

# from src.sim.Photon import Photon, PhotonPart
from src.sim.QuantumState import QuantumState


class Photon:
    def __init__(self, state: QuantumState):
        self.state = state
        self.time = 0


class PhotonPart:
    def __init__(self, base_photon: Photon):
        self.base_photon = base_photon

    @staticmethod
    def split(photon: Photon, n):
        return [PhotonPart(photon)] * n


class Device:
    def __init__(self, name="Basic Device"):
        self.outputs = list()
        self.inputs = list()
        self.name = name

    def __repr__(self):
        return self.name

    def process_full(self, photon: Photon) -> Photon:
        print(f"Processed photon {photon}")
        return photon

    def process_part(self, photon: PhotonPart) -> Photon:
        print(f"Processed photon part {photon}")

        return Photon(QuantumState((complex(0, 0), complex(0, 0))))

    def __call__(self, photon: Union[Photon, PhotonPart]) -> List[Any]:
        if isinstance(photon, Photon):
            photon = self.process_full(photon)
        else:
            photon = self.process_part(photon)

        # if len(self.outputs) == 1:
        #     return [next(iter(self.outputs))(photon)]
        # else:
        #     # for i in PhotonPart.split(photon):
        #     return [i(PhotonPart(photon)) for i in self.outputs]

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


ds = Device("1")
d = Device("2")
df = Device("3")

ds.forward_link(d)
d.forward_link(df)
df.forward_link(ds)

print(ds.inputs, ds.outputs)
print(d.inputs, d.outputs)
print(df.inputs, df.outputs)

# ds(Photon(QuantumState((0, 0))))