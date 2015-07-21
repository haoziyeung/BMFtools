cimport cython
cimport pysam.calignmentfile
cimport pysam.calignedsegment
cimport pysam.cfaidx
cimport numpy as np
cimport utilBMF.HTSUtils
from cython cimport bint
from cpython cimport array as c_array
from libc.stdint cimport *
from libc.stdio cimport sprintf
from libc.string cimport memcpy
from pysam.chtslib cimport bam_aux2Z, bam_hdr_t, bam_get_seq
from numpy cimport ndarray
from utilBMF.HTSUtils cimport PysamToChrDict
from utilBMF.Inliners cimport Num2Nuc
from utilBMF.PysamUtils cimport PysamToChrInline
from utilBMF.cstring cimport struct_str
from utilBMF.MPA cimport MergeAgreedQualities, MergeDiscQualities
from pysam.calignedsegment cimport pysam_get_l_qname, bam1_t
ctypedef pysam.calignedsegment.AlignedSegment AlignedSegment_t
ctypedef pysam.calignmentfile.AlignmentFile AlignmentFile
ctypedef pysam.calignmentfile.AlignmentFile AlignmentFile_t
ctypedef cython.str cystr
ctypedef BamPipe BamPipe_t
ctypedef struct_str struct_str_t
ctypedef c_array.array py_array
ctypedef utilBMF.HTSUtils.pFastqProxy pFastqProxy_t

import cython
'''
cdef extern from "zlib.h" nogil:
    int inflate(ztream_p, int)
'''

cdef dict cGetCOTagDict(AlignedSegment_t read)

cpdef dict pGetCOTagDict(AlignedSegment_t read)


cdef inline bint c_argmax32i(int32_t q, int32_t r) nogil:
    return 0 if(q > r) else 1


cdef inline int32_t getFMFromAS(AlignedSegment_t read):
    return <int32_t> read.opt("FM")


@cython.boundscheck(False)
@cython.initializedcheck(False)
@cython.wraparound(False)
cdef inline int8_t BarcodeHD(char * str1, char * str2,
                             int8_t length) nogil:
    cdef int8_t ret = 0
    cdef uint16_t index
    for index in xrange(length):
        if(str1[index] != str2[index]):
            ret += 1
    return ret


cdef inline bint IS_REV(AlignedSegment_t read):
    return read.is_reverse


cdef inline bint IS_READ1(AlignedSegment_t read):
    return read.is_read1


cdef inline int MPOS(AlignedSegment_t read):
    return read.mpos


cdef inline int POS(AlignedSegment_t read):
    return read.pos


cdef inline int REF_ID(AlignedSegment_t read):
    return read.reference_id


cdef inline int RNEXT(AlignedSegment_t read):
    return read.rnext


cdef class BamPipe:
    """
    Creates a callable function which acts on a BAM stream.

    :param function - callable function which returns an input BAM object.
    :param bin_input - boolean - true if input is BAM
    false for TAM/SAM
    :param bin_output - boolean - true to output in BAM format.
    :param uncompressed_output - boolean - true to output uncompressed
    BAM records.
    """
    cdef public object function
    cdef public bint bin_input, bin_output, uncompressed_output
    cdef public AlignmentFile_t inHandle, outHandle
    cpdef process(self)
    cdef write(self, AlignedSegment_t read)

