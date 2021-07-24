from threading import Thread
from time import sleep


class Eventable:
    def __init__(self):
        self.events = dict()
        self.event_results = dict()

    def subscribe(self, eid, cb):
        if eid not in self.events:
            self.events[eid] = dict()
        cb_id = len(self.events[eid])
        self.events[eid][cb_id] = cb
        return cb_id

    def unsubscribe(self, eid, cb_id):
        del self.events[eid][cb_id]

    def _emit(self, on_response, eid, *args):
        for i in self.events.get(eid, {}).values():
            res = i(*args)
            if on_response is not None:
                on_response(res)

    def emit(self, eid, *args, on_response=None, threaded=False):
        if threaded:
            thread = Thread(target=self._emit, args=(on_response, eid, *args), daemon=True)
            thread.start()
        else:
            self._emit(on_response, eid, *args)

    def set_proc_result(self, pid, res):
        self.event_results[pid] = res

    def wait_for_result(self, pid):
        while pid not in self.event_results:
            sleep(0.0001)
        res = self.event_results[pid]
        del self.event_results[pid]
        return res
