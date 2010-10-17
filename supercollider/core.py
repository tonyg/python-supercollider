import supercollider.osc as osc
import time
import struct

class CalcRate:
    RATE_SCALAR = 0
    RATE_CONTROL = 1
    RATE_AUDIO = 2

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

class UGenBase(object):
    special_index = 0

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
            spec = UGenSpec(cls.classname(), calcrate, special_index)
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

def compute_rate(a, b):
    if a.calcrate == CalcRate.RATE_AUDIO: return CalcRate.RATE_AUDIO
    if b.calcrate == CalcRate.RATE_AUDIO: return CalcRate.RATE_AUDIO
    if a.calcrate == CalcRate.RATE_CONTROL: return CalcRate.RATE_CONTROL
    if b.calcrate == CalcRate.RATE_CONTROL: return CalcRate.RATE_CONTROL
    return CalcRate.RATE_SCALAR

class OutputProxy(object):
    def __init__(self, spec, index):
        self.spec = spec
        self.index = index

    def realSpec(self):
        return self.spec

    def outputNumber(self):
        return self.index
