import supercollider.osc as osc
import time

def msg(address, *args):
    m = osc.OSCMessage(address)
    for a in args:
        m.append(a)
    return m

def bundle(*msgs):
    b = osc.OSCBundle()
    for m in msgs:
        b.append(m)
    return b

def timedBundle(timeTag, *msgs):
    b = bundle(*msgs)
    b.setTimeTag(timeTag)
    return b

def delayedBundle(delta, *msgs):
    return timedBundle(time.time() + delta, *msgs)
