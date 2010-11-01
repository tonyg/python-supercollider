import supercollider.core
from supercollider.core import ArgSpec, UGenBase, is_mc

class SinOsc(UGenBase):
    argspecs = [ArgSpec('freq'),
                ArgSpec('phase', 0)]

class Line(UGenBase):
    argspecs = [ArgSpec('start', 0),
                ArgSpec('end', 1),
                ArgSpec('dur', 1),
                ArgSpec('doneAction', 0)]

class XLine(Line): pass

class PlayBuf(UGenBase):
    argspecs = [ArgSpec('bufnum', 0),
                ArgSpec('rate', 1),
                ArgSpec('trigger', 1),
                ArgSpec('startPos', 0),
                ArgSpec('loop', 0),
                ArgSpec('doneAction', 0)]

class BufInfoUGenBase(UGenBase):
    argspecs = [ArgSpec('bufnum', 0)]

class BufRateScale(BufInfoUGenBase): pass

class _OutSpec(supercollider.core.UGenSpec):
    def outputs(self):
        return []

class Out(UGenBase):
    @classmethod
    def construct(cls, calcrate, special_index, bus, channels):
        spec = _OutSpec(cls.classname(), calcrate, special_index)
        ArgSpec('bus').configure(spec, bus)
        if not is_mc(channels):
            channels = [channels]
            # Just the one!
        for channel in channels:
            ArgSpec('source').configure(spec, channel)
        return spec
