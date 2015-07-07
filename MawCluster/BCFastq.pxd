cimport cython
cimport numpy as np
cimport pysam.calignmentfile
cimport pysam.cfaidx
cimport utilBMF.HTSUtils
ctypedef utilBMF.HTSUtils.pFastqFile pFastqFile_t
ctypedef utilBMF.HTSUtils.pFastqProxy pFastqProxy_t
from utilBMF.HTSUtils cimport chr2ph, chr2phStr, int2Str, ph2chrDict
from utilBMF.cstring cimport cs_to_ph, cs_to_ia, PH2CHR_TRANS
from utilBMF.Inliners cimport Num2Nuc, Nuc2Num
from numpy cimport ndarray
from cpython cimport array as c_array
import cython.str
ctypedef cython.str cystr
ctypedef c_array.array py_array
ctypedef np.int32_t np_int32_t

cdef cystr cCompareFqRecsFast(list R, cystr name=?, double minPVFrac=?,
                              double minFAFrac=?, double minMaxFA=?)
cpdef cystr pCompareFqRecsFast(list R, cystr name=?)
cpdef cystr MakeTagComment(cystr saltedBS, pFastqProxy_t rec, int)

cdef cystr cQualArr2QualStr(ndarray[np_int32_t, ndim=1] qualArr)
cpdef cystr QualArr2QualStr(ndarray[np_int32_t, ndim=1] qualArr)

cpdef cystr QualArr2PVString(ndarray[np_int32_t, ndim=1] qualArr)
cdef cystr cQualArr2PVString(ndarray[np_int32_t, ndim=1] qualArr)
cdef cystr cQualArr2FAString(ndarray[np_int32_t, ndim=1] qualArr)


cdef inline bint BarcodePasses(cystr barcode, int hpLimit):
    if("N" in barcode or "A" * hpLimit in barcode or
       "C" * hpLimit in barcode or
       "G" * hpLimit in barcode or "T" * hpLimit in barcode):
        return False
    else:
        return True


cdef inline cystr cMakeTagComment(cystr saltedBS,
                                  pFastqProxy_t rec, int hpLimit):
    cdef bint PASS = BarcodePasses(saltedBS, hpLimit)
    if(PASS == True):
        return "~#!#~" + rec.comment + "|FP=IndexPass|BS=" + saltedBS
    else:
        return "~#!#~" + rec.comment + "|FP=IndexFail|BS=" + saltedBS

cdef public dict Num2NucDict

cdef public cystr ARGMAX_TRANSLATE_STRING
