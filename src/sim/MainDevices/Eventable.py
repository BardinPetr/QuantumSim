from queue import Queue
from threading import Thread
from typing import Optional


class Eventable:
    def __init__(self):
        self.events = dict()

    def subscribe(self, eid, cb):
        if eid not in self.events:
            self.events[eid] = dict()
        cb_id = len(self.events[eid])
        self.events[eid][cb_id] = cb
        return cb_id

    def unsubscribe(self, eid, cb_id):
        del self.events[eid][cb_id]

    def _emit(self, wait_response, queue: Optional[Queue], eid, *args):
        for i in self.events.get(eid, {}).values():
            if wait_response:
                res = i(*args)
                if queue is not None:
                    queue.put(res)
                else:
                    return res
            else:
                i(*args)

    def emit(self, eid, *args, wait_response=False, threaded=False):
        if threaded:
            q = Queue()
            thread = Thread(target=self._emit, args=(wait_response, q, eid, *args), daemon=True)
            thread.start()
            if wait_response:
                thread.join()
                return q.get(timeout=0.1)
        else:
            return self._emit(wait_response, None, eid, *args)
