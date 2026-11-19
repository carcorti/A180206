/* Synthetic output qualification: factorial bounds are NOT sequence values. */
#define main a206_program_main
#include "../src/a180206.c"
#undef main
int main(int argc,char **argv) {
    started=heartbeat=now();need(argc==3,"fixture directory and mode");init(28);
    dirfd=open(argv[1],O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);need(dirfd>=0,"fixture directory");
    State s={0};for(unsigned n=1;n<=CAP;n++)s.result[n]=fact[n];
    finish(&s,!strcmp(argv[2],"check"));closefd(dirfd);return 0;
}
