#ifndef PAIR_UTIL_H
#define PAIR_UTIL_H
#include <ctype.h>
#include <errno.h>
#include <inttypes.h>
#include <omp.h>
#include <regex.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <zlib.h>
#include "bam.h"
#include "bam_rescue.h"
#include "cstr_util.h"
#include "htslib/khash.h"
#include "htslib/klist.h"
#include "htslib/ksort.h"
#include "htslib/kstring.h"
#include "htslib/sam.h"
#include "flow_util.h"
#include "io_util.h"
#include "mem_util.h"
#include "sam.h"
#include "sam_opts.h"


#ifndef ucs_sort_mate_key
#define ucs_sort_mate_key(a) (uint64_t)((uint64_t)a->core.mtid<<32|(bam_aux2i(bam_aux_get(b, "MU")) + 1)<<2|(!!(a->core.flag & BAM_FMREVERSE)))
#endif

#ifndef ucs_sort_core_key
#define ucs_sort_core_key(a) (uint64_t)((uint64_t)a->core.tid<<32|(bam_aux2i(bam_aux_get(b, "SU"))+1)<<2|bam_is_rev(a)<<1|bam_is_r1(a))
#endif

#ifndef bmfsort_core_key
#define bmfsort_core_key(a) (uint64_t)((uint64_t)a->core.tid<<32|(a->core.pos+1)<<2|bam_is_rev(a)<<1|bam_is_r1(a))
#endif

#ifndef bmfsort_mate_key
#define bmfsort_mate_key(a) (uint64_t)((uint64_t)a->core.mtid<<32|(a->core.mpos+1))
#endif

static inline void add_unclipped_mate_starts(bam1_t *b1, bam1_t *b2);

static inline void add_unclipped_mate_starts(bam1_t *b1, bam1_t *b2) {
	uint32_t i, offset1 = 0, offset2 = 0, ucs1 = b1->core.pos, ucs2 = b2->core.pos;
	uint32_t *cigar1 = bam_get_cigar(b1);
	uint32_t *cigar2 = bam_get_cigar(b2);
	for(i = 0; i < b1->core.n_cigar; ++i) {
		if(!(cigar1[i]&0xf)) { // 'M' in cigar.
			break;
		}
		else {
			offset1 += cigar1[i] >> BAM_CIGAR_SHIFT;
		}
	}
	for(i = 0; i < b2->core.n_cigar; ++i) {
		if(!(cigar2[i]&0xf)) {
			break;
		}
		else {
			offset2 += cigar2[i] >> BAM_CIGAR_SHIFT;
		}
	}
	ucs1 += (b1->core.flag & BAM_FREVERSE) ? offset1: -1 * offset1;
	ucs2 += (b2->core.flag & BAM_FREVERSE) ? offset2: -1 * offset2;
	bam_aux_append(b2, "MU", 'I', sizeof(uint32_t), (uint8_t *)&ucs1);
	bam_aux_append(b1, "MU", 'I', sizeof(uint32_t), (uint8_t *)&ucs2);
	return;
}

#endif
