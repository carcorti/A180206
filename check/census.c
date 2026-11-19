/* A180206 reviewer oracle: definition-level census.
 * Counts permutations p of 0..n-1 admitting nonnegative integers x_0..x_{n+1}
 * with p_i = x_i + x_{i+1} + x_{i+2}. Derived directly from the definition:
 * d_i = p_{i+1}-p_i forces x_{i+3} = x_i + d_i, so each residue class of
 * indices mod 3 forms a chain; feasibility is a per-chain lower bound and
 * x_0+x_1+x_2 = p_0. The chain predicate is itself validated against a naive
 * bounded enumeration of all x vectors for n <= 5 (see Python driver).
 * Reviewer: GLM (Z.ai). No candidate code involved.
 */
#include <stdio.h>
#include <string.h>

static int n;
static int p[16], used[16];
static long long count;

static void rec(int i) {
    if (i == n) {
        /* chain feasibility from the definition */
        long long need = 0;
        for (int r = 0; r < 3; r++) {
            long long s = 0, minima = 0;   /* S_0 = 0 included */
            for (int j = r; j + 1 < n; j += 3) { s += p[j + 1] - p[j]; if (s < minima) minima = s; }
            need += -minima;
        }
        if (need <= p[0]) count++;
        return;
    }
    for (int v = 0; v < n; v++)
        if (!used[v]) { used[v] = 1; p[i] = v; rec(i + 1); used[v] = 0; }
}

int main(int argc, char **argv) {
    for (n = 1; n <= 11; n++) {
        count = 0;
        memset(used, 0, sizeof used);
        rec(0);
        printf("%d %lld\n", n, count);
    }
    return 0;
}
