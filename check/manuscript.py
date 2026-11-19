"""Read-only checks of the examples, term table and measured cost table in the manuscript."""
from itertools import permutations
from pathlib import Path
from math import comb, factorial, prod
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[1]


def read_json(path):
    return json.loads(path.read_bytes())


def rows(path):
    return {int(n): int(a) for n, a in (line.split() for line in
            path.read_text().splitlines() if line.strip())}


def tail(word, width=3):
    state = (0,) * (width - 1)
    for v in word:
        entry = v - sum(state)
        if entry < 0:
            return None
        state = (*state[1:], entry)
    return state


def member(p, width):
    step = [0] * width
    minimum = step.copy()
    for i in range(len(p) - 1):
        r = i % width
        step[r] += p[i+1] - p[i]
        minimum[r] = min(minimum[r], step[r])
    return -sum(minimum) <= p[0]


def verify_examples(expected):
    for n in range(1, 9):
        assert sum(member(p, 3) for p in permutations(range(n))) == expected[n]
    for word, pair in [((2,4,5,3),(1,0)), ((3,4,5,2),(1,0)),
                       ((1,2,4,3,5),(0,3)), ((1,2,3,5,4),(3,0))]:
        assert tail(word) == pair
    assert tail((1,2,4,3,5,7,6)) is None
    assert tail((1,2,3,5,4,7,6)) == (4,2)
    for alphabet, count in [((1,2,3),1), ((1,2,4),1), ((1,2,3,4),2), ((1,2,3,5),1)]:
        assert sum(tail(w) is not None for w in permutations(alphabet)) == count
    assert [sum(member(p, w) for p in permutations(range(5))) for w in (2,3,4)] == [44,18,16]
    for p, allowed in [((0,1,2,4,3,6,5),[False,True,False]),
                       ((1,0,2,3,5,6,4),[True,False,True])]:
        assert [member(p,w) for w in (2,3,4)] == allowed
        i = p.index(0)
        for w, feasible in zip((2,3,4), allowed):
            assert all(tail(word,w) is not None for word in (p[:i][::-1],p[i+1:])) == feasible
    assert tuple(sum((2*a+b)%3 == r for a in range(26) for b in range(26-a))
                 for r in range(3)) == (117,117,117)
    cell_bytes = lambda h: 8 if h <= 20 else 16
    assert 16*2**25 + 117*max(sum(comb(25,j)*cell_bytes(j) for j in (h,h+1))
                              for h in range(25)) == 10271832512
    assert factorial(20) < 2**64 < factorial(21)
    assert factorial(28) < 2**98 < prod((2**61-1, 2**61-3))


def check_tables(tex, expected):
    term_text = tex.split(r'\label{tab:terms}',1)[1].split(r'\end{tabular}',1)[0]
    term_pairs = {}
    for a,b,c,d in re.findall(r'(?m)^(\d+)\s*&\s*(\d+)\s*&\s*(\d+)\s*&\s*(\d+)\\',term_text):
        term_pairs[int(a)] = int(b)
        term_pairs[int(c)] = int(d)
    assert term_pairs == {n: expected[n] for n in range(17,27)}
    cost = tex.split(r'\label{tab:cost}',1)[1].split(r'\end{tabular}',1)[0]
    walls = []
    for n in (24,26):
        run = ROOT/'runs'/f'n{n}'
        reference = {i: expected[i] for i in range(1,n+1)}
        assert rows(run/'prod/cnt.tsv') == reference == rows(run/'ops/v001/crt.tsv')
        checks = read_json(run/'valid.json')
        assert checks['rows'] == n and all(c['returncode']==0 for c in checks['checks'])
        assert checks['crt_returncode'] == 0 and read_json(run/'consol.json')['last_index']==n
        receipts = {}
        for op in ('p001','i001','v001','c001'):
            path = run/'ops'/op
            receipt = read_json(path/'done.json')
            assert hashlib.sha256((path/'call.json').read_bytes()).hexdigest() == receipt['call_sha256']
            receipts[op] = receipt
        p,ie = receipts['p001'],receipts['i001']
        wall = sum(r['wall_seconds'] for r in receipts.values())
        walls.append(wall)
        cpu = sum(r[k] for r in (p,ie) for k in ('child_user_seconds','child_system_seconds'))
        fields = (n,round(p['wall_seconds']),round(ie['wall_seconds']),round(wall),round(cpu),
                  p['peak_child_rss_kib'],ie['peak_child_rss_kib'])
        assert ('&'.join(map(str,fields))+r'\\') in cost
        m = n-1
        assert ie['after']['cursor'] == 2**m
        assert ie['after']['additions'] == 2*m*2**(m-1)*sum(comb(v+2,2) for v in range(1,m+1))
    assert round(sum(walls)) == 344


if __name__ == '__main__':
    expected = rows(ROOT/'data/b180206.txt')
    assert list(expected) == list(range(1,27))
    verify_examples(expected)
    check_tables((ROOT/'paper/A180206.tex').read_text(), expected)
    print('PASS: direct membership 1..8, tail/width witnesses, arithmetic, both tables, receipt and work totals')
