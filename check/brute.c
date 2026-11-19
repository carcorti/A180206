/* Independent definition check: for every permutation, enumerate ALL starting
   pairs (x0,x1) (free start), propagate, count realizations. Also evaluate the
   paper's Proposition (difference/minimum criterion) and compare. */
#include <stdio.h>
#include <stdlib.h>
static int n,p[16],used[16];static long long feas,multi,critbad;
static void test(void){
    int nreal=0;
    for(int x0=0;x0<=p[0];x0++)for(int x1=0;x0+x1<=p[0];x1++){
        int x[20];x[0]=x0;x[1]=x1;int ok=1;
        for(int i=0;i<n;i++){x[i+2]=p[i]-x[i]-x[i+1];if(x[i+2]<0){ok=0;break;}}
        nreal+=ok;
    }
    long m[3]={0,0,0},s[3]={0,0,0};
    for(int i=0;i<n-1;i++){int r=i%3;s[r]+=p[i+1]-p[i];if(-s[r]>m[r])m[r]=-s[r];}
    int crit=(m[0]+m[1]+m[2]<=p[0]);
    if(crit!=(nreal>0))critbad++;
    if(nreal)feas++; if(nreal>1)multi++;
}
static void rec(int k){if(k==n){test();return;}for(int v=0;v<n;v++)if(!used[v]){used[v]=1;p[k]=v;rec(k+1);used[v]=0;}}
int main(int c,char**v){int N=atoi(v[1]);for(n=1;n<=N;n++){feas=multi=critbad=0;rec(0);printf("%d %lld multi=%lld criterion_mismatch=%lld\n",n,feas,multi,critbad);fflush(stdout);}}
