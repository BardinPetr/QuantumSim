import os
from typing import List

from numpy.typing import NDArray

from src.sim.Utils.StatisticsData import StatisticsData
from src.KeyManager import KeyManager

class FileWriter:
    def __init__(self, stat_path: str, key_managers: List[KeyManager], clear_files: bool = False):
        self.key_managers = key_managers

        self.stat_path = stat_path

        if clear_files or not os.path.isfile(stat_path):
            with open(self.stat_path, 'w') as f:
                f.write('[]')

        if clear_files:
            for key_manager in self.key_managers:
                with open(key_manager.path, 'w'):
                    f.write('')

    def write(self, data: StatisticsData):
        with open(self.stat_path, 'ab+') as f:
            f.seek(-1, os.SEEK_END)
            f.truncate()
            f.write(f'\n{data.to_json()}]'.encode('utf-8'))

    def append_key(self, user: int, key: NDArray):
        self.key_managers[user].append(key)
