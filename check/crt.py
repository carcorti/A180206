#!/usr/bin/env python3
"""Exact A180206 residue reconstruction. Project owner: Carlo Corti.

Consumes complete IE output with matching committed state and code identity.
The matching IE `check` is a separate read-only integrity audit. This script
checks declared coverage; it does not prove the IE algorithm or authenticate
against malicious self-consistent rewriting. No producer answer is an input.
"""
import argparse
import hashlib
import math
from pathlib import Path
import struct

P, Q = 2**61-1, 2**61-3


def reconstruct(a, b, n):
    if not (1 <= n <= 28 and 0 <= a < P and 0 <= b < Q):
        raise ValueError('residue/index outside proven domain')
    x = a + P * (((b-a) * pow(P, -1, Q)) % Q)
    if x > math.factorial(n):
        raise ValueError('CRT result exceeds n!')
    return x


def read(path):
    raw = path.read_bytes()
    if not raw.endswith(b'\n') or b'\r' in raw:
        raise ValueError('noncanonical framing')
    rows = []
    for line in raw[:-1].split(b'\n'):
        fields = line.split(b' ')
        if len(fields) != 3 or any(not f or (len(f)>1 and f[0]==48)
                                  or any(c < 48 or c > 57 for c in f) for f in fields):
            raise ValueError('expected three unsigned decimals separated by one space')
        rows.append(tuple(map(int, fields)))
    if [r[0] for r in rows] != list(range(1, len(rows)+1)) or not 1 <= len(rows) <= 28:
        raise ValueError('indices must be contiguous 1..maximum<=28')
    return rows


def complete_state(path, rows, executable):
    """Authenticate declared native coverage/identity, not IE mathematics."""
    raw = path.with_name('ctl.bin').read_bytes()
    if len(raw) != 672 or raw[:8] != b'A206IE\0\0' or hashlib.sha256(raw[:-32]).digest() != raw[-32:]:
        raise ValueError('invalid IE control')
    n, cursor, additions = struct.unpack_from('<QQQ', raw, 8)
    if n != len(rows) or cursor != 1 << (n-1):
        raise ValueError('incomplete or mismatched IE coverage')
    m = n-1
    expected = sum((cursor//(2 << b)*(1 << b) + max(0, cursor % (2 << b)-(1 << b)))
                   * 2*m*((b+2)*(b+3)//2) for b in range(m))
    if additions != expected:
        raise ValueError('IE cursor/work mismatch')
    for i, (_, a, b) in enumerate(rows):
        if struct.unpack_from('<QQ', raw, 32+16*i) != (a, b):
            raise ValueError('residue text differs from committed state')
    inputs = (executable.with_name('ie.cpp'), executable.parent/'../src/Makefile', executable)
    canonical = bytearray(672)
    canonical[:8] = b'A206IE\0\0'
    struct.pack_into('<QQQ', canonical, 8, n, cursor, additions)
    for i, (_, a, b) in enumerate(rows):
        struct.pack_into('<QQ', canonical, 32+16*i, a, b)
    for i, item in enumerate(inputs):
        with item.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').digest()
        if digest != raw[528+32*i:560+32*i]:
            raise ValueError('IE source/build/executable identity changed')
        canonical[528+32*i:560+32*i] = digest
    canonical[-32:] = hashlib.sha256(canonical[:-32]).digest()
    if canonical != raw:
        raise ValueError('noncanonical IE state')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('residues', nargs='?', type=Path)
    ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--ie', type=Path, default=Path(__file__).with_name('ie'))
    args = ap.parse_args()
    if args.selftest:
        if args.residues:
            ap.error('selftest takes no input')
        for x in (0, 1, P-1, P, Q, Q-1, math.factorial(28)):
            if reconstruct(x % P, x % Q, 28) != x:
                raise AssertionError('CRT reconstruction selftest mismatch')
        try:
            reconstruct(P, 0, 28)
        except ValueError:
            pass
        else:
            raise AssertionError('out-of-range accepted')
        print('CRT SELFTEST PASS')
    else:
        if not args.residues:
            ap.error('residue file required')
        rows = read(args.residues)
        complete_state(args.residues, rows, args.ie)
        for n, a, b in rows:
            print(n, reconstruct(a, b, n))


if __name__ == '__main__':
    main()
