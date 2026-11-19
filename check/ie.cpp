/* Independent repeated-label inclusion-exclusion for A180206.
 * Project owner: Carlo Corti. Maintainer: Luna / OpenAI Codex.
 * No F table, colex rank, producer data or expected numerical answers used.
 * For each allowed alphabet T, count pair-state walks with repetitions, then
 * Q_m(T)=sum_k L_k(T)L_(m-k)(T). IE forces all m positive labels present
 * in m slots. The zero-split bijection is shared mathematical input.
 * Residue rings need coprimality, not primality. CRT is a separate program.
 * POSIX/Linux, OpenMP, OpenSSL3. Build via src/Makefile.
 */
#define _POSIX_C_SOURCE 200809L
#include <array>
#include <cerrno>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fcntl.h>
#include <omp.h>
#include <openssl/evp.h>
#include <signal.h>
#include <string>
#include <sys/file.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>
__extension__ typedef unsigned __int128 U;
#ifndef A180206_IE_SHA256
#error "Build through src/Makefile or supply exact source/Makefile digests"
#endif
#ifndef A180206_MAKE_SHA256
#error "Missing Makefile identity"
#endif
using A=std::array<std::array<uint64_t,2>,31>;
constexpr uint64_t mod[2]={UINT64_C(2305843009213693951),UINT64_C(2305843009213693949)};
constexpr size_t RS=672;
static volatile sig_atomic_t stopflag;
static void fail(const char *s){std::fprintf(stderr,"IE ERROR %s: %s\n",s,std::strerror(errno));std::exit(1);}
static void req(bool b,const char *s){if(!b){errno=EINVAL;fail(s);}}
static double clocknow(){timespec t{};if(clock_gettime(CLOCK_MONOTONIC,&t))fail("clock");return double(t.tv_sec)+double(t.tv_nsec)*1e-9;}
static void caught(int s){(void)s;stopflag=1;}
static uint64_t num(const char *s,uint64_t low,uint64_t high){uint64_t a=0;req(*s,"number");for(;*s;s++){req(*s>='0'&&*s<='9',"decimal grammar");uint64_t v=unsigned(*s-'0');req(v<=high&&a<=(high-v)/10,"range");a=a*10+v;}req(a>=low&&a<=high,"range");return a;}
static uint64_t plus(uint64_t a,uint64_t b,unsigned c){uint64_t z=a+b;return z>=mod[c]?z-mod[c]:z;}
static uint64_t minus(uint64_t a,uint64_t b,unsigned c){return a>=b?a-b:a+mod[c]-b;}
static uint64_t times(uint64_t a,uint64_t b,unsigned c){return uint64_t(U(a)*b%mod[c]);}
static void digest(const void *p,size_t len,unsigned char d[32]){unsigned n=0;req(EVP_Digest(p,len,d,&n,EVP_sha256(),nullptr)==1&&n==32,"SHA256");}
static void put(unsigned char *p,uint64_t x){for(unsigned i=0;i<8;i++){p[i]=static_cast<unsigned char>(x);x>>=8;}}
static uint64_t get(const unsigned char *p){uint64_t a=0;for(unsigned i=8;i;i--)a=(a<<8)|p[i-1];return a;}
static void bytes(int fd,void *p,size_t n,bool write){size_t a=0;while(a<n){ssize_t z=write ? ::write(fd,static_cast<unsigned char *>(p)+a,n-a) : ::read(fd,static_cast<unsigned char *>(p)+a,n-a);if(z<0&&errno==EINTR)continue;if(z<=0)fail("short IO");a+=size_t(z);}}
static void sync(int fd){if(fsync(fd))fail("fsync");}
static void closeit(int fd){if(close(fd))fail("close");}
static int file(int dir,const char *name,int flags){int f=openat(dir,name,flags|O_CLOEXEC|O_NOFOLLOW,0600);if(f<0)fail(name);struct stat st{};if(fstat(f,&st))fail("stat");req(S_ISREG(st.st_mode),"regular file");return f;}
static uint64_t size(int fd){struct stat st{};if(fstat(fd,&st))fail("stat");return uint64_t(st.st_size);}
static void pathhash(const std::string &p,unsigned char d[32]){int f=open(p.c_str(),O_RDONLY|O_NOFOLLOW|O_CLOEXEC);if(f<0)fail(p.c_str());EVP_MD_CTX *ctx=EVP_MD_CTX_new();req(ctx,"digest ctx");req(EVP_DigestInit_ex(ctx,EVP_sha256(),nullptr)==1,"digest init");unsigned char b[65536];ssize_t n;while((n=read(f,b,sizeof b))!=0){if(n<0){if(errno==EINTR)continue;fail("read hash");}req(EVP_DigestUpdate(ctx,b,size_t(n))==1,"digest update");}unsigned z=0;req(EVP_DigestFinal_ex(ctx,d,&z)==1&&z==32,"digest final");EVP_MD_CTX_free(ctx);closeit(f);}
static std::array<unsigned char,96> identity(){char exe[4096];ssize_t n=readlink("/proc/self/exe",exe,sizeof exe-1);req(n>0&&size_t(n)<sizeof exe-1,"exe path");exe[n]=0;std::string path(exe),parent=path.substr(0,path.find_last_of('/'));std::array<unsigned char,96> d{};pathhash(parent+"/ie.cpp",d.data());pathhash(parent+"/../src/Makefile",d.data()+32);pathhash(path,d.data()+64);
    char source_hex[65],make_hex[65];
    for(unsigned i=0;i<32;i++){std::snprintf(source_hex+2*i,3,"%02x",unsigned(d[i]));std::snprintf(make_hex+2*i,3,"%02x",unsigned(d[i+32]));}
    req(!std::strcmp(source_hex,A180206_IE_SHA256)&&!std::strcmp(make_hex,A180206_MAKE_SHA256),"compiled source/Makefile mismatch");return d;}
static void save(int dir,const unsigned char *r){int f=file(dir,"ctl.tmp",O_WRONLY|O_CREAT|O_TRUNC);bytes(f,const_cast<unsigned char *>(r),RS,true);sync(f);closeit(f);if(renameat(dir,"ctl.tmp",dir,"ctl.bin"))fail("rename");sync(dir);}
struct Edge { uint16_t src,dst; };
static Edge edge[28][406];
static unsigned edge_count[28],states;
static void geometry(unsigned M){
    unsigned id[28][28]{};states=0;
    for(unsigned a=0;a<=M;a++)for(unsigned b=0;b<=M-a;b++)id[a][b]=states++;
    for(unsigned v=1;v<=M;v++)for(unsigned a=0;a<=v;a++)for(unsigned b=0;b<=v-a;b++)
        edge[v][edge_count[v]++]={uint16_t(id[a][b]),uint16_t(id[b][v-a-b])};
}
static void alphabet(uint32_t mask,unsigned M,A &sum,uint64_t &adds){
    unsigned high=mask?32U-unsigned(__builtin_clz(mask)):0,card=unsigned(__builtin_popcount(mask));
    uint64_t L[31][2]{};L[0][0]=L[0][1]=1;
    alignas(64) uint64_t prev[406][2]{},next[406][2]{};prev[0][0]=prev[0][1]=1;
    for(unsigned h=1;h<=M;h++){
        std::memset(next,0,sizeof next);
        for(uint32_t t=mask;t;t&=t-1){unsigned v=unsigned(__builtin_ctz(t))+1;for(unsigned e=0;e<edge_count[v];e++){const Edge x=edge[v][e];for(unsigned c=0;c<2;c++)next[x.dst][c]=plus(next[x.dst][c],prev[x.src][c],c);}
            adds+=2*edge_count[v];}
        for(unsigned s=0;s<states;s++)for(unsigned c=0;c<2;c++)L[h][c]=plus(L[h][c],next[s][c],c);
        std::memcpy(prev,next,sizeof prev);
    }
    for(unsigned m=high;m<=M;m++)for(unsigned c=0;c<2;c++){uint64_t q=0;for(unsigned k=0;k<=m;k++)q=plus(q,times(L[k][c],L[m-k][c],c),c);sum[m][c]=((m-card)&1U)?minus(sum[m][c],q,c):plus(sum[m][c],q,c);}
}
static uint64_t expected_additions(uint64_t cursor,unsigned M){
    uint64_t count=0;
    for(unsigned b=0;b<M;b++){
        uint64_t half=UINT64_C(1)<<b,period=half*2;
        uint64_t ones=(cursor/period)*half,tail=cursor%period;
        if(tail>half)ones+=tail-half;
        count+=ones*2*M*((b+2)*(b+3)/2);
    }
    return count;
}
static void selftest(){for(unsigned c=0;c<2;c++){req(plus(mod[c]-1,mod[c]-1,c)==mod[c]-2,"mod add");req(times(mod[c]-1,mod[c]-1,c)==1,"mod product");req(minus(0,mod[c]-1,c)==1,"mod subtract");}unsigned char b[8];put(b,UINT64_MAX);req(get(b)==UINT64_MAX,"serialization");std::puts("IE SELFTEST PASS modular boundary arithmetic; no term computed");}
int main(int argc,char **argv){
    const double start=clocknow();
    if(argc==2&&!std::strcmp(argv[1],"selftest")){selftest();return 0;}
    req(argc>=2,"mode required");bool check=!std::strcmp(argv[1],"check"),resume=false;req(check||!std::strcmp(argv[1],"run"),"run/check");unsigned n=0,threads=8,seconds=3000,seen=0;uint64_t quantum=4096;const char *root=nullptr;
    for(int i=2;i<argc;i++){unsigned bit=0;if(!std::strcmp(argv[i],"--resume")){bit=32;req(!check,"check/resume");resume=true;}else{req(i+1<argc,"missing value");const char *k=argv[i++],*v=argv[i];if(!std::strcmp(k,"--root")){bit=1;root=v;req(*v,"empty root");}else if(!std::strcmp(k,"--max")){bit=2;n=unsigned(num(v,1,28));}else if(!std::strcmp(k,"--threads")){bit=4;req(!check,"check/threads");threads=unsigned(num(v,1,16));}else if(!std::strcmp(k,"--seconds")){bit=8;req(!check,"check/seconds");seconds=unsigned(num(v,1,3000));}else if(!std::strcmp(k,"--quantum")){bit=16;req(!check,"check/quantum");quantum=num(v,1,4096);}else fail("unknown option");}req(!(seen&bit),"duplicate option");seen|=bit;}
    req((seen&3)==3,"root/max required");unsigned M=n-1;geometry(M);uint64_t end=UINT64_C(1)<<M,cursor=0,adds=0;A sums{};auto ids=identity();bool fresh=!check&&!resume;
    if(fresh&&mkdir(root,0700))fail("new root no clobber");
    int dir=open(root,O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);if(dir<0)fail("root");if(fresh){int parent=openat(dir,"..",O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);if(parent<0)fail("job parent");sync(parent);closeit(parent);}int lock=file(dir,"lock",check?O_RDONLY:O_RDWR|O_CREAT);if(flock(lock,(check?LOCK_SH:LOCK_EX)|LOCK_NB))fail("locked");
    unsigned char r[RS]{};auto encode=[&](){std::memset(r,0,RS);std::memcpy(r,"A206IE\0",8);put(r+8,n);put(r+16,cursor);put(r+24,adds);for(unsigned m=0;m<=M;m++)for(unsigned c=0;c<2;c++)put(r+32+16*m+8*c,sums[m][c]);std::memcpy(r+528,ids.data(),ids.size());digest(r,RS-32,r+RS-32);};
    if(fresh){encode();save(dir,r);}else{int f=file(dir,"ctl.bin",O_RDONLY);req(size(f)==RS,"control size");bytes(f,r,RS,false);closeit(f);unsigned char d[32];digest(r,RS-32,d);req(!std::memcmp(d,r+RS-32,32),"control digest");req(!std::memcmp(r,"A206IE\0",8)&&get(r+8)==n&&!std::memcmp(r+528,ids.data(),96),"identity/config");cursor=get(r+16);adds=get(r+24);req(cursor<=end,"cursor");for(unsigned m=0;m<=M;m++)for(unsigned c=0;c<2;c++){sums[m][c]=get(r+32+16*m+8*c);req(sums[m][c]<mod[c],"residue domain");}unsigned char copy[RS];std::memcpy(copy,r,RS);encode();req(!std::memcmp(copy,r,RS),"canonical state");}
    req(adds==expected_additions(cursor,M),"cursor/work semantic identity");
    if(cursor<end){struct stat st{};req(fstatat(dir,"cnt.tsv",&st,AT_SYMLINK_NOFOLLOW)!=0&&errno==ENOENT,"complete count beside incomplete control");}
    double last=start;std::fprintf(stderr,"IE max=%u committed_subsets=%llu/%llu mode=%s\n",n,(unsigned long long)cursor,(unsigned long long)end,check?"READ_ONLY":"RUN");
    struct sigaction sa{};sa.sa_handler=caught;sigemptyset(&sa.sa_mask);if(sigaction(SIGINT,&sa,nullptr)||sigaction(SIGTERM,&sa,nullptr))fail("signals");
    while(!check&&cursor<end&&!stopflag&&clocknow()-start<seconds){uint64_t hi=cursor+quantum;if(hi>end)hi=end;std::array<A,16> local{};std::array<uint64_t,16> work{};
        #pragma omp parallel for num_threads(threads) schedule(static)
        for(uint64_t t=cursor;t<hi;t++){unsigned id=unsigned(omp_get_thread_num());alphabet(uint32_t(t),M,local[id],work[id]);}
        for(unsigned t=0;t<threads;t++){adds+=work[t];for(unsigned m=0;m<=M;m++)for(unsigned c=0;c<2;c++)sums[m][c]=plus(sums[m][c],local[t][m][c],c);}cursor=hi;encode();save(dir,r);
        if(clocknow()-last>=5){std::fprintf(stderr,"IE max=%u committed_subsets=%llu/%llu additions=%llu elapsed_s=%.0f\n",n,(unsigned long long)cursor,(unsigned long long)end,(unsigned long long)adds,clocknow()-start);last=clocknow();}
    }
    if(cursor==end){char text[4096];size_t used=0;for(unsigned m=0;m<=M;m++){int z=std::snprintf(text+used,sizeof text-used,"%u %llu %llu\n",m+1,(unsigned long long)sums[m][0],(unsigned long long)sums[m][1]);req(z>0&&size_t(z)<sizeof text-used,"result size");used+=size_t(z);}struct stat st{};
        if(fstatat(dir,"cnt.tsv",&st,AT_SYMLINK_NOFOLLOW)==0){int f=file(dir,"cnt.tsv",O_RDONLY);req(size(f)==used,"count size");char b[4096];bytes(f,b,used,false);closeit(f);req(!std::memcmp(b,text,used),"count mismatch");}else{req(errno==ENOENT&&!check,"missing result");int f=file(dir,"cnt.tmp",O_WRONLY|O_CREAT|O_TRUNC);bytes(f,text,used,true);sync(f);closeit(f);if(linkat(dir,"cnt.tmp",dir,"cnt.tsv",0)||unlinkat(dir,"cnt.tmp",0))fail("no clobber count");sync(dir);}
    }
    std::fprintf(stderr,"IE status=%s subsets=%llu additions=%llu elapsed_s=%.0f\n",cursor==end?"COMPLETE":"INCOMPLETE",(unsigned long long)cursor,(unsigned long long)adds,clocknow()-start);closeit(lock);closeit(dir);return check||cursor==end?0:2;
}
