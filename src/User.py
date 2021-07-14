from src.utils.rand import rand_bin


class User:
    def __init__(self):
        self.bases = []  # bases that this user choose
        self.wave_time = []  # list of time, when waves was measured or emitted
        self.raw_information = []  # raw information of user

    def choose_basis(self):
        basis = 1 / 2 if rand_bin(0.5) else 0
        self.bases.append(basis)

        return basis
