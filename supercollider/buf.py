class BufferManager(object):
    def __init__(self):
        self.freeset = set()
        self.next_unused = 0

    def next(self):
        try:
            return self.freeset.pop()
        except KeyError:
            n = self.next_unused
            self.next_unused = n + 1
            return n

    def release(self, n):
        if n == self.next_unused - 1:
            self.next_unused = n
            while self.next_unused - 1 in self.freeset:
                self.freeset.remove(self.next_unused - 1)
                self.next_unused = self.next_unused - 1
        else:
            self.freeset.add(n)

manager = BufferManager()
