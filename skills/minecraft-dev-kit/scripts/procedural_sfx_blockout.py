#!/usr/bin/env python3
"""Create deterministic prototype SFX for timing/blockout (not final premium audio)."""
from __future__ import annotations
import argparse,math,random,shutil,struct,subprocess,wave
from pathlib import Path

def env(t,d,attack=.02,release=.25):
    a=min(1,t/max(.001,attack)); r=min(1,max(0,d-t)/max(.001,release)); return max(0,min(a,r))
def synth(kind,d,sr,seed):
    rng=random.Random(seed); out=[]; phase=0.0
    for i in range(int(d*sr)):
        t=i/sr; e=env(t,d,.01 if kind=='impact' else .04,.20 if kind=='impact' else .35); n=rng.uniform(-1,1)
        if kind=='impact': val=(math.sin(2*math.pi*(85-35*t/d)*t)*.65+n*.35)*e
        elif kind=='whoosh': val=(n*.7+math.sin(2*math.pi*(180+120*t/d)*t)*.3)*e*math.sin(math.pi*t/d)
        elif kind=='rumble': val=(math.sin(2*math.pi*55*t)*.55+math.sin(2*math.pi*83*t)*.25+n*.20)*e
        elif kind=='chime': val=(math.sin(2*math.pi*660*t)+.5*math.sin(2*math.pi*990*t)+.25*math.sin(2*math.pi*1320*t))/1.75*e
        elif kind=='growl': val=(math.sin(2*math.pi*(95+12*math.sin(2*math.pi*5*t))*t)*.65+n*.2)*e
        else: val=n*e
        out.append(max(-1,min(1,val*.75)))
    return out

def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument('--kind',choices=['impact','whoosh','rumble','chime','growl','noise'],required=True);ap.add_argument('--duration',type=float,default=.8);ap.add_argument('--seed',type=int,default=1);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--ogg',action='store_true');a=ap.parse_args();sr=44100
    if not (0.05<=a.duration<=15):raise SystemExit('duration must be 0.05..15s')
    wav=a.output if a.output.suffix.lower()=='.wav' else a.output.with_suffix('.wav'); wav.parent.mkdir(parents=True,exist_ok=True); samples=synth(a.kind,a.duration,sr,a.seed)
    with wave.open(str(wav),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(sr);w.writeframes(b''.join(struct.pack('<h',int(x*32767)) for x in samples))
    final=wav
    if a.ogg:
        ff=shutil.which('ffmpeg')
        if not ff:print('ffmpeg unavailable; kept WAV prototype')
        else:
            ogg=a.output if a.output.suffix.lower()=='.ogg' else a.output.with_suffix('.ogg');p=subprocess.run([ff,'-y','-loglevel','error','-i',str(wav),'-c:a','libvorbis','-q:a','5',str(ogg)],timeout=30)
            if p.returncode==0:final=ogg
    print(final);return 0
if __name__=='__main__':raise SystemExit(main())
