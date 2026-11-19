#!/usr/bin/env python3
"""A180206 retained-record replay. Packaging adaptation of the original replay.
Original comparison body unchanged; inputs now use proof/map.json and run.tgz.
Native images are non-executable identity data. No producer state is recreated.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
def digest(data):
    return hashlib.sha256(data).hexdigest()
def require(condition, message):
    if not condition:
        raise ValueError(message)

def inputs():
    index = json.loads((ROOT/'proof/map.json').read_bytes())
    archived = {e['member']: e for e in index['entries'] if e['member']}
    require(digest((ROOT/index['archive']).read_bytes()) == index['archive_sha256'], 'Archive identity')
    data = {}
    with tarfile.open(ROOT/index['archive'], 'r:gz') as arc:
        for item in arc:
            require(item.isfile() and item.name in archived and item.name not in data, 'Unexpected/duplicate archive member')
            require(item.mode == 0o644, 'Archive mode')
            data[item.name] = arc.extractfile(item).read()
    require(set(data) == set(archived), 'Missing archive member')
    result = {}
    for e in index['entries']:
        raw = (ROOT/e['public']).read_bytes() if e['public'] else data[e['member']]
        require(len(raw) == e['bytes'] and digest(raw) == e['sha256'], 'Evidence identity: '+e['original'])
        # An exhibit fragment is restored to its short logical member name.
        name = e['member'] if '#' in e['original'] else e['original']
        path = PurePosixPath(name)
        require(not path.is_absolute() and '..' not in path.parts and '\\' not in name, 'Unsafe restore name')
        require(name not in result, 'Duplicate logical evidence')
        result[name] = raw
    return result

FILES = {}
def read_member(name):
    return FILES[name]

def replay(root):
    for name in FILES:
        dest = root / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(read_member(name))

    def record(name):
        return json.loads((root / name).read_bytes())

    def check_hashes(mapping):
        for name, expected in mapping.items():
            require(digest((root / name).read_bytes()) == expected, name)

    final = record('outputs/post26/receipt.json')
    frozen = 'runbooks/frozen.json'
    check_hashes({frozen: final['frozen_manifest_sha256'],
                  'data/b180206.txt': final['canonical_sha256']})
    check_hashes(final['receipt_hashes'])
    code = record(frozen)['artifacts']
    check_hashes({name: code[name] for name in
                  ('check/crt.py', 'check/ie', 'check/ie.cpp', 'src/Makefile')})
    canonical = (root / 'data/b180206.txt').read_bytes()
    before = (root / 'runs/n24/prod/base.txt').read_bytes()
    require(canonical.endswith(b'\n\n') and not canonical.endswith(b'\n\n\n'),
            'Canonical b-file framing')

    for n in (24, 26):
        stage = 'runs/n' + str(n)
        run = root / stage
        valid = record(stage + '/valid.json')
        consolidation = record(stage + '/consol.json')
        check_hashes(valid['evidence'])
        require(valid['status'] == 'INDEPENDENT_COMPARISON_PASS'
                and valid['rows'] == valid['maximum'] == n
                and valid['code_manifest_sha256'] == final['frozen_manifest_sha256']
                and valid['crt_returncode'] == 0
                and [x['returncode'] for x in valid['checks']] == [0, 0],
                'Validation receipt')
        for op in ('p001', 'i001', 'v001', 'c001'):
            folder = run / 'ops' / op
            done = json.loads((folder / 'done.json').read_bytes())
            require(done['call_sha256'] == digest((folder / 'call.json').read_bytes()),
                    'Call/done link ' + op)
        producer = (run / 'prod/cnt.tsv').read_bytes()
        require(record(stage + '/prod/end.json')['count_sha256'] == digest(producer),
                'Producer end receipt')
        output = subprocess.check_output([sys.executable, '-I', '-B', str(root / 'check/crt.py'),
                                          str(run / 'ie/cnt.tsv')], cwd=root)
        require(output == producer == (run / 'ops/v001/crt.tsv').read_bytes(),
                'Original native vs reconstructed output')
        after = producer + b'\n'
        require(after.startswith(before[:-1]) and
                after == b''.join(canonical.splitlines(keepends=True)[:n]) + b'\n',
                'Canonical prefix')
        require(consolidation['status'] == 'CONSOLIDATED'
                and consolidation['data_rows'] == consolidation['last_index'] == n
                and consolidation['validation_sha256'] == digest((run / 'valid.json').read_bytes())
                and valid['canonical_before_sha256'] == consolidation['before_sha256'] == digest(before)
                and consolidation['after_sha256'] == digest(after), 'Consolidation chain')
        before = after
        print(f'PASS 1..{n}: original committed residues, native output, CRT and canonical prefix')



def main():
    global FILES
    ap = argparse.ArgumentParser(description=__doc__)
    group = ap.add_mutually_exclusive_group()
    group.add_argument('--list', action='store_true')
    group.add_argument('--show')
    group.add_argument('--restore', type=Path, help='New directory only; native images remain non-executable')
    a = ap.parse_args()
    FILES = inputs()  # Validate all members before creating a restore destination.
    if a.list:
        print('\n'.join(sorted(FILES)))
    elif a.show:
        print(read_member(a.show).decode('utf-8'), end='')
    elif a.restore:
        a.restore.mkdir(exist_ok=False)
        replay(a.restore)
    else:
        with tempfile.TemporaryDirectory() as d:
            replay(Path(d))

if __name__ == '__main__':
    main()
