import asyncio
import time


class Photon:
    pass


fl = open('test', 'w')


async def generate(f):
    t = time.time()
    t1 = time.time()
    while True:
        dt = time.time() - t
        # if True:  # dt > 1 / f:
        yield Photon()
        fl.write("%d\n" % ((time.time() - t1) * 10e6) )
        if dt < 1 / f:
            await asyncio.sleep((1 / f) - dt)
        t = time.time()
        t1 = time.time()


async def main():
    async for i in generate(5 * 10e3):
        # print(i)
        i.__hash__()



asyncio.run(main())

# import time
# from datetime import timedelta
#
# from timeloop import Timeloop
#
# tl = Timeloop()
#
# t = time.time()
#
#
#
# # @tl.job(interval=timedelta(seconds=1 / (5 * 10e6)))
#
# def sample_job_every_2s():
#     global t
#     print((time.time() - t) * 10e6)
#     t = time.time()
#
#
# import threading
# if __name__ == "__main__":
#     # tl.start(block=True)
#     threading.Timer(1 / (5 * 10e6), sample_job_every_2s).start()
#     time.sleep(10)
