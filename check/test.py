#!/usr/bin/env python3
"""Bounded candidate checks: known data only, disposable state, no official run."""
import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path
import resource
import shutil
import signal
import struct
import subprocess
import tempfile
import time

import crt

ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / 'src/a180206'
IE = ROOT / 'check/ie'
EVENTS = []


def run(args, status=0):
    t = time.monotonic()
    r = subprocess.run(list(map(str, args)), capture_output=True, text=True,
                       stdin=subprocess.DEVNULL, timeout=120)
    EVENTS.append({'argv': list(map(str, args)), 'returncode': r.returncode,
                   'seconds': time.monotonic()-t, 'stdout': r.stdout, 'stderr': r.stderr})
    assert r.returncode == status, EVENTS[-1]
    return r


def expected(n):
    rows = [tuple(map(int, x.split())) for x in (ROOT/'data/b180206.txt').read_text().splitlines() if x]
    assert [x[0] for x in rows] == list(range(1, len(rows)+1))
    assert len(rows) >= 16
    return ''.join(f'{i} {a}\n' for i,a in rows[:n])


def command(exe, path, n, threads=2, quantum=None, resume=False):
    c = [exe, 'run', '--root', path, '--max', n, '--threads', threads]
    if quantum is not None:
        c += ['--quantum', quantum]
    if resume:
        c += ['--resume']
    return list(map(str,c))


def audit(exe, path, n):
    run([exe,'check','--root',path,'--max',n])


def hashes(path):
    return {x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in path.iterdir() if x.is_file()}


def interrupt(exe, path, n, graceful):
    c = command(exe,path,n,2,1)
    with tempfile.TemporaryFile() as err:
        proc = subprocess.Popen(c, stdout=subprocess.DEVNULL, stderr=err, stdin=subprocess.DEVNULL)
        deadline = time.monotonic()+30
        observed = None
        while proc.poll() is None and time.monotonic()<deadline:
            f=path/'ctl.bin'
            if f.exists():
                raw=f.read_bytes()
                if len(raw) in (672,1024) and hashlib.sha256(raw[:-32]).digest()==raw[-32:]:
                    frontier=struct.unpack_from('<Q',raw,8 if exe==NATIVE else 16)[0]
                    if frontier>=3:
                        observed=raw
                        proc.send_signal(signal.SIGTERM if graceful else signal.SIGKILL)
                        break
            time.sleep(.001)
        if observed is None:
            proc.kill();proc.wait();raise AssertionError('interruption frontier not observed')
        rc=proc.wait(timeout=30);err.seek(0)
        EVENTS.append({'argv':c,'interrupted': 'SIGTERM' if graceful else 'SIGKILL',
                       'returncode':rc,'observed_frontier':frontier,'stderr':err.read().decode()})
        assert rc==(2 if graceful else -signal.SIGKILL)
    assert not (path/'cnt.tsv').exists()
    audit(exe,path,n)
    old=(path/'ctl.bin').read_bytes()
    run(command(exe,path,n,8,resume=True))
    audit(exe,path,n)
    return old


def direct_member(p):
    total=[0]*3;low=[0]*3
    for i in range(len(p)-1):
        r=i%3;total[r]+=p[i+1]-p[i];low[r]=min(low[r],total[r])
    return -sum(low)<=p[0]


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--max',type=int,choices=(8,16),default=16)
    ap.add_argument('--skip-fsize',action='store_true',help='Instrumentation-only: resource failure checked on release separately')
    options=ap.parse_args();n=options.max
    begin=time.monotonic()
    with tempfile.TemporaryDirectory(prefix='a206-check-') as tmp:
        t=Path(tmp)
        for exe in (NATIVE,IE):
            run([exe,'selftest'])
            for args in [[],['invalid'],['selftest','--max','8'],
                         ['run','--root',str(t/'bad'),'--max','0'],
                         ['run','--root',str(t/'bad'),'--max','29'],
                         ['run','--root',str(t/'bad'),'--max','-1'],
                         ['run','--root',str(t/'bad'),'--max','+8'],
                         ['run','--root',str(t/'bad'),'--max',' 8'],
                         ['run','--root',str(t/'bad'),'--max','8','--max','8'],
                         ['run','--root',str(t/'bad'),'--max','8','--threads','0'],
                         ['run','--root',str(t/'bad'),'--max','8','--threads','17'],
                         ['run','--root',str(t/'bad'),'--max','8','--seconds','0'],
                         ['run','--root',str(t/'bad'),'--max','8','--quantum','0'],
                         ['run','--root',str(t/'bad'),'--max','8','--unknown','1'],
                         ['run','--root',str(t/'bad'),'--max'],
                         ['check','--root',str(t/'bad'),'--max','8','--resume'],
                         ['check','--root',str(t/'bad'),'--max','8','--threads','2']]:
                run([exe]+args,1)
            assert not (t/'bad').exists()
        run([ROOT/'check/crt.py','--selftest']) if (ROOT/'check/crt.py').stat().st_mode & 0o111 else run(['python3','-B',ROOT/'check/crt.py','--selftest'])
        for k in [1,2,3,8]:
            p=t/f'p{k}';i=t/f'i{k}'
            run(command(NATIVE,p,k));audit(NATIVE,p,k)
            assert (p/'cnt.tsv').read_text()==expected(k)
            run(command(IE,i,k));audit(IE,i,k)
            got=run(['python3','-B',ROOT/'check/crt.py',i/'cnt.tsv']).stdout
            assert got==expected(k)
        # All small coefficients from the full candidate F table.
        f=(t/'p8/f.bin').read_bytes()
        for mask in range(128):
            labels=[v+1 for v in range(7) if mask>>v&1];h=len(labels)
            idx=sum(math.comb(7,j) for j in range(h))+sum(math.comb(v-1,j+1) for j,v in enumerate(labels))
            count=0
            for word in itertools.permutations(labels):
                a=b=0
                for v in word:
                    a,b=b,v-a-b
                    if b<0:break
                else:count+=1
            assert int.from_bytes(f[16*idx:16*idx+16],'little')==count
        for k in range(1,9):
            count=sum(direct_member(w) for w in itertools.permutations(range(k)))
            assert expected(k).splitlines()[-1]==f'{k} {count}'
        for th in [1,8]:
            p=t/f'full{th}'
            run(command(NATIVE,p,n,th));audit(NATIVE,p,n)
            assert (p/'cnt.tsv').read_text()==expected(n)
        i=t/'iefull';run(command(IE,i,n,8));audit(IE,i,n)
        assert run(['python3','-B',ROOT/'check/crt.py',i/'cnt.tsv']).stdout==expected(n)
        for exe,label in [(NATIVE,'prod'),(IE,'ie')]:
            for graceful in (False,True):
                p=t/f'{label}{graceful}';old=interrupt(exe,p,n,graceful)
                data=(p/'cnt.tsv').read_text()
                if exe==NATIVE:assert data==expected(n)
                else:assert run(['python3','-B',ROOT/'check/crt.py',p/'cnt.tsv']).stdout==expected(n)
                before=hashes(p);run(command(exe,p,n),1);assert hashes(p)==before
                # A stale partial control cannot erase a completed receipt.
                (p/'ctl.bin').write_bytes(old);before=hashes(p)
                run(command(exe,p,n,resume=True),1);assert hashes(p)==before
        # Corruption checks are read-only and reject both hashes and semantics.
        for name in ['ctl.bin','f.bin','lay1.bin']:
            src=t/'full1';dest=t/f'corrupt-{name}';shutil.copytree(src,dest)
            if not (dest/name).exists():
                name=next(x.name for x in dest.glob('lay*.bin'))
            raw=bytearray((dest/name).read_bytes());raw[0]^=1;(dest/name).write_bytes(raw)
            before=hashes(dest);run([NATIVE,'check','--root',dest,'--max',n],1);assert hashes(dest)==before
        dest=t/'semantic';shutil.copytree(t/'iefull',dest)
        raw=bytearray((dest/'ctl.bin').read_bytes());struct.pack_into('<Q',raw,24,0);raw[-32:]=hashlib.sha256(raw[:-32]).digest();(dest/'ctl.bin').write_bytes(raw)
        before=hashes(dest);run([IE,'check','--root',dest,'--max',n],1);assert hashes(dest)==before
        for bad in ['1 1 1\n1 1 1\n','2 1 1\n','1 1 1\r\n','1 1\n','1 01 1\n']:
            b=t/'bad.tsv';b.write_text(bad)
            try:crt.read(b)
            except ValueError:pass
            else:raise AssertionError('CRT malformed rows accepted')
        # Source/build identity and historical-prefix evolution in an isolated tree.
        clone=t/'clone';(clone/'src').mkdir(parents=True);(clone/'data').mkdir()
        for name in ['a180206','a180206.c','Makefile']:
            shutil.copyfile(ROOT/'src'/name,clone/'src'/name)
        (clone/'src/a180206').chmod(0o700)
        shutil.copyfile(ROOT/'data/b180206.txt',clone/'data/b180206.txt')
        for name in ['a180206.c','Makefile']:
            q=clone/'src'/name;raw=q.read_bytes();q.write_bytes(raw+b'\n')
            result=run(command(clone/'src/a180206',clone/name,8),1)
            assert 'compiled source/Makefile mismatch' in result.stderr
            q.write_bytes(raw)
        # A future longer b-file does not silently change the frozen16-term input.
        q=clone/'data/b180206.txt';q.write_bytes(q.read_bytes().rstrip(b'\n')+b'\n17 999999999\n\n')
        run(command(clone/'src/a180206',clone/'evolve',8))
        assert (clone/'evolve/cnt.tsv').read_text()==expected(8)
        if not options.skip_fsize:
            # Resource failure during append leaves a usable committed prefix.
            def file_limit():
                signal.signal(signal.SIGXFSZ,signal.SIG_IGN)
                resource.setrlimit(resource.RLIMIT_FSIZE,(16384,16384))
            failpath=t/'fsize';c=command(NATIVE,failpath,16,2,8)
            fail=subprocess.run(c,capture_output=True,text=True,stdin=subprocess.DEVNULL,
                                preexec_fn=file_limit,timeout=30)
            EVENTS.append({'argv':c,'fixture':'RLIMIT_FSIZE=16384, SIGXFSZ ignored',
                           'returncode':fail.returncode,'stderr':fail.stderr})
            assert fail.returncode==1 and 'File too large' in fail.stderr,(fail.returncode,fail.stderr)
            audit(NATIVE,failpath,16)
            run(command(NATIVE,failpath,16,8,resume=True));audit(NATIVE,failpath,16)
            assert (failpath/'cnt.tsv').read_text()==expected(16)
    print(json.dumps({'status':'PASS','maximum_known_index':n,
                      'seconds':time.monotonic()-begin,'events':EVENTS},indent=2))


if __name__=='__main__':
    main()
