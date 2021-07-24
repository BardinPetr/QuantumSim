import time
from threading import Thread

import zmq


class LockServer:
    STATE_REL = 0
    STATE_ACC = 1

    def __init__(self, pub_port=9990, rep_port=9991):
        self.running = True
        self.locks = dict()

        cnt = zmq.Context()
        self.rep = cnt.socket(zmq.REP)
        self.rep.bind(f"tcp://0.0.0.0:{rep_port}")
        self.pub = cnt.socket(zmq.PUB)
        self.pub.bind(f"tcp://0.0.0.0:{pub_port}")

        self.thread = Thread(target=self._run, daemon=True)
        self.thread.start()

    def __del__(self):
        self.running = False

    def _run(self):
        while self.running:
            data = self.rep.recv_json()
            name, idx = data['name'], data['id']
            if data['mode'] == 1:  # acquire
                self.locks[name] = self.locks.get(name, [])
                if idx not in self.locks[name]:
                    self.locks[name].append(idx)
                if len(self.locks[name]) == 1:
                    self.rep.send_json({'mode': LockServer.STATE_ACC})
                    # print(f"Acquired for {name}")
                    continue
            elif name in self.locks and len(self.locks[name]) > 0:  # release
                # print(f"Sended release {name}  {self.locks}")
                self.locks[name].pop(0)
                if len(self.locks[name]) > 0:
                    self.pub.send_json({'name': name, 'id': self.locks[name][0]})

            self.rep.send_json({'mode': LockServer.STATE_REL})


class LockClient:
    def __init__(self, ip, pub_port=9990, rep_port=9991, identity=None):
        self.running = True
        self.acquired = set()
        self.identity = str(id(self)) if identity is None else identity

        cnt = zmq.Context()
        self.req = cnt.socket(zmq.REQ)
        self.req.connect(f"tcp://{ip}:{rep_port}")
        self.sub = cnt.socket(zmq.SUB)
        self.sub.connect(f"tcp://{ip}:{pub_port}")
        self.sub.setsockopt_string(zmq.SUBSCRIBE, '')

        self.thread = Thread(target=self._run, daemon=True)
        self.thread.start()

    def __del__(self):
        self.running = False

    def _run(self):
        while self.running:
            update = self.sub.recv_json()
            if update['name'] in self.acquired and update['id'] == self.identity:
                self.acquired.remove(update['name'])

    def _request(self, state, name, ident=None) -> bytes:
        self.req.send_json({
            'id':   self.identity if ident is None else ident,
            'name': name,
            'mode': state
        })
        return self.req.recv_json()['mode']

    def acquire(self, name, timeout=None):
        t_start = time.time()
        resp = self._request(LockServer.STATE_ACC, name)
        self.acquired.add(name)
        if resp == LockServer.STATE_ACC:  # acquired
            # print("!", name)
            return True
        while name in self.acquired:
            if timeout is not None and (time.time() - t_start) > timeout:
                return False
            time.sleep(0.0001)
        return True

    def release(self, name):
        self._request(LockServer.STATE_REL, name)

    def release_other(self, name, ident):
        # print(name, ident)
        self._request(LockServer.STATE_REL, name, ident)


if __name__ == "__main__":
    svr = LockServer()
    while True: pass
