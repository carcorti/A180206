/* Internal qualification fixture; includes the exact production functions.
 * It computes synthetic rows, never a new A180206 term. */
#define main a206_program_main
#include "../src/a180206.c"
#undef main
#include <sys/resource.h>

static void synthetic(unsigned h) {
    init(28);
    uint64_t rows_prev=C[M][h-1],lo=C[M][h]/2,hi=lo+256;
    if(hi>C[M][h])hi=C[M][h];
    void *prev=allocate(rows_prev*w,width(h-1));
    void *cur=allocate(C[M][h]*w,width(h));
    U *F=allocate(UINT64_C(1)<<M,16);
    /* Every predecessor row has total (h-1)!: a valid numeric upper bound.
     * Populate one slot by a deterministic pattern, not a valid tail census. */
    memset(prev,0,(size_t)(rows_prev*w*width(h-1)));
    for(uint64_t r=0;r<rows_prev;r++)setcell(prev,r*w+(r%w),width(h-1),fact[h-1]);
    double a0=now();threads=1;uint64_t work1=rows(cur,prev,F,h,lo,hi);
    uint64_t bytes=(hi-lo)*w*width(h);unsigned char *copy=malloc((size_t)bytes);
    need(copy!=NULL,"fixture copy");memcpy(copy,(unsigned char *)cur+lo*w*width(h),(size_t)bytes);
    threads=8;uint64_t work8=rows(cur,prev,F,h,lo,hi);
    need(work1==work8 && !memcmp(copy,(unsigned char *)cur+lo*w*width(h),(size_t)bytes),"synthetic thread invariance");
    /* Separate Python checker reconstructs the synthetic rows and weights. */
    for(uint64_t rank=lo;rank<hi;rank++) {
        printf("ROW %u %"PRIu64" %u",h,rank,unrank(rank,h));
        for(unsigned j=0;j<w;j++){char value[40];dec(cell(cur,rank*w+j,width(h)),value);printf(" %s",value);}
        putchar('\n');
    }
    fprintf(stderr,"SYNTHETIC h=%u rows=%"PRIu64" work=%"PRIu64" seconds=%.9f\n",h,hi-lo,work1,now()-a0);
    free(copy);free(F);free(cur);free(prev);
}

static void memory(void) {
    init(28);uint64_t best=0;unsigned at=0;
    for(unsigned h=1;h<=M;h++){uint64_t b=w*(C[M][h-1]*width(h-1)+C[M][h]*width(h));if(b>best){best=b;at=h;}}
    uint64_t sizes[3]={16*(UINT64_C(1)<<M),w*C[M][at-1]*width(at-1),w*C[M][at]*width(at)};
    void *p[3];
    for(unsigned i=0;i<3;i++){p[i]=allocate(sizes[i],1);memset(p[i],(int)i+1,(size_t)sizes[i]);}
    for(unsigned i=0;i<3;i++){volatile unsigned char *q=p[i];for(uint64_t j=0;j<sizes[i];j+=4096)need(q[j]==i+1,"resident memory readback");}
    struct rusage ru;need(!getrusage(RUSAGE_SELF,&ru),"rusage");
    printf("MEMORY layer=%u bytes=%"PRIu64" rss_bytes=%"PRIu64"\n",at,arrays(),(uint64_t)ru.ru_maxrss*1024);
    for(unsigned i=0;i<3;i++)free(p[i]);
}

static void bench(void) {
    init(28);unsigned h=13;uint64_t lo=C[M][h]/2,hi=lo+65536;
    void *prev=allocate(C[M][h-1]*w,8),*cur=allocate(C[M][h]*w,8);U *F=allocate(UINT64_C(1)<<M,16);
    /* Touch all source pages to prevent a zero-page cache benchmark. */
    uint64_t cells=C[M][h-1]*w;
    for(uint64_t i=0;i<cells;i++)((uint64_t *)prev)[i]=(i%w==0);
    for(unsigned nt=1;nt<=8;nt*=8){threads=nt;double t=now();uint64_t work=rows(cur,prev,F,h,lo,hi);
        printf("BENCH threads=%u rows=%"PRIu64" reads=%"PRIu64" seconds=%.9f\n",nt,hi-lo,work,now()-t);}
    free(F);free(cur);free(prev);
}

static void widen(void) {
    init(28);uint32_t mask=(UINT32_C(1)<<21)-1;
    void *prev=allocate(21*w,8),*cur=allocate(w,16);U *F=allocate(UINT64_C(1)<<M,16);
    memset(prev,0,21*w*8);
    for(unsigned v=1;v<=21;v++){
        uint64_t pr=findex(mask^(UINT32_C(1)<<(v-1)))-off[20];need(pr<21,"widen predecessor");
        setcell(prev,pr*w+(unsigned)pair_id[v][0],8,fact[20]);
    }
    threads=8;(void)rows(cur,prev,F,21,0,1);
    need(cell(cur,0,16)==fact[21],"forced widening collision");
    char a[40],b[40];dec(fact[20],a);dec(cell(cur,0,16),b);printf("WIDEN %s %s\n",a,b);
    free(F);free(cur);free(prev);
}

int main(int argc,char **argv) {
    started=heartbeat=now();
    need(argc==2,"fixture mode");
    if(!strcmp(argv[1],"memory"))memory();
    else if(!strcmp(argv[1],"bench"))bench();
    else {
        need(!strcmp(argv[1],"numeric"),"fixture mode");
        for(unsigned h=20;h<=22;h++)synthetic(h);
        widen();
        init(28);
        /* Serialization of maximum native/64-bit values through exact public I/O. */
        FILE *tmp=tmpfile();need(tmp!=NULL,"fixture temporary file");int fd=fileno(tmp);
        uint64_t u64[3]={0,UINT64_MAX,(uint64_t)fact[20]},v64[3]={0};
        cells_io(fd,u64,0,3,true,8);cells_io(fd,v64,0,3,false,8);need(!memcmp(u64,v64,sizeof u64),"u64 I/O");
        U u128[3]={0,~(U)0,fact[28]},v128[3]={0};
        cells_io(fd,u128,0,3,true,16);cells_io(fd,v128,0,3,false,16);need(!memcmp(u128,v128,sizeof u128),"u128 I/O");
        need(!fclose(tmp),"fixture close");
    }
    return 0;
}
