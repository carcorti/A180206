#!/usr/bin/env python3
"""Sofia independent cross-check for A180206. Uses only the definition
p_i = x_i + x_{i+1} + x_{i+2}, x_j >= 0. No zero anchor, no split, no colex,
no mod-3 packing, no IE. Two methods:
 (A) brute force over permutations and over all (x0,x1), counting realizations;
 (B) left-to-right transfer over (used set, x_{i+1}, x_{i+2}) from every free
     start (x0,x1); counts realizations (=permutations iff realization unique,
     which (A) checks for n<=9 and which follows from the zero label forcing
     x_k=x_{k+1}=x_{k+2}=0)."""
import itertools, sys, numpy as np

def brute(n):
    perms = mult_bad = 0
    for p in itertools.permutations(range(n)):
        real = 0
        for x0 in range(p[0]+1):
            for x1 in range(p[0]-x0+1):
                a, b, ok = x0, x1, True
                for v in p:
                    c = v - a - b
                    if c < 0: ok = False; break
                    a, b = b, c
                real += ok
        if real: perms += 1
        if real > 1: mult_bad += 1
    return perms, mult_bad

def transfer(n):
    if n == 0: return 1
    K = n  # x values lie in 0..n-1
    pairs = [(a, b) for a in range(K) for b in range(K - a)]
    pid = {q: i for i, q in enumerate(pairs)}
    P = len(pairs)
    st = np.zeros((1 << n, P), dtype=object if n > 18 else np.int64)
    for i in range(P): st[0, i] = 1          # every free start (x0,x1)
    maps = []
    for v in range(n):
        src = [pid[(a, b)] for (a, b) in pairs if a + b <= v]
        dst = [pid[(b, v - a - b)] for (a, b) in pairs if a + b <= v]
        maps.append((np.array(src), np.array(dst)))
    masks_by_pc = [[] for _ in range(n + 1)]
    for m in range(1 << n): masks_by_pc[bin(m).count('1')].append(m)
    for k in range(n):
        ms = np.array(masks_by_pc[k])
        for v in range(n):
            sel = ms[((ms >> v) & 1) == 0]
            if len(sel) == 0: continue
            src, dst = maps[v]
            st[(sel | (1 << v))[:, None], dst[None, :]] += st[sel][:, src]
    return int(st[(1 << n) - 1].sum())

if __name__ == '__main__':
    ref = {int(a): int(b) for a, b in (l.split() for l in open(sys.argv[1]) if l.strip())}
    for n in range(1, 10):
        perms, bad = brute(n)
        assert perms == ref[n] and bad == 0, (n, perms, bad)
        print(f'BRUTE n={n} a={perms} multi_realization_perms={bad}')
    for n in range(1, 17):
        t = transfer(n)
        assert t == ref[n], (n, t, ref[n])
        print(f'TRANSFER n={n} a={t} MATCH')
