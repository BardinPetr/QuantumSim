
class KeyManager:

    def __init__(self, path):
        self.file = open(path, 'rb')

    def close(self):
        self.file.close()

    def get_key(self, length):
        return self.file.read(length)

