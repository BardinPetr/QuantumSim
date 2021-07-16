import json

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from scipy import signal
from scipy.interpolate import make_interp_spline
from scipy.signal import medfilt, savgol_filter, wiener, symiirorder1, decimate, filtfilt

from src.sim.Data.HardwareParams import HardwareParams
from src.sim.Math.QBERGen import simulate_bb84


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


def moving_average(x, w):
    return np.convolve(x, np.ones(w), 'valid') / w


if __name__ == '__main__':
    sr = StatisticsReader(path_to_statistics='../data/statistics.json')

    sr.parse()

    emitted_waves_count = sr.get_parameter_values('emitted_waves_count')
    received_waves_count = sr.get_parameter_values('key_length')

    q = received_waves_count / emitted_waves_count
    laser_freq = 1 / sr.data['params'][0]['laser_period']

    practical_values = q * laser_freq

    theoretical_values = sr.get_theoretical_data(0)

    mean = signal.filtfilt(*signal.ellip(11, 0.07, 50, 0.09), practical_values)

    fig, axs = plt.subplots(2, sharex='col')

    fig.suptitle('R(sift)')

    axs[0].plot(theoretical_values, color='red', linestyle='dashed')
    axs[0].plot(practical_values, color='blue')

    axs[1].plot(theoretical_values, color='red', linestyle='dashed')
    axs[1].plot(mean, color='blue')

    plt.show()
