/* Bounded test interposer only. Never use for scientific jobs. */
#define _GNU_SOURCE
#define _LARGEFILE64_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <signal.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/statvfs.h>

int fstatvfs64(int fd,struct statvfs64 *st) {
    int (*real)(int,struct statvfs64 *);void *p=dlsym(RTLD_NEXT,"fstatvfs64");memcpy(&real,&p,sizeof real);
    int rc=real(fd,st);const char *s=getenv("A206_FREE");
    if(!rc && s){st->f_frsize=1;st->f_bavail=strtoull(s,NULL,10);}
    return rc;
}
FILE *fopen64(const char *name,const char *mode) {
    FILE *(*real)(const char *,const char *);void *p=dlsym(RTLD_NEXT,"fopen64");memcpy(&real,&p,sizeof real);
    if(getenv("A206_LOW_RAM") && !strcmp(name,"/proc/meminfo")) {
        static char b[]="MemAvailable: 1024 kB\n";return fmemopen(b,sizeof b-1,"r");
    }
    return real(name,mode);
}
int renameat(int a,const char *x,int b,const char *y) {
    int (*real)(int,const char *,int,const char *);void *p=dlsym(RTLD_NEXT,"renameat");memcpy(&real,&p,sizeof real);
    int rc=real(a,x,b,y);const char *s=getenv("A206_STOP");
    if(!rc && s && !strcmp(y,"ctl.bin")) {
        unsigned char r[64];int fd=openat(b,y,O_RDONLY);ssize_t z=pread(fd,r,sizeof r,0);close(fd);
        uint64_t seq=0,phase=0,n=0;
        if(z==(ssize_t)sizeof r){memcpy(&seq,r+8,8);memcpy(&phase,r+16,8);memcpy(&n,r+40,8);
            if((!strcmp(s,"initial") && seq==1)||(!strcmp(s,"dp") && seq==5)||(!strcmp(s,"conv") && phase==1 && n==10))raise(SIGTERM);
            if(!strcmp(s,"terminal") && phase==2)raise(SIGKILL);
        }
    }
    return rc;
}
