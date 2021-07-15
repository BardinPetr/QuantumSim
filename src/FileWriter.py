import os
from typing import List

from numpy.typing import NDArray

from src.KeyManager import KeyManager
from src.sim.Utils.StatisticsData import StatisticsData


class FileWriter:
    def __init__(self, stat_path: str, key_managers: List[KeyManager], clear_files: bool = True):
        self.key_managers = key_managers
        self.stat_path = stat_path
        self.sessions_count = 0

        if clear_files or not os.path.isfile(stat_path):
            with open(self.stat_path, 'w') as f:
                f.write('[]')

        if clear_files:
            for key_manager in self.key_managers:
                key_manager.clear()

    def write(self, data: StatisticsData):
        with open(self.stat_path, 'ab+') as f:
            f.seek(-1, os.SEEK_END)
            f.truncate()
            f.write(f'{("," if self.sessions_count != 0 else "")}\n{data.to_json()}]'.encode('utf-8'))

        self.sessions_count += 1

    def append_key(self, user: int, key: NDArray):
        self.key_managers[user].append(key)
