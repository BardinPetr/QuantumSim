import json

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

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

        for i in self.data['params']:
            i['laser_period'] *= 1e-9
            i['dt'] *= 1e-9

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

    # practical_values = sr.get_parameter_values('qber', -100)
    #
    # theoretical_values = sr.get_theoretical_data(0, -100)
    #
    # mean = signal.filtfilt(*signal.ellip(11, 0.07, 50, 0.09), practical_values)
    #
    # fig, axs = plt.subplots(2, sharex='col')
    #
    # fig.suptitle('QBER')
    #
    # axs[0].plot(theoretical_values, color='red', linestyle='dashed')
    # axs[0].plot(practical_values, color='blue')
    #
    # axs[1].plot(theoretical_values, color='red', linestyle='dashed')
    # axs[1].plot(mean, color='blue')
    #
    # plt.show()

    # QBER
    # practical_data = sr.get_parameter_values('qber')
    # theoretical_data = sr.get_theoretical_data(1)

    # R(sift)
    laser_frequency = 1 / np.array([i['laser_period'] for i in sr.get_parameter_values('params')])
    q = sr.get_parameter_values('received_waves_count') / sr.get_parameter_values('emitted_waves_count')

    practical_data = laser_frequency * q
    theoretical_data = sr.get_theoretical_data(4)

    plt.figure(figsize=(5 * 1.6, 5))

    n, bins, patches = plt.hist(practical_data, bins=10, density=True, label='Распределение практического значения')
    plt.axvline(theoretical_data[0], color='r', label='Теоретическое значение')

    print('Среднее значение из эксперимента:', np.mean(practical_data))
    print('Среднеквадратическое отклонение:', np.std(practical_data))
    print('Отклонение теоретического значения от среднего:', abs(np.mean(practical_data) - theoretical_data[0]))

    # print(pres(output='qber'))
    # print(np.mean(qbers) - pres(output='qber'))
    # print(np.std(qbers))

    plt.xlabel('R(raw)')
    plt.ylabel('Количество')

    plt.legend(loc='upper left', bbox_to_anchor=(0.285, 1.17))

    # plt.show()

    plt.savefig('rraw.png', dpi=300)
