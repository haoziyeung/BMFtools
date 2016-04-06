#ifndef BMF_INFER_H
#define BMF_INFER_H
#include <assert.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <zlib.h>
#include <tgmath.h>
#include <unordered_map>
#include <algorithm>
#include <functional>
#include "htslib/sam.h"
#include "include/bam.h" // for bam_get_library
#include "include/igamc_cephes.h" // for igamc
#include "lib/kingfisher.h"
#include "dlib/cstr_util.h"
#include "dlib/sort_util.h"
#include "dlib/bam_util.h"
#include "bmf_rsq.h"

namespace BMF {
    struct infer_aux_t {
        FILE *fqh;
        samFile *in;
        samFile *out;
        int cmpkey; // 0 for pos, 1 for unclipped start position
        uint32_t mmlim:16; // Mismatch failure threshold.
        uint32_t is_se:1;
        uint32_t write_supp:1;
        bam_hdr_t *hdr; // BAM header
        std::unordered_map<std::string, std::string> realign_pairs;
    };

    // Once a set of reads have been selected, their data is put into this class for collapsing.
    class BamFisherSet {
    uint32_t n:31;
    uint32_t is_read1:1;
    const int32_t len;
    const int32_t unclipped_start;
    std::vector<uint32_t> phred_sums; // Length: 5 * readlen
    std::vector<uint32_t> votes; // Length: 5 * readlen
    std::string max_observed_phreds; // Held in memory -33, write out as readable string.
    public:
        std::string name;
    private:
        void update_qual(uint8_t *qual) {
            for(int i = 0; i < len; ++i)
                if(max_observed_phreds[i] < qual[i])
                    max_observed_phreds[i] = qual[i];
        }
        /*
         * This sprintf's to the buffer in name, then tells it to resize
         * itself to the number of characters written, which is the
         * return value of sprintf.
         * This is probably evil, but very, very efficient.
         */
        void make_name(bam1_t *b) {
            kstring_t ks{0};
            LOG_DEBUG("Unclipped start: %i.\n", unclipped_start);
            if(is_read1) {
                ksprintf(&ks, "collapsed:%i:%i:%i:%i:%i:%i:%i:%i",
                         unclipped_start, bam_itag(b, "MU"), // Unclipped starts for self and mate
                         b->core.tid, b->core.mtid, // Contigs
                         !!(b->core.flag & (BAM_FREVERSE)), !!(b->core.flag & (BAM_FMREVERSE)), // Strandedness combinations
                         b->core.l_qseq, bam_itag(b, "LM") // Read length of self and mate.
                         );
            } else {
                ksprintf(&ks, "collapsed:%i:%i:%i:%i:%i:%i:%i:%i",
                         bam_itag(b, "MU"), unclipped_start,
                         b->core.mtid, b->core.tid,
                         !!(b->core.flag & (BAM_FMREVERSE)), !!(b->core.flag & (BAM_FREVERSE)),
                         bam_itag(b, "LM"), b->core.l_qseq
                         );
            }
            name = ks.s;
            free(ks.s);
        }
    public:
        uint32_t get_is_read1() {
            return is_read1;
        }
        void add_rec(bam1_t *b) {
            assert(b->core.l_qseq == len);
            uint8_t *seq = bam_get_seq(b);
            uint8_t *qual = bam_get_qual(b);
            update_qual(qual);
            for(int i = 0; i < len; ++i) {
                const int ind = i * 5 + seqnt2num(bam_seqi(seq, i));
                phred_sums[ind] += qual[i];
                //LOG_DEBUG("Incrementing votes at index %i for read index %i  with seqnt2num %i.\n", ind, i, seqnt2num(bam_seqi(seq, i)));
                ++votes[ind];
            }
            ++n;
        }
        BamFisherSet(bam1_t *b) :
        n(1),
        is_read1(!!(b->core.flag & BAM_FREAD1)),
        len(b->core.l_qseq),
        unclipped_start(is_read1 ? dlib::get_unclipped_start(b): bam_itag(b, "MU")),
        phred_sums(len * 5)
        {
            LOG_DEBUG("Unclipped start: %i. Return from function: %i.\n", unclipped_start, is_read1 ? dlib::get_unclipped_start(b): bam_itag(b, "MU"));
            assert((b->core.flag & (BAM_FUNMAP | BAM_FMUNMAP)) == 0);
            max_observed_phreds.resize(len);
            votes.resize(len * 5);
            update_qual(bam_get_qual(b));
            make_name(b);
            add_rec(b);
        }
        std::string to_fastq();
    };

    class BamFisherKing {
    std::unordered_map<int32_t, BamFisherSet> sets;
    public:

    BamFisherKing(dlib::tmp_stack_t *stack) {
            std::sort(stack->a, stack->a + stack->n, [](bam1_t *a, bam1_t *b) {
                return a ? (b ? (int)(strcmp(bam_get_qname(a), bam_get_qname(b)) < 0): 0): (b ? 1: 0);
            });
            std::for_each(stack->a, stack->a + stack->n, [&](bam1_t *b) {
                auto found = sets.find(b->core.l_qseq);
                if(found == sets.end()) {
                    sets.emplace(b->core.l_qseq, BamFisherSet(b));
                } else {
                    found->second.add_rec(b);
                }
            });
        }
        void add_to_hash(infer_aux_t *settings);
    };
    // In this prototype, we're ignoring the alignment stop, though it should likely be expanded to include it.
} /* namespace BMF */

#endif /* BMF_INFER_H */