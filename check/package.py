#!/usr/bin/env python3
"""Bounded A180206 public-package checks. Owner: Carlo Corti.

Default: exact inventory, retained records/CRT, manuscript examples/tables,
synthetic arithmetic and original review outputs. Optional fresh builds use
private scratch storage and known indices only. Never executes archived ELF.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import struct
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]

def require(ok, message):
    if not ok:
        raise ValueError(message)

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT/'check'/f'{name}.py')
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

def inventory():
    expected = {}
    for line in (ROOT/'checks.sha256').read_text().splitlines():
        require(re.fullmatch(r'[0-9a-f]{64}  [A-Za-z0-9_./-]+', line), 'Malformed manifest')
        checksum, name = line.split('  ')
        p = PurePosixPath(name)
        require(not p.is_absolute() and '..' not in p.parts and str(p) == name, 'Unsafe manifest path')
        require(name != 'checks.sha256' and name not in expected, 'Duplicate manifest entry')
        expected[name] = checksum
    expected_dirs = {parent.as_posix() for name in expected
                     for parent in PurePosixPath(name).parents
                     if parent != PurePosixPath('.')}
    found = set()
    found_dirs = set()
    for directory, dirs, files in os.walk(ROOT, followlinks=False):
        base = Path(directory)
        for name in dirs + files:
            require(not (base/name).is_symlink(), 'Symlink in payload: '+str(base/name))
        if base == ROOT and '.git' in dirs:
            dirs.remove('.git')  # Only root clone metadata is outside the payload.
        for name in dirs:
            relative = (base/name).relative_to(ROOT).as_posix()
            require(relative in expected_dirs, 'Unexpected payload directory: '+relative)
            found_dirs.add(relative)
        for name in files:
            path = base/name
            require(path.is_file(), 'Special payload entry')
            found.add(path.relative_to(ROOT).as_posix())
    require(found == set(expected) | {'checks.sha256'}, 'Missing/unexpected payload files')
    require(found_dirs == expected_dirs, 'Missing/unexpected payload directories')
    for name, checksum in expected.items():
        require(digest((ROOT/name).read_bytes()) == checksum, 'Changed payload: '+name)
    return len(found)

def run(argv, cwd=None):
    result = subprocess.run(list(map(str, argv)), cwd=cwd, stdin=subprocess.DEVNULL,
                            capture_output=True, text=True, timeout=180)
    require(result.returncode == 0, 'Command failed: '+str(argv)+'\n'+result.stdout+result.stderr)
    return result.stdout

def journal(root, n):
    stage = root/f'runs/n{n}/prod'
    ctl = (stage/'ctl.bin').read_bytes()
    raw = (stage/'evt.bin').read_bytes()
    require(len(ctl) == 1024 and len(raw) == struct.unpack_from('<Q', ctl, 8)[0]*1024,
            'Journal/control length')
    previous = bytes(32)
    for i in range(len(raw)//1024):
        rec = raw[1024*i:1024*(i+1)]
        require(rec[:8] == b'A180206\0' and struct.unpack_from('<Q', rec, 8)[0] == i+1,
                'Journal sequence')
        require(rec[-32:] == hashlib.sha256(rec[:-32]).digest() and rec[592:624] == previous,
                'Journal digest chain')
        require(rec[560:592] == hashlib.sha256((stage/'cfg.json').read_bytes()).digest(),
                'Journal configuration binding')
        previous = rec[-32:]
    require(raw[-1024:] == ctl and struct.unpack_from('<Q', ctl, 16)[0] == 2,
            'Journal terminal control')
    counts = [tuple(map(int, line.split())) for line in (stage/'cnt.tsv').read_text().splitlines()]
    require(all(int.from_bytes(ctl[80+16*(k-1):96+16*(k-1)], 'little') == v for k,v in counts),
            'Journal terminal counts')
    # Intentionally not a native F/W byte audit: those four files were discarded.

def review(root, expected):
    record = json.loads((root/'proof/review.json').read_bytes())
    plain = (ROOT/'check/freedp.c').read_bytes()
    old = b't+=row[s];'
    require(plain.count(old) == 1, 'Endpoint guard recipe')
    guarded = plain.replace(old, b'if(__builtin_add_overflow(t,row[s],&t)) return 3;')
    hashes = {'brute': digest((ROOT/'check/brute.c').read_bytes()),
              'freedp': digest(plain), 'checked': digest(guarded)}
    seen = set()
    for event in record['events']:
        program, n = event['program'], event['argument']
        require(program in hashes and event['source_sha256'] == hashes[program] and event['rc'] == 0,
                'Original reviewer execution identity/status')
        rows = event['stdout'].splitlines()
        wanted = ([f'{k} {expected[k]} multi=0 criterion_mismatch=0' for k in range(1,n+1)]
                  if program == 'brute' else [f'{n} {expected[n]}'])
        require(rows == wanted, 'Original reviewer output')
        seen.add((program,n))
    require(seen == {('brute',11), ('checked',21)} | {('freedp',n) for n in range(1,22)},
            'Original reviewer execution scope')
    return guarded

def builds(root, guarded):
    with tempfile.TemporaryDirectory(prefix='a206-build-') as directory:
        work = Path(directory)
        for name in ('src','check','data'):
            shutil.copytree(ROOT/name, work/name)
        run(['make','-C',work/'src','all','ie'])
        matrix = json.loads(run([sys.executable,'-B',work/'check/test.py','--max','16']))
        require(matrix['status'] == 'PASS' and matrix['maximum_known_index'] == 16, 'Fresh regression')
        # Rebuild exact review sources, but repeat only small already-known cases.
        expected = dict(tuple(map(int,line.split())) for line in (ROOT/'data/b180206.txt').read_text().splitlines() if line)
        for name, limit in [('brute',11),('freedp',16),('guard',16)]:
            source = work/'check'/f'{name}.c'
            if name == 'guard':
                source.write_bytes(guarded)
            exe = work/name
            run(['gcc-13','-std=c17','-O2',source,'-o',exe])
            actual = run([exe,str(limit)]).splitlines()
            target = ([f'{k} {expected[k]} multi=0 criterion_mismatch=0' for k in range(1,limit+1)]
                      if name == 'brute' else [f'{limit} {expected[limit]}'])
            require(actual == target, 'Fresh review-program check')
        print('PASS fresh canonical build, known-prefix regression 1..16 and review programs')

def tex():
    with tempfile.TemporaryDirectory(prefix='a206-tex-') as directory:
        work = Path(directory)
        source = work/'A180206.tex'
        source.write_bytes((ROOT/'paper/A180206.tex').read_bytes())
        for _ in range(3):
            run(['pdflatex','-draftmode','-interaction=nonstopmode','-halt-on-error',source.name], cwd=work)
        log = source.with_suffix('.log').read_text()
        require(not re.search(r'(?:LaTeX|Package [^\n]+) Warning:|(?:Overfull|Underfull) \\[hv]box', log),
                'TeX reference/layout warnings')
        require(not source.with_suffix('.pdf').exists(), 'Unexpected PDF')
        print('PASS monolithic TeX draft-mode compilation; no PDF created')

def main():
    require(not sys.flags.optimize, 'Python optimization disables original fixture assertions')
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--build', action='store_true', help='Fresh scratch builds and known-prefix checks through 16')
    ap.add_argument('--tex', action='store_true', help='Three draft-mode TeX passes in scratch; no PDF')
    args = ap.parse_args()
    count = inventory()
    replay = module('replay')
    replay.FILES = replay.inputs()
    with tempfile.TemporaryDirectory(prefix='a206-evidence-') as directory:
        work = Path(directory)
        replay.replay(work)
        frozen = json.loads((work/'runbooks/frozen.json').read_bytes())
        for name in ('src/a180206.c','src/Makefile','src/a180206','check/ie.cpp','check/ie','check/crt.py'):
            require(digest((work/name).read_bytes()) == frozen['artifacts'][name], 'Frozen identity: '+name)
        for n in (24,26):
            journal(work,n)
        raw = (ROOT/'data/b180206.txt').read_bytes()
        require(b'\r' not in raw and raw.endswith(b'\n\n') and not raw.endswith(b'\n\n\n'), 'B-file framing')
        expected = dict(tuple(map(int,line.split())) for line in raw.splitlines() if line)
        require(list(expected) == list(range(1,27)), 'Canonical indices')
        paper = module('manuscript')
        paper.ROOT = work
        paper.verify_examples(expected)
        paper.check_tables((ROOT/'paper/A180206.tex').read_text(), expected)
        require(run([sys.executable,'-I','-B',ROOT/'check/numeric.py',work/'outputs/dev/numeric.txt']).strip(),
                'Synthetic numeric replay')
        guarded = review(work,expected)
        print('PASS journal chains, synthetic 768-row arithmetic, manuscript examples/tables and 23 review records')
        if args.build:
            builds(work,guarded)
    if args.tex:
        tex()
    require(inventory() == count, 'Payload changed during checks')
    print(f'PUBLIC PACKAGE PASS: {count} files; contiguous 1..26; retained evidence only; no new campaign')

if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, AssertionError, subprocess.SubprocessError) as error:
        print('PACKAGE STOP: '+str(error), file=sys.stderr)
        raise SystemExit(1)
