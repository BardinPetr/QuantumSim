import json

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from scipy import signal

from src.sim.data.HardwareParams import HardwareParams
from src.math.theoretical_data_generator import simulate_bb84

"""
Read statistics from json file and parse it
"""


class StatisticsReader:
    def __init__(self, path_to_statistics: str):
        self.path = path_to_statistics
        self.data = None

    def get_statistics_file_content(self):
        with open(self.path, 'r') as f:
            content = f.read()

        return json.loads(content)

    def parse(self):
        self.data = pd.DataFrame(self.get_statistics_file_content())
        return self.data

    def get_parameter_values(self, parameter: str, limit: int = None):
        return self.data[parameter][:(limit if limit else len(self.data))]

    def get_theoretical_data(self, parameter: int, limit: int = None):
        params = self.data['params'][:(limit if limit else len(self.data))]

        return [simulate_bb84(HardwareParams(**i))[parameter] for i in params]


if __name__ == '__main__':
    sr = StatisticsReader(path_to_statistics='../../data/statistics.json')

    sr.parse()

    practical_values = sr.get_parameter_values('qber', -100)

    theoretical_values = sr.get_theoretical_data(1, -100)

    mean = signal.filtfilt(*signal.ellip(11, 0.07, 50, 0.09), practical_values)

    fig, axs = plt.subplots(2, sharex='col')

    fig.set_figwidth(15)
    fig.set_figheight(10)

    axs[0].plot(practical_values, color='blue', label='Практическое значение')
    axs[0].plot(theoretical_values, color='red', linestyle='dashed', label='Теоретическое значение')

    axs[1].plot(mean[5:], color='blue', label='Усреднённое практическое значение')
    axs[1].plot(theoretical_values, color='red', linestyle='dashed', label='Теоретическое значение')

    axs[0].legend(loc="upper right", prop={'size': 15})
    axs[1].legend(loc="upper right", prop={'size': 15})

    plt.show()
