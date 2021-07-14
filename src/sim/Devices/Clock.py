from time import sleep

from src.sim.MainDevices.Device import Device


class Clock(Device):
    EVENT_TICK = "event_tick"

    def __init__(self, period, real_period=0, name="Clock"):
        super().__init__(name)

        self.period = period
        self.real_period = real_period
        self.run = True

    def __del__(self):
        self.run = False

    def work(self):
        current_time = 0

        while self.run:
            yield current_time
            self.emit(Clock.EVENT_TICK, current_time)
            current_time += self.period
            if self.real_period > 0:
                sleep(self.real_period)
