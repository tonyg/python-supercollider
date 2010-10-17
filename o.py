import supercollider
import supercollider.osc as osc
from supercollider import SynthDef, mc
from supercollider.ugen import *
from supercollider.oscutil import *

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

    s = osc.OSCServer((hostname, 14641))
    s.addMsgHandler('default', s.msgPrinter_handler)

    m = osc.OSCMessage("/status")
    c = s.client
    c.sendto(m, (hostname, 57110))

    def send(msgOrBundle):
        print 'sending', msgOrBundle
        c.sendto(msgOrBundle, (hostname, 57110))

    m = msg("/d_recv")
    m.append(supercollider.compileDefs([m2()]), 'b')
    n = supercollider.node.Node("s")
    m.append(n.s_new().getBinary(), 'b')
    send(m)
    send(delayedBundle(2.0, n.set("freqL", 400).n_set()))
    send(delayedBundle(3.0, n.n_free()))
    s.serve_forever()

def m4():
    hostname = 'walk'

    s = osc.OSCServer((hostname, 14641))
    s.addMsgHandler('default', s.msgPrinter_handler)
    import threading
    st = threading.Thread(target = s.serve_forever)
    st.start()

    m = osc.OSCMessage("/status")
    cl = s.client
    cl.sendto(m, (hostname, 57110))

    def send(msgOrBundle):
        print 'sending', msgOrBundle
        cl.sendto(msgOrBundle, (hostname, 57110))

    sd = SynthDef("s", [('freqL', 1200), ('freqR', 1205)])
    c = sd.controls
    sd.addUgen(Out.ar(0, SinOsc.ar(mc(c['freqL'], c['freqR'])) * 0.2))

    m = msg("/d_recv")
    m.append(supercollider.compileDefs([sd]), 'b')
    n = supercollider.node.Node("s")
    m.append(delayedBundle(0.01, n.s_new()).getBinary(), 'b')
    send(m)
    send(delayedBundle(1.0, n.set("freqL", 400).n_set()))
    send(delayedBundle(2.0, n.set("freqL", 550).n_set()))
    send(delayedBundle(3.0, n.n_free()))

if __name__ == '__main__':
    m4()
    time.sleep(5)
    import sys
    sys.exit(0)
