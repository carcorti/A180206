# A180206: exact enumeration through n=26

Carlo Corti · carlo.corti@outlook.com · release date 19 November 2026.

Software release: **v1.0**.
[GitHub release and source archive](https://github.com/carcorti/A180206/releases/tag/v1.0)
· [Repository](https://github.com/carcorti/A180206).
`10.5281/zenodo.xxxxxxxx` is the author's required provisional DOI, not an
assigned identifier. Keep it until the author supplies the official locator.

## Definition and results

`a(n)` counts ordered permutations `p` of `0,...,n-1` for which nonnegative
integers `x[0],...,x[n+1]` satisfy `p[i] = x[i]+x[i+1]+x[i+2]`.
The offset is 1. Reversed permutations count separately when distinct.
The zero window fixes three zero entries and determines a unique realization.
The producer counts weighted tails on complementary sets of actual labels.
The checker uses repeated-label words and inclusion-exclusion, in two modular
channels; Python reconstructs the exact integer by CRT.

The canonical file `data/b180206.txt` contains exactly 26 rows of `n a(n)`,
unsigned decimal integers separated by one space, followed by one empty final
record (exactly two final LF bytes). Hardin's historical terms are 1..16,
ending in `612195224`. Carlo Corti's computation supplies 17..26, with
`a(25)=160065864659464904` and `a(26)=1688253382074096582`. The first
uncomputed index is 27. Maxima 24 and 26 designate complete prefix jobs;
the second job includes index 25. Software capacity 28 is not a computed result.

## Files and evidence roles

| Path | Role |
|---|---|
| `paper/A180206_v3.tex` | Exact current reviewed manuscript; monolithic, inline bibliography, no external figures or scientific inputs |
| `src/a180206.c`, `src/Makefile` | Exact reviewed and executed producer source and original build recipe |
| `check/ie.cpp`, `check/crt.py` | Exact modular recount and independent reconstruction arithmetic |
| `data/b180206.txt` | Canonical contiguous counts, byte-identical to the workspace master |
| `check/test.py` | Original bounded regression: definition, tail coefficients, workers, restart, corruption, resource failure |
| `check/qualify.py`, `check/remediate.py`, `check/closure.py` | Original compiler/instrumentation and resource/recovery qualification drivers |
| `check/kernel.c`, `check/numeric.py` | Original synthetic integer-width fixture and exact Python transcript checker |
| `check/fault.c`, `check/output.c`, `check/tsan.c`, `check/iekernel.cpp` | Required fault, output, race-control and bounded hot-path fixtures |
| `check/brute.c`, `check/freedp.c`, `check/indep.py`, `check/ftable.py`, `check/census.c` | Exact reviewer-supplied definition, free-start and coefficient programs, with compact public names |
| `check/manuscript.py` | Original manuscript examples/tables checker; sole edit routes the TeX input from v1 to current v3 |
| `check/replay.py` | Original retained-result comparison body, adapted to indexed archive inputs instead of embedded Base64 |
| `check/package.py` | New packaging driver; verifies inventory, original evidence and bounded reproduction |
| `proof/run.tgz`, `proof/map.json` | Lossless original records, original native images as identity data, and complete per-file hash/size/mode/original-path/role map |
| `checks.sha256` | Exact public file inventory and SHA-256 checksums, excluding only itself |
| `CITATION.cff`, `LICENSE` | Citation metadata and the pre-existing MIT license, retained unchanged |

The map identifies renamed review sources and the exact manuscript-checker
path adaptation. The numerical production code, compiler flags, Makefile and
TeX bytes are unchanged. Exact shared public inputs are not duplicated inside
the archive. Archive members use short ordinary paths; original historical
paths are recreated only in scratch storage. The source programs and manuscript
retain their meaningful names. Private review conversations, transport copies,
obsolete manuscript drafts, development worktrees and third-party papers are
excluded. References and external reading locators are in the manuscript.

No additional OEIS a-file is supplied: exact terms are already contiguous in
the b-file; native evidence and width witnesses have appropriate documented
formats here. There are no proved sparse later indexed terms. Duplicating these
records as an a-file would add no separate verification function.

## Bounded public validation

Run from this package's root; no write access to the package is needed:

```sh
python3 -I -B check/package.py
```

Requires Python 3.11 or newer with its standard library. The recorded campaign
used Python 3.12.3. The command verifies exact inventory and archive members,
restores private temporary inputs, reconstructs the original 24- and 26-term
prefixes from committed residues, compares the producer outputs and canonical
rows, checks journal digest chains, reruns the 768-row synthetic arithmetic
checker, checks manuscript examples/tables and validates 23 original executions
of the review programs against their exact source hashes. It does not execute
an archived native image, allocate the discarded DP tables, or enumerate new
terms. Expected final line:

```text
PUBLIC PACKAGE PASS: 30 files; contiguous 1..26; retained evidence only; no new campaign
```

Changed, missing and unexpected payload files cause a nonzero exit. Only a
root `.git/` directory is ignored as clone metadata. Do not use Python `-O`:
original fixtures contain assertions, and the public driver refuses it.
Hashes provide integrity and internal identity binding, not independent
external authentication of execution history.

For a fresh build and small known-data regression, use:

```sh
python3 -I -B check/package.py --build
```

This builds both canonical native programs in disposable storage using the
unchanged Makefile, runs the original regression through 16, and compiles/runs
the two review sources and the guarded terminal-sum variant on small known
cases. It neither overwrites the historical binaries nor attributes new builds
to old runs. It leaves the package untouched.

Fresh native checks require Linux with `/proc/meminfo`, GCC/G++ 13.3.0
(`gcc-13`, `g++-13`), GNU Make, `sha256sum`, OpenSSL/libcrypto development
headers and libraries, and OpenMP/libgomp. The producer deliberately requires
its array estimate plus 8.5 GiB of available memory even on small jobs.
The original campaign ran on AMD Ryzen 9 7940HS, Linux Mint 22.3,
kernel `6.17.0-42-generic`, requesting eight workers. The exact C17/C++17
optimization flags are in `src/Makefile`; `-march=native` means rebuilt
machine code depends on the build host. Original tool and library identities
are retained in the archive. Native schema interpretation is little-endian.

## TeX build

The source uses standard TeX Live packages: fontenc (T1), English babel,
lmodern, amsmath, amssymb, amsthm, booktabs, microtype, geometry and hyperref.
No BibTeX, `.bib`, external images or private workspace paths are required.
To check compilation and references without generating a PDF:

```sh
python3 -I -B check/package.py --tex
```

Three pdfLaTeX draft-mode passes run in disposable storage. No PDF is included
or generated by package preparation. Standard pdfLaTeX can later typeset the
same monolithic source when requested.

## Inspecting or restoring the retained records

The compressed evidence payload is 272008 bytes; its 71 file contents expand
to 2307735 bytes, excluding tar headers and the shared visible files. Every
member's identity, role and original mode are in `proof/map.json`.
To list evidence or inspect one original text record:

```sh
python3 -I -B check/replay.py --list
python3 -I -B check/replay.py --show runs/n26/valid.json
```

To restore and verify in a new directory outside this package:

```sh
python3 -I -B check/replay.py --restore /tmp/a206-proof
```

The destination must not already exist. All input identities are checked before
the destination is created; existing directories are never overwritten.
Native images are restored without execute permission and are used solely as
data for historical source/build/image identity. To remove an inspected scratch
tree, delete only the exact destination you created. The public archive contains
neither the four discarded producer intermediates nor a means of restoring them.

After restoration, the historical weighted Python diagnostic can run against
its original sixteen-term input in the disposable restored tree:

```sh
cp /tmp/a206-proof/runs/n24/prod/base.txt /tmp/a206-proof/data/b180206.txt
python3 -B /tmp/a206-proof/outputs/strategy/probe.py
```

This changes only scratch data to the retained historical baseline and replaces
the scratch diagnostic report. It does not change public canonical data.

## Further checks and precise limits

The review free-start C checker was originally executed separately for every
`n=1..21`; its terminal-sum guarded variant was also executed at 21. The exact
one-line recipe replaces `t+=row[s];` with
`if(__builtin_add_overflow(t,row[s],&t)) return 3;`. The public driver regenerates
this variant and checks its original recorded hash. Review builds used
`gcc-13 -std=c17 -O2`; the endpoint requests 3875536896 bytes and is not
repeated by default. `check/brute.c` was executed through 11; its argument is
the inclusive maximum, whereas `check/freedp.c` accepts one index. These are
minimal research fixtures: use only the documented positive ranges.

`check/indep.py` reproduces the original Python free-start check through 16
and exhaustive starting-pair/permutation checks through 9. It accepts the
b-file path as its sole argument and requires NumPy (2.4.4 available at package
preparation). `check/census.c` reproduces the separate criterion census through
11. Original local outputs are retained. `check/ftable.py FFILE 15` compares all
32768 coefficients with an independent arbitrary-precision recurrence. Its
original small producer fixture was disposable; the execution record is retained
in `outputs/rev01/adjacent.json`. Repeating this comparison requires a *fresh*
known-prefix producer run with maximum 16 and its new `prod/f.bin`, not either
discarded large campaign table. The retained weighted Python diagnostic and the
bounded regression also supply runnable coefficient checks.

Original release/instrumentation observations are historical evidence:
`outputs/rev01/test.json` records 101 release invocations;
`outputs/rev01/qual/qualfail.json` contains completed Clang and ASan/UBSan
matrices followed by a failed Valgrind attempt; its outer `FAIL` is preserved.
The separate passing compatible Valgrind record is `outputs/dev/qualvg.json`.
The TSan/Archer controls and 97-invocation matrix are in
`outputs/rev01/tsan/qual.json`. The resource/recovery supplements and their
original outputs are retained too. ASan leak detection was disabled for OpenMP;
TSan excluded noninstrumented modules and the file-size-limit cases. Static
analysis records include diagnostics and nonzero Cppcheck status, not a claim
of universal warning-free code. Some synthetic and Valgrind evidence was
inherited from unchanged mechanisms of the predecessor; the exact predecessor
source and region identities are retained. Host inventory candidate hashes
identify that earlier development state, not a different official result.

Re-executing qualification requires the additional exact tool families recorded
in the host inventory: Clang 17.0.6, Clang/LLVM 18.1.3, Archer/libomp 18,
Valgrind 3.22.0 and Cppcheck 2.13.0. The original drivers and fixture sources
are supplied; the default public check audits their retained evidence rather
than rerunning these environment-sensitive matrices or large synthetic
allocations. Historical receipts also mention private review/runbook documents;
those workflow links are historical and are not dependencies of public checks.

The main enumerations share the zero-split theorem and local transition. CRT
is exact reconstruction, not a third independent census. The later forward
count removes the zero-split dependency through 21; the numerical comparison
for 22..26 remains between the original producer and alphabet recount.
The original producer's full on-disk audit cannot be repeated: its two full
subset-total files and two final-layer files were deliberately discarded
without an archive (671092112 bytes). Their prior native-audit receipts remain;
current journal checks verify digest chains and terminal counts, not the
missing F/W contents. Newly recomputed states would be new evidence.

The release retains the reviewed provisional manuscript `A180206_v3.tex`,
including its contemporary pre-publication availability statement. The
`status` field in `proof/map.json` records the initial package assembly;
the current software release is v1.0, identified above. The DOI remains an
intentional placeholder. An actual Zenodo deposit and its distributed bytes
require separate verification; synchronization alone is not that verification.
DOI replacement, final manuscript/PDF preparation and OEIS submission are
separate actions. See `CITATION.cff` and `LICENSE`. Reviewer-provided source
attribution is preserved in the source comments and manuscript AI-use disclosure.
