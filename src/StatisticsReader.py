import json

from matplotlib import pyplot as plt


def flatten_dict(d, parent_key='', sep='.'):
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))

    return dict(items)


class StatisticsReader:
    def __init__(self, path_to_statistics: str):
        self.path = path_to_statistics
        self.data = {}

    def get_statistics_file_content(self):
        with open(self.path, 'r') as f:
            content = f.read()

        return json.loads(content)

    def parse(self):
        self.data = [flatten_dict(row, sep='.') for row in self.get_statistics_file_content()]
        return self.data

    def get_parameter_values(self, parameter: str, limit: int = -1):
        values = []

        for i in self.data[:(limit if limit > 0 else len(self.data))]:
            values.append(i[parameter])

        return values


if __name__ == '__main__':
    sr = StatisticsReader(path_to_statistics='../data/statistics.json')

    sr.parse()

    print(sr.data)

    values = sr.get_parameter_values('qber')

    plot = plt.plot(values)

    plt.show()
