import os

from src.statistics.StatisticsData import StatisticsData

"""
Write statistics from StatisticsData to json file
"""


class StatisticsWriter:
    def __init__(self, statistics_file_path: str, clear_files: bool = False):
        self.file_path = statistics_file_path
        self.sessions_count = 0

        if clear_files or not os.path.isfile(self.file_path):
            with open(self.file_path, 'w') as f:
                f.write('[]')

    def write(self, data: StatisticsData):
        with open(self.file_path, 'ab+') as f:
            f.seek(-1, os.SEEK_END)
            f.truncate()
            f.write(f'{("," if self.sessions_count != 0 else "")}\n{data.to_json()}]'.encode('utf-8'))

        self.sessions_count += 1
