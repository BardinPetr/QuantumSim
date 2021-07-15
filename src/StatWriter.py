import os
from typing import List

from numpy.typing import NDArray

from src.KeyManager import KeyManager
from src.sim.Utils.StatisticsData import StatisticsData


class StatWriter:
    def __init__(self, stat_path: str, clear_files: bool = False):
        self.stat_path = stat_path
        self.sessions_count = 0

        if clear_files or not os.path.isfile(stat_path):
            with open(self.stat_path, 'w') as f:
                f.write('[]')

    def write(self, data: StatisticsData):
        with open(self.stat_path, 'ab+') as f:
            f.seek(-1, os.SEEK_END)
            f.truncate()
            f.write(f'{("," if self.sessions_count != 0 else "")}\n{data.to_json()}]'.encode('utf-8'))

        self.sessions_count += 1
