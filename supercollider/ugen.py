import supercollider.core
from supercollider.core import ArgSpec, UGenBase

class SinOsc(UGenBase):
    argspecs = [ArgSpec('freq'),
                ArgSpec('phase', 0)]

class Line(UGenBase):
    argspecs = [ArgSpec('start', 0),
                ArgSpec('end', 1),
                ArgSpec('dur', 1),
                ArgSpec('doneAction', 0)]

class XLine(Line): pass

class _OutSpec(supercollider.core.UGenSpec):
    def outputs(self):
        return []

class Out(UGenBase):
    @classmethod
    def construct(cls, calcrate, special_index, bus, channels):
        spec = _OutSpec(cls.classname(), calcrate, special_index)
        ArgSpec('bus').configure(spec, bus)
        for channel in channels:
            ArgSpec('source').configure(spec, channel)
        return spec
