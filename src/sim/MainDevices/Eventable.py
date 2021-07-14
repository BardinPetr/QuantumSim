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

    def emit(self, eid, *args):
        for i in self.events.get(eid, {}).values():
            i(*args)
