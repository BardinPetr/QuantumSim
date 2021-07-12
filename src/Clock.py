from asyncio import sleep


class Clock:
    def __init__(self, period, real_period=0):
        self.period = period
        self.real_period = real_period
        self.run = True

    def __del__(self):
        self.run = False

    async def work(self):
        current_time = 0

        while self.run:
            yield current_time
            current_time += self.period
            if self.real_period > 0:
                await sleep(self.real_period)
