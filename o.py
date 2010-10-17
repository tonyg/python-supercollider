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
    return flatten(['SCgf', # magic
                    eu32(1), ## file version
                    eu16(len(synthdefs)), [s.compile() for s in synthdefs],
                    eu16(0) ## number of variants
                    ])

class ArgSpec(object):
    def __init__(self, name, defaultValue = None):
        self.name = name
        self.defaultValue = defaultValue

    def configure(self, spec, value):
        if value is None:
            if self.defaultValue is None:
                raise Exception('no default value for argspec', self)
            spec.addConstantInput(self.defaultValue)
        elif type(value) == float or type(value) == int:
            spec.addConstantInput(value)
        else:
            spec.addUgenInput(value.realSpec(), value.outputNumber())

class MultiChannel(object):
    def __init__(self, specs):
        self.specs = specs

    def __getitem__(self, i):
        return self.specs[i]

    def __len__(self):
        return len(self.specs)

    def __neg__(self): return MultiChannel([-x for x in self.specs])
    def __add__(self, other): return MultiChannel([x + other for x in self.specs])
    def __sub__(self, other): return MultiChannel([x - other for x in self.specs])
    def __mul__(self, other): return MultiChannel([x * other for x in self.specs])
    def __div__(self, other): return MultiChannel([x / other for x in self.specs])
    def __mod__(self, other): return MultiChannel([x % other for x in self.specs])

def mc(*specs):
    return MultiChannel(specs)

def is_mc(x):
    return type(x) == MultiChannel

def expand_multichannel(args):
    maxlen = 1
    for arg in args:
        if is_mc(arg):
            maxlen = max(maxlen, len(arg))
    result = []
    for i in range(maxlen):
        result.append([])
        for arg in args:
            if is_mc(arg):
                result[i].append(arg[i % len(arg)])
            else:
                result[i].append(arg)
    return result

class SynthDef(object):
    def __init__(self, name, controldefs):
        self.name = name
        self.constants = {}
        self.parameters = []
        self.parameter_names = {}
        self.pending_ugens = set()
        self.ugens = {}
        for (name, init) in controldefs:
            self.addParam(init, name)
        self.controls = ControlSpec([d[0] for d in controldefs])

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
            if spec in self.pending_ugens:
                return
            self.pending_ugens.add(spec)
            spec.resolve(self)
            self.ugens[spec] = len(self.ugens)
            self.pending_ugens.remove(spec)

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

    def addConstantInput(self, f):
        self.inputs.append(float(f))

    def addUgenInput(self, u, outputIndex):
        self.inputs.append((u, outputIndex))

    def outputs(self):
        return [self.calcrate]

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
        outputs = self.outputs()
        return [estr(self.classname),
                eu8(self.calcrate),
                eu16(len(self.inputs)),
                eu16(len(outputs)),
                eu16(self.special_index),
                [self.compileInput(i, synthDef) for i in self.inputs],
                [eu8(o) for o in outputs]]

    def realSpec(self):
        return self

    def outputNumber(self):
        return 0

    def __neg__(self):
        return UnaryOpUGen.construct(self.calcrate, UnOp.NEG, self)

    def __add__(self, other):
        return BinaryOpUGen.construct(compute_rate(self, other), BinOp.PLUS, self, other)

    def __sub__(self, other):
        return BinaryOpUGen.construct(compute_rate(self, other), BinOp.MINUS, self, other)

    def __mul__(self, other):
        return BinaryOpUGen.construct(compute_rate(self, other), BinOp.TIMES, self, other)

    def __div__(self, other):
        return BinaryOpUGen.construct(compute_rate(self, other), BinOp.DIVIDE, self, other)

    def __mod__(self, other):
        return BinaryOpUGen.construct(compute_rate(self, other), BinOp.MOD, self, other)

class ControlSpec(UGenSpec):
    def __init__(self, controlnames):
        UGenSpec.__init__(self, 'Control', CalcRate.RATE_CONTROL)
        self.controlnames = controlnames

    def outputs(self):
        return [self.calcrate for n in self.controlnames]

    def controls(self):
        if len(self.controlnames) == 1:
            return self
        else:
            return [OutputProxy(self, i) for i in range(len(self.controlnames))]

    def lookupControl(self, controlname):
        return self.controlnames.index(controlname)

    def __len__(self):
        return len(self.controlnames)

    def __getitem__(self, i):
        if type(i) == int:
            if len(self.controlnames) == 1:
                return self
            else:
                return OutputProxy(self, i)
        else:
            return self[self.lookupControl(i)]

class OutSpec(UGenSpec):
    def outputs(self):
        return []

def compute_rate(a, b):
    if a.calcrate == CalcRate.RATE_AUDIO: return CalcRate.RATE_AUDIO
    if b.calcrate == CalcRate.RATE_AUDIO: return CalcRate.RATE_AUDIO
    if a.calcrate == CalcRate.RATE_CONTROL: return CalcRate.RATE_CONTROL
    if b.calcrate == CalcRate.RATE_CONTROL: return CalcRate.RATE_CONTROL
    return CalcRate.RATE_SCALAR

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
    LOG = 25
    LOG2 = 26
    LOG10 = 27

class UGenBase(object):
    special_index = 0
    spec_class = UGenSpec

    @classmethod
    def classname(cls):
        return cls.__name__

    @classmethod
    def kr(cls, *args): return cls.construct(CalcRate.RATE_CONTROL, cls.special_index, *args)

    @classmethod
    def ar(cls, *args): return cls.construct(CalcRate.RATE_AUDIO, cls.special_index, *args)

    @classmethod
    def construct(cls, calcrate, special_index, *args):
        arglists = expand_multichannel(args)
        specs = []
        for arglist in arglists:
            spec = cls.spec_class(cls.classname(), calcrate, special_index)
            for i in range(len(cls.argspecs)):
                argspec = cls.argspecs[i]
                arg = arglist[i] if i < len(arglist) else None
                argspec.configure(spec, arg)
            specs.append(spec)
        if len(specs) == 1:
            return specs[0]
        else:
            return MultiChannel(specs)

class BinaryOpUGen(UGenBase):
    argspecs = [ArgSpec('left'),
                ArgSpec('right')]

class UnaryOpUGen(UGenBase):
    argspecs = [ArgSpec('in')]

class SinOsc(UGenBase):
    argspecs = [ArgSpec('freq'),
                ArgSpec('phase', 0)]

class Line(UGenBase):
    argspecs = [ArgSpec('start', 0),
                ArgSpec('end', 1),
                ArgSpec('dur', 1),
                ArgSpec('doneAction', 0)]

class XLine(UGenBase):
    argspecs = [ArgSpec('start', 0),
                ArgSpec('end', 1),
                ArgSpec('dur', 1),
                ArgSpec('doneAction', 0)]

class Out(UGenBase):
    spec_class = OutSpec
    @classmethod
    def construct(cls, calcrate, special_index, bus, channels):
        spec = cls.spec_class(cls.classname(), calcrate, special_index)
        ArgSpec('bus').configure(spec, bus)
        for channel in channels:
            ArgSpec('source').configure(spec, channel)
        return spec

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
    """SynthDef.new("s", { arg freqL = 120, freqR = 125; Out.ar(0, SinOsc.ar([freqL, freqR], 0, 0.2))}).play()"""
    """
    53436766
    00000001
    0001
      0173
      0002
        00000000
        3e4ccccd
      0002
        42f00000
        42fa0000
      0002
        05667265714c 0000
        056672657152 0001
      0006
        07436f6e74726f6c Control
          01 0000 0002 0000
          01 01
        0653696e4f7363 SinOsc
          02 0002 0001 0000
          0000 0000 ffff 0000
          02
        0c42696e6172794f705547656e BinaryOpUGen
          02 0002 0001 0002
          0001 0000 ffff 0001
          02
        0653696e4f7363 SinOsc
          02 0002 0001 0000
          0000 0001 ffff 0000
          02
        0c42696e6172794f705547656e
          02 0002 0001 0002
          0003 0000 ffff 0001
          02
        034f7574
          02 0003 0000 0000
          ffff 0000 0002 0000 0004 0000
      0000
    """
    sd = SynthDef("s", [('freqL', 1200), ('freqR', 1205)])
    c = sd.controls
    sd.addUgen(Out.ar(0, SinOsc.ar(Line.kr(100, mc(c['freqL'], c['freqR'])), 0) * 0.2))
    return sd

def m3():
    hostname = 'walk'

    s = OSC.OSCServer((hostname, 14641))
    s.addMsgHandler('default', s.msgPrinter_handler)

    m = OSC.OSCMessage("/status")
    c = s.client
    c.sendto(m, (hostname, 57110))

    def send(msgOrBundle):
        c.sendto(msgOrBundle, (hostname, 57110))

    m = msg("/d_recv")
    m.append(compileDefs([m2()]), 'b')
    n = Node("s")
    m.append(n.s_new().getBinary(), 'b')
    send(m)
    send(timedBundle(time.time() + 3.0, n.n_free()))
    s.serve_forever()

if __name__ == '__main__':
    m3()
