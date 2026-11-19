#!/usr/bin/env python3
"""Independent exact check of the synthetic production-kernel row transcript."""
import json
import math
from pathlib import Path
import sys

pairs={z:[(a,b) for a in range(28) for b in range(28-a) if (2*a+b)%3==z]
       for z in range(3)}
ids={z:{x:i for i,x in enumerate(pairs[z])} for z in range(3)}
seen=set()
widen=False
for line in Path(sys.argv[1]).read_text().splitlines():
    f=line.split()
    if f[0]=='WIDEN':
        assert list(map(int,f[1:]))==[math.factorial(20),math.factorial(21)]
        assert math.factorial(20)<2**64<math.factorial(21)
        widen=True
        continue
    assert f[0]=='ROW'
    h,rank,mask=map(int,f[1:4]);got=list(map(int,f[4:]));assert h in [20,21,22]
    labels=[v for v in range(1,28) if mask>>(v-1)&1]
    assert len(labels)==h and rank==sum(math.comb(v-1,j+1) for j,v in enumerate(labels))
    assert (h,rank) not in seen;seen.add((h,rank))
    res=sum(labels)%3;expected=[0]*136
    for v in labels:
        pred=[x for x in labels if x!=v]
        pr=sum(math.comb(x-1,j+1) for j,x in enumerate(pred));rp=sum(pred)%3;slot=pr%136
        if slot>=len(pairs[rp]):continue
        a,b=pairs[rp][slot];c=v-a-b
        if c>=0:expected[ids[res][(b,c)]]+=math.factorial(h-1)
    assert got==expected,(h,rank)
assert len(seen)==768 and widen
print(json.dumps({'status':'PASS','distinct_rows':len(seen),
                  'layers':[20,21,22],'forced_64_to_128_overflow_case':True}))
