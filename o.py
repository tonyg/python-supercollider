import OSC1 as OSC
import time
import struct

class IdDispenser:
    def __init__(self, init_id = 0x100000):
        self.next_id = init_id
    def next(self):
        id = self.next_id
        self.next_id = id + 1
        return id
id_dispenser = IdDispenser()

def msg(address, *args):
    m = OSC.OSCMessage(address)
    for a in args:
        m.append(a)
    return m

def bundle(*msgs):
    b = OSC.OSCBundle()
    for m in msgs:
        b.append(m)
    return b

seconds1900To1970 = 2208988800L
def timedBundle(timeTag, *msgs):
    b = bundle(*msgs)
    # It's *local* time (ugh) and it's based on a 1900 epoch...
    b.setTimeTag(timeTag + seconds1900To1970)
    return b

class AddAction:
    GROUP_HEAD = 0
    GROUP_TAIL = 1
    BEFORE = 2
    AFTER = 3
    REPLACE = 4

# 23:05:56.595248 IP walk.57120 > walk.57110: UDP, length 316
#         0x0000:  4500 0158 95c6 0000 4011 0000 7f00 0001  E..X....@.......
#         0x0010:  7f00 0001 df20 df16 0144 ff57 2362 756e  .........D.W#bun
#         0x0020:  646c 6500 0000 0000 0000 0001 0000 0128  dle............(
#         0x0030:  2f64 5f72 6563 7600 2c62 6900 0000 0113  /d_recv.,bi.....

#         0x0040:  5343 6766 0000 0001 0001 0474 6973 6800  SCgf.......tish.
#         0x0050:  0300 0000 003e 9999 9a3c 23d7 0a00 0244  .....>...<#....D
#         0x0060:  9600 0040 0000 0000 0204 6672 6571 0000  ...@......freq..
#         0x0070:  0472 6174 6500 0100 0907 436f 6e74 726f  .rate.....Contro
#         0x0080:  6c01 0000 0002 0000 0101 0749 6d70 756c  l..........Impul
#         0x0090:  7365 0200 0200 0100 0000 0000 01ff ff00  se..............
#         0x00a0:  0002 0c42 696e 6172 794f 7055 4765 6e02  ...BinaryOpUGen.
#         0x00b0:  0002 0001 0002 0001 0000 ffff 0001 0206  ................
#         0x00c0:  4465 6361 7932 0200 0300 0100 0000 0200  Decay2..........
#         0x00d0:  00ff ff00 02ff ff00 0102 0a57 6869 7465  ...........White
#         0x00e0:  4e6f 6973 6502 0000 0001 0000 020c 4269  Noise.........Bi
#         0x00f0:  6e61 7279 4f70 5547 656e 0200 0200 0100  naryOpUGen......
#         0x0100:  0200 0400 0000 0300 0002 0a57 6869 7465  ...........White
#         0x0110:  4e6f 6973 6502 0000 0001 0000 020c 4269  Noise.........Bi
#         0x0120:  6e61 7279 4f70 5547 656e 0200 0200 0100  naryOpUGen......
#         0x0130:  0200 0600 0000 0300 0002 034f 7574 0200  ...........Out..
#         0x0140:  0300 0000 00ff ff00 0000 0500 0000 0700  ................
#         0x0150:  0000 0064 0000 0000                      ...d....

def flatten(l):
    if type(l) == list:
        return ''.join((flatten(v) for v in l))
    else:
        return l

def eu8(v): return struct.pack('>B', v)
def eu16(v): return struct.pack('>H', v)
def eu32(v): return struct.pack('>I', v)
def ef32(v): return struct.pack('>f', v)
def estr(v): return struct.pack('>B', len(v)) + v

def compileDefs(synthdefs):
    for s in synthdefs: s.resolve()
    return flatten(['SCgf', # magic
                    eu32(0), ## file version (always zero, for now,
                             ## though version 1 has been seen in the wild!)
                    eu16(len(synthdefs)), [s.compile() for s in synthdefs]])

class ArgSpec(object):
    def __init__(self, name, defaultValue = None):
        self.name = name
        self.defaultValue = defaultValue

    def configure(self, spec, value):
        if value is None:
            if self.defaultValue is None:
                raise Exception('no default value for argspec', self)
            spec.addConstantInput(self.defaultValue)
        elif type(value) == float:
            spec.addConstantInput(value)
        else:
            spec.addUgenInput(value.realSpec(), value.outputNumber())

def expand_multichannel(args):
    maxlen = 1
    for arg in args:
        if type(arg) == tuple:
            maxlen = max(maxlen, len(arg))
    result = []
    for i in range(maxlen):
        result.append([])
        for arg in args:
            if type(arg) == tuple:
                result[i].append(arg[i % len(arg)])
            else:
                result[i].append(arg)
    return result

class SynthDef(object):
    def __init__(self, name):
        self.name = name
        self.constants = {}
        self.parameters = []
        self.parameter_names = {}
        self.ugens = {}

    def addConstant(self, floatVal):
        if floatVal not in self.constants:
            self.constants[floatVal] = len(self.constants)

    def addParam(self, pinit, pname):
        ## TODO: maybe the spec can support parameter aliases? This is
        ## why pname is last - so we can in future add *aliases to the
        ## arg list of this method, if we like.
        self.parameter_names[pname] = len(self.parameters)
        self.parameters.append(pinit)

    def addUgen(self, spec):
        if spec not in self.ugens:
            self.ugens[spec] = len(self.ugens)

    def resolve(self):
        ## TODO: make resolution produce a depth-first serialization
        ## of the ugen graph, as per the documentation. Apparently it
        ## makes better use of buffers that way.
        for u in self.ugens.keys():
            u.resolve(self)

    def lookupConstant(self, floatVal):
        return self.constants[floatVal]

    def lookupUgen(self, spec):
        return self.ugens[spec]

    def compile(self):
        return [estr(self.name),

                eu16(len(self.constants)),
                [ef32(v[0]) for v in sorted(self.constants.items(), key=lambda x:x[1])],

                eu16(len(self.parameters)),
                [ef32(v) for v in self.parameters],
                eu16(len(self.parameter_names)),
                [estr(v[0]) + eu16(v[1]) for v in self.parameter_names.items()],

                eu16(len(self.ugens)),
                [v[0].compile(self) for v in sorted(self.ugens.items(), key=lambda x:x[1])]
                ]

class CalcRate:
    RATE_SCALAR = 0
    RATE_CONTROL = 1
    RATE_AUDIO = 2

class UGenSpec(object):
    def __init__(self, classname, calcrate, special_index = 0):
        self.classname = classname
        self.calcrate = calcrate
        self.special_index = special_index
        self.inputs = []
        self.outputs = []

    def addConstantInput(self, f):
        self.inputs.append(f)

    def addUgenInput(self, u, outputIndex):
        self.inputs.append((u, outputIndex))

    def addOutput(self, rate):
        self.outputs.append(rate)

    def resolve(self, synthDef):
        for i in self.inputs:
            if type(i) == float:
                synthDef.addConstant(i)
            else:
                synthDef.addUgen(i[0])

    def compileInput(self, i, synthDef):
        if type(i) == float:
            return eu16(0xffff) + eu16(synthDef.lookupConstant(i))
        else:
            return eu16(synthDef.lookupUgen(i[0])) + eu16(i[1])

    def compile(self, synthDef):
        return [estr(self.classname),
                eu8(self.calcrate),
                eu16(len(self.inputs)),
                eu16(len(self.outputs)),
                eu16(self.special_index),
                [self.compileInput(i, synthDef) for i in self.inputs],
                [eu8(o) for o in self.outputs]]

    def realSpec(self):
        return self

    def outputNumber(self):
        return 0

    def __add__(self, other):
        return BinOpUGen.construct(compute_rate(self, other), BinOp.PLUS, self, other)

    def __mul__(self, other):
        return BinOpUGen.construct(compute_rate(self, other), BinOp.TIMES, self, other)

class UnOp:
    NEG = 0

class BinOp:
    PLUS = 0
    MINUS = 1
    TIMES = 2
    DIVIDE = 3
    MOD = 4
    MIN = 5
    MAX = 6

class UGenBase(object):
    special_index = 0
    spec_class = UGenSpec

    @classmethod
    def kr(cls, *args): return cls.construct(CalcRate.RATE_CONTROL, cls.special_index, *args)

    @classmethod
    def ar(cls, *args): return cls.construct(CalcRate.RATE_AUDIO, cls.special_index, *args)

    @classmethod
    def construct(cls, calcrate, special_index, *args):
        arglists = expand_multichannel(args)
        specs = []
        for arglist in arglists:
            spec = cls.spec_class(cls.classname, calcrate, special_index)
            for i in range(len(arglist)):
                argspec = cls.argspecs[i]
                arg = arglist[i] if i < len(arglist) else None
                argspec.configure(spec, arg)
            specs.append(spec)
        if len(specs) == 1:
            return specs[0]
        else:
            return specs

class OutputProxy(object):
    def __init__(self, spec, index):
        self.spec = spec
        self.index = index

    def realSpec(self):
        return self.spec

    def outputNumber(self):
        return self.index

class Node(object):
    def __init__(self, synthdef_name, id = None):
        self.id = id
        self.synthdef_name = synthdef_name
        if self.id is None:
            self.id = id_dispenser.next()

    def s_new(self, add_action = AddAction.GROUP_HEAD, add_target = 1):
        return msg("/s_new", self.synthdef_name, self.id, add_action, add_target)

    def n_free(self):
        return msg("/n_free", self.id)

def main():
    hostname = 'walk'

    s = OSC.OSCServer((hostname, 14641))
    s.addMsgHandler('default', s.msgPrinter_handler)

    m = OSC.OSCMessage("/status")
    c = s.client
    c.sendto(m, (hostname, 57110))

    def send(msgOrBundle):
        c.sendto(msgOrBundle, (hostname, 57110))

    n = Node("tutorial-SinOsc")
    send(msg("/notify", 0))
    send(msg("/notify", 1))
    send(timedBundle(time.time() + 1.0, n.s_new()))
    send(timedBundle(time.time() + 2.0, n.n_free()))

    s.serve_forever()

def m2():
    pass