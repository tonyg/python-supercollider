import oscutil

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

def _maybeAppendCompletionMsg(m, completion_msg):
    if completion_msg is not None:
        m.append(completion_msg.getBinary(), 'b')

def alloc(buffer_number,
          frame_count,
          channel_count = 1,
          completion_msg = None):
    m = oscutil.msg("/b_alloc")
    m.append(buffer_number)
    m.append(frame_count)
    m.append(channel_count)
    _maybeAppendCompletionMsg(m, completion_msg)
    return m

def allocRead(buffer_number,
              path,
              start_frame = 0,
              frame_count = 0, # means entire file
              completion_msg = None):
    m = oscutil.msg("/b_allocRead")
    m.append(buffer_number)
    m.append(path)
    m.append(start_frame)
    m.append(frame_count)
    _maybeAppendCompletionMsg(m, completion_msg)
    return m

def read(buffer_number,
         path,
         file_start_frame = 0,
         frame_count = -1, # means entire file
         buffer_start_frame = 0,
         leave_file_open = False,
         completion_msg = None):
    m = oscutil.msg("/b_read")
    m.append(buffer_number)
    m.append(path)
    m.append(file_start_frame)
    m.append(frame_count)
    m.append(buffer_start_frame)
    if leave_file_open:
        m.append(1)
    else:
        m.append(0)
    _maybeAppendCompletionMsg(m, completion_msg)
    return m

def write(buffer_number,
          path,
          header_format = "wav",
          sample_format = "int16",
          frame_count = -1,
          buffer_start_frame = 0,
          leave_file_open = False,
          completion_msg = None):
    m = oscutil.msg("/b_write")
    m.append(buffer_number)
    m.append(path)
    m.append(header_format)
    m.append(sample_format)
    m.append(frame_count)
    m.append(buffer_start_frame)
    if leave_file_open:
        m.append(1)
    else:
        m.append(0)
    _maybeAppendCompletionMsg(m, completion_msg)
    return m

def free(buffer_number,
         completion_msg = None):
    m = oscutil.msg("/b_free")
    m.append(buffer_number)
    _maybeAppendCompletionMsg(m, completion_msg)
    return m

def zero(buffer_number,
         completion_msg = None):
    m = oscutil.msg("/b_zero")
    m.append(buffer_number)
    _maybeAppendCompletionMsg(m, completion_msg)
    return m
