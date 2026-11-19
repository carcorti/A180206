#include <omp.h>
#include <stdio.h>
static int value;
int main(void) {
    int total=0;
    #pragma omp parallel num_threads(4) reduction(+:total)
    {
        total += omp_get_thread_num()+1;
        #ifdef RACY
        for(int k=0;k<1000;k++)value++;
        #else
        #pragma omp single
        value=7;
        #pragma omp barrier
        total+=value;
        #endif
    }
    printf("%d %d\n",total,value);
    return 0;
}
