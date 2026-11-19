/* Bounded hot-path qualification. No full inclusion-exclusion traversal. */
#define main a206_ie_main
#include "ie.cpp"
#undef main
int main(){
    constexpr unsigned M=27;geometry(M);
    const uint64_t end=UINT64_C(1)<<M;
    for(unsigned nt: {1U,8U})for(unsigned trial=0;trial<2;trial++){
        uint64_t hi=end-trial*4096,lo=hi-4096;
        std::array<A,16> sums{};std::array<uint64_t,16> work{};
        double start=clocknow();
        #pragma omp parallel for num_threads(nt) schedule(static)
        for(uint64_t T=lo;T<hi;T++){unsigned id=unsigned(omp_get_thread_num());alphabet(uint32_t(T),M,sums[id],work[id]);}
        uint64_t adds=0;for(unsigned t=0;t<nt;t++)adds+=work[t];
        req(adds==expected_additions(hi,M)-expected_additions(lo,M),"fixture exact additions");
        std::printf("IEBENCH threads=%u holdout=%u alphabets=%llu additions=%llu seconds=%.9f\n",nt,trial,(unsigned long long)(hi-lo),(unsigned long long)adds,clocknow()-start);
    }
}
