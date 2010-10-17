import PIL.Image
import numpy
import time
import os
import sys
import colorsys

class Config: pass
config = Config()

config.shrink = (16,12)
#config.shrink = (32,24)

#config.ncolors = 2
config.ncolors = None

imgdir = '../webcam-snapshot-osx/build/dist/'
def I(f):
    return os.path.join(imgdir, f)

def HSV(c):
    (r, g, b) = c
    return colorsys.rgb_to_hsv(r/255.0, g/255.0, b/255.0)

while True:
    time.sleep(0.2)
    try:
        p = PIL.Image.open(I("webcam.png"))
    except IOError:
        continue
    sys.stdout.write('.')
    sys.stdout.flush()
    o = p
    o = o.resize(config.shrink)
    if config.ncolors is not None:
        o = o.quantize(config.ncolors)
        palette = o.getpalette()[:config.ncolors * 3]
        palette = [palette[i*3:(i+1)*3] for i in range(config.ncolors)]
        palette = [HSV(p) for p in palette]
        print [p[0] for p in palette]
    o = o.resize((320,240))
    o.save(I("frame2.bmp"))
