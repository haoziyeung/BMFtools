cimport cython
cimport pysam.calignmentfile
cimport pysam.cfaidx
from cython cimport bint
from numpy cimport ndarray
from utilBMF.HTSUtils cimport PysamToChrDict
from utilBMF.Inliners cimport Num2Nuc
from utilBMF.PysamUtils cimport PysamToChrInline
ctypedef pysam.calignmentfile.AlignedSegment AlignedSegment_t
ctypedef pysam.calignmentfile.AlignmentFile AlignmentFile
ctypedef cython.str cystr

cdef cystr cBarcodeTagCOBam(pysam.calignmentfile.AlignmentFile bam,
                      pysam.calignmentfile.AlignmentFile outbam)
cpdef cystr pBarcodeTagCOBam(cystr bam, cystr outbam=?)

cdef dict cGetCOTagDict(AlignedSegment_t read)

cpdef dict pGetCOTagDict(AlignedSegment_t read)

cdef double getAF(AlignedSegment_t read)
cdef double getSF(AlignedSegment_t read)
# cpdef AlignedSegment_t TagAlignedSegment(AlignedSegment_t read)


cdef inline cystr RPString(AlignedSegment_t read):
    return (PysamToChrInline(read.reference_id) + ":%s," % read.pos +
            PysamToChrInline(read.rnext) +
            ":%s" % read.mpos)
