import supercollider.oscutil

class AddAction:
    GROUP_HEAD = 0
    GROUP_TAIL = 1
    BEFORE = 2
    AFTER = 3
    REPLACE = 4

class IdDispenser:
    def __init__(self, init_id = 0x100000):
        self.next_id = init_id
    def next(self):
        id = self.next_id
        self.next_id = id + 1
        return id
id_dispenser = IdDispenser()

class Node(object):
    def __init__(self, synthdef_name, id = None):
        self.id = id
        self.synthdef_name = synthdef_name
        if self.id is None:
            self.id = id_dispenser.next()
        self.controls = {}

    def set(self, *args):
        for i in range(len(args) / 2):
            self.controls[args[i*2]] = args[i*2+1]
        return self

    def inits(self, controlnamefilter = None):
        inits = []
        for (n, v) in self.controls.iteritems():
            if controlnamefilter is None or n in controlnamefilter:
                inits.append(n)
                inits.append(float(v))
        return inits

    def s_new(self, add_action = AddAction.GROUP_HEAD, add_target = 1):
        inits = self.inits()
        return supercollider.oscutil.msg("/s_new",
                                         self.synthdef_name,
                                         self.id,
                                         add_action,
                                         add_target,
                                         *inits)

    def n_set(self, controlnamefilter = None):
        inits = self.inits(controlnamefilter)
        return supercollider.oscutil.msg("/n_set", self.id, *inits)

    def n_free(self):
        return supercollider.oscutil.msg("/n_free", self.id)
