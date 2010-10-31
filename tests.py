import unittest
import supercollider.buf

class TestBufferManager(unittest.TestCase):
    def setUp(self):
        self.m = supercollider.buf.BufferManager()

    def test_release(self):
        self.assertEqual(self.m.next(), 0)
        self.assertEqual(self.m.next(), 1)
        self.assertEqual(self.m.next(), 2)
        self.m.release(1)
        self.assertEqual(self.m.freeset, set([1]))
        self.assertEqual(self.m.next_unused, 3)
        self.m.release(2)
        self.assertEqual(self.m.freeset, set([]))
        self.assertEqual(self.m.next_unused, 1)
        self.m.release(0)
        self.assertEqual(self.m.freeset, set([]))
        self.assertEqual(self.m.next_unused, 0)

if __name__ == '__main__':
    unittest.main()
