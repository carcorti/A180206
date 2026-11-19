#!/usr/bin/env python3
"""Finite compiler/instrumentation qualification, known indices only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
OUT=None
ROWS=[]


def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def invoke(args,env=None,expect=0,timeout=180):
    start=time.monotonic()
    result=subprocess.run(list(map(str,args)),capture_output=True,text=True,
                          stdin=subprocess.DEVNULL,env=env,timeout=timeout)
    row={'argv':list(map(str,args)),'returncode':result.returncode,
         'seconds':time.monotonic()-start,'stdout':result.stdout,'stderr':result.stderr}
    ROWS.append(row)
    assert result.returncode==expect,row
    return result


def tree(base):
    for name in ['src','check','data']:(base/name).mkdir(parents=True)
    for name in ['src/a180206.c','src/Makefile','check/ie.cpp','check/crt.py','check/test.py','data/b180206.txt']:
        shutil.copyfile(ROOT/name,base/name)


def bindings(base,ie=False):
    q=base/('check/ie.cpp' if ie else 'src/a180206.c')
    return [f'-DA180206_{"IE" if ie else "SOURCE"}_SHA256="{digest(q)}"',
            f'-DA180206_MAKE_SHA256="{digest(base/"src/Makefile")}"']


def main():
    global OUT
    ap=argparse.ArgumentParser();ap.add_argument('--flavor',choices=('all','clang','asan','tsan','valgrind'),default='all');ap.add_argument('--out',type=Path,required=True,help='New output directory, fails if it exists');options=ap.parse_args();chosen=options.flavor
    destination=options.out.resolve();destination.mkdir(parents=True,exist_ok=False);OUT=destination
    start=time.monotonic();env=os.environ.copy()
    archer=Path('/usr/lib/llvm-18/lib/libarcher.so')
    omp_include=Path(invoke(['clang-18','--print-resource-dir']).stdout.strip())/'include'
    warnings=['-Wall','-Wextra','-Wpedantic','-Wshadow','-Wconversion','-Wdouble-promotion','-Wformat=2']
    with tempfile.TemporaryDirectory(prefix='a206-qual-') as tmp:
        top=Path(tmp)
        omp_only=top/'omp';omp_only.mkdir();shutil.copyfile(omp_include/'omp.h',omp_only/'omp.h')
        for flavor in (['clang','asan','tsan'] if chosen=='all' else ([] if chosen=='valgrind' else [chosen])):
            base=top/flavor;tree(base)
            compiler='gcc-13' if flavor=='asan' else ('clang-17' if flavor=='clang' else 'clang-18')
            flags=['-O2','-fopenmp']
            if flavor=='clang':flags += ['-isystem',str(omp_only),'-L'+str(archer.parent),'-Wl,-rpath,'+str(archer.parent)]
            if flavor in ['asan','tsan']:
                flags=['-O1','-g','-fno-omit-frame-pointer','-fopenmp',
                       '-fsanitize='+('address,undefined' if flavor=='asan' else 'thread')]
            for ie in [False,True]:
                cc=compiler.replace('gcc','g++') if ie else compiler
                if ie and compiler.startswith('clang'):cc=compiler.replace('clang','clang++')
                src=base/('check/ie.cpp' if ie else 'src/a180206.c');exe=src.with_suffix('')
                r=invoke([cc,'-std='+('c++17' if ie else 'c17'),*flags,*warnings,*bindings(base,ie),src,'-lcrypto','-o',exe])
                assert not r.stderr,r.stderr
            testenv=env.copy()
            if flavor=='asan':
                testenv['ASAN_OPTIONS']='detect_leaks=0:halt_on_error=1'
                testenv['UBSAN_OPTIONS']='halt_on_error=1:print_stacktrace=1'
            if flavor=='tsan':
                testenv.update(OMP_TOOL='enabled',OMP_TOOL_LIBRARIES=str(archer),
                               TSAN_OPTIONS='ignore_noninstrumented_modules=1:halt_on_error=1:exitcode=66')
                control=ROOT/'check/tsan.c'
                startup=top/'startup.c';startup.write_text('int main(void){return 0;}\n')
                invoke(['clang-18','-O1','-fsanitize=thread',startup,'-o',top/'startup'])
                invoke([top/'startup'],env=testenv)
                for bad in [False,True]:
                    exe=top/('racy' if bad else 'safe')
                    invoke(['clang-18','-O1','-g','-fsanitize=thread','-fopenmp',*(['-DRACY'] if bad else []),control,'-o',exe])
                    r=invoke([exe],env=testenv,expect=66 if bad else 0)
                    if bad:assert 'ThreadSanitizer: data race' in r.stderr and f'{control.name}:' in r.stderr
                    else:assert not r.stderr,r.stderr
            r=invoke(['python3','-B',base/'check/test.py','--max','8',*(['--skip-fsize'] if flavor=='tsan' else [])],env=testenv)
            result=json.loads(r.stdout);assert result['status']=='PASS'
            # Embed exact tested binary/source IDs; disposable payloads are intentionally removed.
            ROWS[-1]['identities']={str(q.relative_to(base)):digest(q) for q in [base/'src/a180206.c',base/'src/Makefile',base/'src/a180206',base/'check/ie.cpp',base/'check/ie']}
            for event in result['events']:
                if event.get('interrupted')!='SIGKILL':
                    assert 'AddressSanitizer' not in event.get('stderr','') and 'runtime error:' not in event.get('stderr','') and 'ThreadSanitizer: data race' not in event.get('stderr',''),event
        # Valgrind3.22 cannot decode release AVX512; compile exact source for AVX2.
        compatible=top/'vg';tree(compatible)
        invoke(['gcc-13','-std=c17','-O2','-march=x86-64-v3','-fopenmp',*warnings,*bindings(compatible),compatible/'src/a180206.c','-lcrypto','-o',compatible/'src/a180206'])
        p=top/'valgrind'
        invoke(['valgrind','--leak-check=full','--errors-for-leak-kinds=definite','--error-exitcode=98',compatible/'src/a180206','run','--root',p,'--max','8','--threads','1'])
    summary={'status':'PASS','seconds':time.monotonic()-start,
             'archer':{'path':str(archer),'sha256':digest(archer)},
             'instrumentation_limit':'ASan leak detector disabled for OpenMP; Valgrind definite-leak/invalid-access path separately checked. Instrumented binaries and state are disposable; source/build/commands and observations retained.',
             'events':ROWS}
    (OUT/'qual.json').write_text(json.dumps(summary,indent=2)+'\n')
    print('PASS compiler, ASan/UBSan, qualified TSan/Archer, Valgrind')


if __name__=='__main__':
    try:main()
    except BaseException:
        if OUT is not None:(OUT/'qualfail.json').write_text(json.dumps({'status':'FAIL','events':ROWS},indent=2)+'\n')
        raise
