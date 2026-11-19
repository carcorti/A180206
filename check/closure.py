#!/usr/bin/env python3
"""Round02 finite supplements on the frozen release; known n=8 only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]


def hashes(path):
    return {x.name:('symlink',os.readlink(x)) if x.is_symlink() else
            ('file',hashlib.sha256(x.read_bytes()).hexdigest())
            for x in path.iterdir() if x.is_file() or x.is_symlink()}


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False);events=[];start=time.monotonic()
    native=ROOT/'src/a180206'
    def run(cmd,rc=0,env=None):
        r=subprocess.run(list(map(str,cmd)),env=env,capture_output=True,text=True,stdin=subprocess.DEVNULL,timeout=45)
        events.append({'argv':list(map(str,cmd)),'rc':r.returncode,'stdout':r.stdout,'stderr':r.stderr,
                       'env_delta':{k:v for k,v in (env or {}).items() if k.startswith('A206_') or k=='LD_PRELOAD'}})
        assert r.returncode==rc,events[-1];return r
    def command(path,*extra):return [native,'run','--root',path,'--max',8,'--threads',1,*extra]
    try:
        with tempfile.TemporaryDirectory(prefix='a206-close-') as tmp:
            t=Path(tmp);source=(ROOT/'check/fault.c').read_text()
            # Fixture-only variant stops inside index8, rather than at index10.
            # Cursor16 is represented by the low byte; the generated n8 history
            # guarantees all higher cursor bytes zero. No producer code changes.
            old='phase==1 && n==10';new='phase==1 && n==8 && r[48]==16'
            assert source.count(old)==1;source=source.replace(old,new)
            (t/'fault.c').write_text(source)
            run(['gcc-13','-std=c17','-O2','-Wall','-Wextra','-Werror','-shared','-fPIC',t/'fault.c','-ldl','-o',t/'fault.so'])
            env=dict(os.environ,LD_PRELOAD=str(t/'fault.so'),A206_STOP='conv')
            p=t/'partial';run(command(p,'--quantum',8),2,env)
            raw=(p/'ctl.bin').read_bytes();assert struct.unpack_from('<Q',raw,16)[0]==1
            assert struct.unpack_from('<2Q',raw,40)==(8,16)
            expected=''.join((ROOT/'data/b180206.txt').read_text().splitlines(True)[:8])
            for q in [4,65536]:
                d=t/('q'+str(q));shutil.copytree(p,d)
                run(command(d,'--resume','--quantum',q));run([native,'check','--root',d,'--max',8])
                assert (d/'cnt.tsv').read_text()==expected
            for name,msg in [('cnt.tsv','complete counts with incomplete control'),('end.json','completion receipt with incomplete control')]:
                d=t/('partial-'+name);shutil.copytree(p,d);(d/name).write_text('fixture\n');before=hashes(d)
                r=run([native,'check','--root',d,'--max',8],1);assert msg in r.stderr and hashes(d)==before
            for kind in ['hardlink','symlink']:
                d=t/kind;shutil.copytree(p,d)
                if kind=='hardlink':os.link(d/'f.bin',t/'alias')
                else:
                    assert not (d/'lay0.bin').exists();(d/'lay0.bin').symlink_to('f.bin')
                before=hashes(d);r=run(command(d,'--resume'),1)
                assert 'private principal file' in r.stderr and hashes(d)==before
            for name in ['cnt.tsv','end.json']:
                d=t/('bad-'+name);shutil.copytree(t/'q65536',d)
                b=(d/name).read_bytes();(d/name).write_bytes(b'X'+b[1:]);before=hashes(d)
                r=run(command(d,'--resume'),1);assert 'terminal artifact mismatch' in r.stderr and hashes(d)==before
            missing=t/'missing'/'job';run(command(missing),1);assert not missing.parent.exists()
            real=t/'real';real.mkdir();link=t/'link';link.symlink_to(real,target_is_directory=True)
            r=run(command(link/'job'),1);assert 'job parent' in r.stderr and not (real/'job').exists()
            run(command(real/'job'));assert (real/'job/cnt.tsv').read_text()==expected
            derived={'base_sha256':hashlib.sha256((ROOT/'check/fault.c').read_bytes()).hexdigest(),
                     'replacement':[old,new],'derived_sha256':hashlib.sha256(source.encode()).hexdigest()}
        result={'status':'PASS','seconds':time.monotonic()-start,'scope':'Known n8; no new term; no producer edit',
                'source_sha256':hashlib.sha256((ROOT/'src/a180206.c').read_bytes()).hexdigest(),
                'binary_sha256':hashlib.sha256(native.read_bytes()).hexdigest(),'fixture':derived,'events':events}
        (a.out/'test.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS',len(events),'supplemental invocations')
    except BaseException:
        (a.out/'failure.json').write_text(json.dumps({'status':'FAIL','events':events},indent=2)+'\n');raise


if __name__=='__main__':main()
