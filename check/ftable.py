#!/usr/bin/env python3
"""Compare every native F coefficient (f.bin) with an independent tail count;
derive colex layout and both invariants independently."""
import sys, math
from collections import defaultdict
fbin, M = sys.argv[1], int(sys.argv[2])
raw = open(fbin, 'rb').read(); assert len(raw) == 16 * (1 << M), len(raw)
# independent forward DP over subsets: W[S] = {(a,b): count}, labels = bit+1
W = [None] * (1 << M); W[0] = {(0, 0): 1}
order = sorted(range(1 << M), key=lambda m: bin(m).count('1'))
bad_res = bad_tri = 0
for S in order:
    st = W[S]
    if st is None: continue
    lab = [v + 1 for v in range(M) if S >> v & 1]
    for (a, b), c in st.items():
        if (2 * a + b - sum(lab)) % 3: bad_res += 1
        if lab and a + b > max(lab): bad_tri += 1
    for v in range(M):
        if S >> v & 1: continue
        T = S | 1 << v; d = W[T] if W[T] is not None else defaultdict(int)
        for (a, b), c in st.items():
            cc = v + 1 - a - b
            if cc >= 0: d[(b, cc)] += c
        W[T] = d
def rank(S):  # independent colex: offset by cardinality, then sum C(bit_i, i)
    bits = [v for v in range(M) if S >> v & 1]; h = len(bits)
    return sum(math.comb(M, j) for j in range(h)) + sum(math.comb(b, i + 1) for i, b in enumerate(bits))
mism = 0; seen = set()
for S in range(1 << M):
    r = rank(S); seen.add(r)
    F = sum(W[S].values()) if W[S] else 0
    if int.from_bytes(raw[16 * r:16 * r + 16], 'little') != F: mism += 1
assert len(seen) == 1 << M
lab = lambda L: sum(1 << (v - 1) for v in L)
ex = (sum(W[lab([1,2,3,4])].values()), sum(W[lab([1,2,3,5])].values()))
print(f'FTABLE M={M} subsets={1<<M} mismatches={mism} residue_violations={bad_res} triangle_violations={bad_tri} F(1234)={ex[0]} F(1235)={ex[1]}')
assert mism == 0 and bad_res == 0 and bad_tri == 0 and ex == (2, 1)
