import asyncio


class Clock:
    def __init__(self, period):
        self.period = period
        self.run = True

    def __del__(self):
        self.run = False

    async def work(self):
        current_time = 0

        while self.run:
            yield current_time
            current_time += self.period
