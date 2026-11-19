#!/usr/bin/env python3
"""Deterministic resource/recovery and synthetic-output qualification, n<=16 only."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import signal
import struct
import subprocess
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--baseline',action='store_true')
    ap.add_argument('--san',action='store_true',help='Same resource cases on a disposable ASan/UBSan build')
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    rows=[];begin=time.monotonic();native=ROOT/'src/a180206'
    def invoke(cmd,rc=0,extra=None):
        env=os.environ.copy();env.update(extra or {})
        r=subprocess.run(list(map(str,cmd)),env=env,capture_output=True,text=True,stdin=subprocess.DEVNULL,timeout=45)
        rows.append({'argv':list(map(str,cmd)),'env':extra,'rc':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
        assert r.returncode==rc,rows[-1]
        return r
    def hashes(p):return {x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in p.iterdir() if x.is_file()}
    try:
        with tempfile.TemporaryDirectory(prefix='a206-rem-') as tmp:
            t=Path(tmp);shim=t/'fault.so';out=t/'output'
            invoke(['gcc-13','-std=c17','-O2','-Wall','-Wextra','-Werror','-shared','-fPIC',ROOT/'check/fault.c','-ldl','-o',shim])
            bind=[f'-DA180206_SOURCE_SHA256="{hashlib.sha256((ROOT/"src/a180206.c").read_bytes()).hexdigest()}"',f'-DA180206_MAKE_SHA256="{hashlib.sha256((ROOT/"src/Makefile").read_bytes()).hexdigest()}"']
            if a.san:
                clone=t/'clone';(clone/'src').mkdir(parents=True);(clone/'data').mkdir()
                for name in ['src/a180206.c','src/Makefile','data/b180206.txt']:shutil.copyfile(ROOT/name,clone/name)
                native=clone/'src/a180206'
                invoke(['gcc-13','-std=c17','-O1','-g','-fno-omit-frame-pointer','-fopenmp','-fsanitize=address,undefined',*bind,clone/'src/a180206.c','-lcrypto','-o',native])
            binary_hash=hashlib.sha256(native.read_bytes()).hexdigest()
            invoke(['gcc-13','-std=c17','-O2','-fopenmp',*bind,ROOT/'check/output.c','-lcrypto','-o',out])
            base={'LD_PRELOAD':str(shim)}
            if a.san:
                lib=invoke(['gcc-13','-print-file-name=libasan.so']).stdout.strip()
                base.update(LD_PRELOAD=lib+':'+str(shim),ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')
            def env(**kw):return dict(base,**kw)
            def command(p,n=16,resume=False,q=None):
                c=[native,'run','--root',p,'--max',n,'--threads',1]
                if resume:c+=['--resume']
                if q:c+=['--quantum',q]
                return c
            def check(p,rc=0,n=16):return invoke([native,'check','--root',p,'--max',n],rc,base if a.san else None)
            reference=''.join((ROOT/'data/b180206.txt').read_text().splitlines(True)[:16])
            disk=5260448+2*2**30
            for name,kwargs,msg in [('ram',{'A206_LOW_RAM':'1'},'MemAvailable'),('disk',{'A206_FREE':str(disk-1)},'free disk'),('quota',{},'quantum too small')]:
                p=t/name;r=invoke(command(p,n=24 if name=='quota' else 16,q=1 if name=='quota' else None),1,env(**kwargs));assert msg in r.stderr
                assert p.exists()==a.baseline,(name,'refusal left a root')
            for stage in ['initial','dp','conv']:
                p=t/stage;invoke(command(p,q=8),2,env(A206_STOP=stage));check(p)
                raw=(p/'ctl.bin').read_bytes()
                if stage=='initial':assert struct.unpack_from('<7Q',raw,8)==(1,0,1,0,1,0,0)
                if stage=='conv':assert struct.unpack_from('<Q',raw,16)[0]==1 and struct.unpack_from('<Q',raw,40)[0]==10
                assert not (p/'cnt.tsv').exists()
                # Only blocks in files credited by the producer; retain 2 GiB headroom.
                held=sum(min(x.stat().st_blocks*512,x.stat().st_size) for x in p.iterdir() if x.name=='f.bin' or x.name.startswith('lay'))
                before=hashes(p)
                r=invoke(command(p,resume=True),1,env(A206_FREE='0'));assert 'free disk' in r.stderr and hashes(p)==before
                if not a.baseline:
                    r=invoke(command(p,resume=True),1,env(A206_FREE=str(disk-held-1)))
                    assert 'free disk' in r.stderr and hashes(p)==before
                r=invoke(command(p,resume=True),1,env(A206_LOW_RAM='1'));assert 'MemAvailable' in r.stderr and hashes(p)==before
                invoke(command(p,resume=True),1 if a.baseline else 0,env(A206_FREE=str(disk-held)))
                if a.baseline:assert hashes(p)==before;invoke(command(p,resume=True),extra=base if a.san else None)
                assert (p/'cnt.tsv').read_text()==reference;check(p)
            p=t/'terminal';invoke(command(p),-signal.SIGKILL,env(A206_STOP='terminal'))
            assert struct.unpack_from('<Q',(p/'ctl.bin').read_bytes(),16)[0]==2
            before=hashes(p);check(p,1);assert hashes(p)==before
            invoke(command(p,resume=True),1 if a.baseline else 0,env(A206_LOW_RAM='1',A206_FREE='0'))
            if a.baseline:assert hashes(p)==before;invoke(command(p,resume=True),extra=base if a.san else None)
            expected=hashes(p)
            for missing in [(),('end.json',),('cnt.tsv',),('cnt.tsv','end.json')]:
                d=t/('done'+str(len(rows)));shutil.copytree(p,d)
                for name in missing:(d/name).unlink()
                invoke(command(d,resume=True),1 if a.baseline else 0,env(A206_LOW_RAM='1',A206_FREE='0'))
                if not a.baseline:assert hashes(d)==expected;check(d)
            # Rehashed corrupt state must still fail before any terminal repair.
            d=t/'bad';shutil.copytree(p,d);raw=bytearray((d/'ctl.bin').read_bytes());struct.pack_into('<Q',raw,24,99);raw[-32:]=hashlib.sha256(raw[:-32]).digest();(d/'ctl.bin').write_bytes(raw)
            before=hashes(d);invoke(command(d,resume=True),1,env(A206_LOW_RAM='1',A206_FREE='0'));assert hashes(d)==before
            # Semantic coverage forgery: remove all final-index partial quanta,
            # repair the unkeyed chain, retain the short-quantum completion.
            p=t/'coverage';invoke(command(p,n=8,q=8),extra=base if a.san else None)
            raw=(p/'evt.bin').read_bytes();chain=[];prev=bytes(32)
            for k in range(0,len(raw),1024):
                r=bytearray(raw[k:k+1024]);n=struct.unpack_from('<Q',r,40)[0];cursor=struct.unpack_from('<Q',r,48)[0]
                if n==8 and cursor>0:continue
                struct.pack_into('<Q',r,8,len(chain)+1);r[592:624]=prev;r[-32:]=hashlib.sha256(r[:-32]).digest();prev=r[-32:];chain.append(r)
            (p/'evt.bin').write_bytes(b''.join(chain));(p/'ctl.bin').write_bytes(chain[-1]);before=hashes(p)
            check(p,0 if a.baseline else 1,n=8);assert hashes(p)==before
            # Full 128-bit positive output, independent expected bytes and receipt.
            p=t/'synthetic';p.mkdir();invoke([out,p,'write'])
            text=''.join(f'{n} {math.factorial(n)}\n' for n in range(1,29)).encode()
            assert (p/'cnt.tsv').read_bytes()==text
            receipt=json.loads((p/'end.json').read_text());assert receipt['count_sha256']==hashlib.sha256(text).hexdigest()
            before=hashes(p);invoke([out,p,'write']);invoke([out,p,'check']);assert hashes(p)==before
            (p/'cnt.tsv').write_bytes(b'X'+text[1:]);before=hashes(p);invoke([out,p,'write'],1);assert hashes(p)==before
            for args in [['run','--root',t/'badcli','--max',8,'--seconds',3001],['run','--root',t/'badcli','--max',8,'--quantum',65537],['check','--root',t/'missing','--max',8],['run','--root',t/'missing','--max',8,'--resume']]:invoke([native,*args],1,base if a.san else None)
            assert not (t/'badcli').exists() and not (t/'missing').exists()
        status='BASELINE_DEFECTS_REPRODUCED' if a.baseline else 'PASS'
    except BaseException:
        (a.out/'failure.json').write_text(json.dumps({'status':'FAIL','events':rows},indent=2)+'\n');raise
    (a.out/'test.json').write_text(json.dumps({'status':status,'seconds':time.monotonic()-begin,'source_sha256':hashlib.sha256((ROOT/'src/a180206.c').read_bytes()).hexdigest(),'binary_sha256':binary_hash,'scope':'known indices<=16; synthetic factorial output is not sequence data','events':rows},indent=2)+'\n')
    print(status,len(rows),'invocations')


if __name__=='__main__':main()
