/* Independent free-start transfer DP: state (used set of labels 0..n-1, last two
   entries). Start from every (x0,x1) with x0+x1<=n-1. No zero split, no residue
   packing, no colex. Counts (permutation, realization) pairs; uniqueness of the
   realization makes this a(n). uint64 with overflow traps. */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
int main(int c,char**v){
  int n=atoi(v[1]);int np=0,id[32][32];int pa[600],pb[600];
  for(int a=0;a<n;a++)for(int b=0;a+b<n;b++){id[a][b]=np;pa[np]=a;pb[np]=b;np++;}
  size_t S=(size_t)1<<n;uint64_t *W=calloc(S*(size_t)np,8);if(!W){perror("calloc");return 1;}
  for(int s=0;s<np;s++)W[s]=1;
  for(size_t m=0;m<S;m++){uint64_t *row=W+m*np;
    for(int s=0;s<np;s++){uint64_t w=row[s];if(!w)continue;int a=pa[s],b=pb[s];
      for(int l=a+b;l<n;l++){if(m>>l&1)continue;int cc=l-a-b;
        uint64_t *d=W+(m|((size_t)1<<l))*np+id[b][cc];
        if(__builtin_add_overflow(*d,w,d)){fprintf(stderr,"overflow\n");return 2;}}}}
  uint64_t t=0;uint64_t *row=W+(S-1)*np;for(int s=0;s<np;s++)t+=row[s];
  printf("%d %llu\n",n,(unsigned long long)t);return 0;}
