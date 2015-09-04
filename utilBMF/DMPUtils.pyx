import logging
import gzip
import os
import subprocess
import time
import cProfile
import cStringIO

from MawCluster.BCFastq import FastFisherFlattening, CutadaptPaired
from utilBMF.HTSUtils import (pFastqProxy, pFastqFile, permuteNucleotides,
                                printlog as pl, getBS)
from utilBMF.ErrorHandling import ThisIsMadness as Tim
from utilBMF.ErrorHandling import UnsetRequiredParameter, ImproperArgumentError

import multiprocessing as mp


def singleDMPWorker(Fastq, IndexFq, bcLen, Prefix, hpLimit, Head=0):
    """
    Not implemented!
    """
    raise Tim("Not yet Implemented!  Sorry!")
    pass


def pairedDMPWorker(Fastq1, Fastq2, cystr Prefix, int bcLen, IndexFq="default",
                    int hpLimit=100, int Head=0, cutAdapt=False,
                    p3Seq="default", p5Seq="default", profile=False):
    """
    dmpWorker function, pulls a bunch of reads into memory based on their
    BC prefix marks then consolidates them.
    """
    if(profile):
        import cProfile
        import pstats
        pr = cProfile.Profile()
        pr.enable()
    cdef int lenPrefix
    cdef pFastqFile_t fq1, fq2, indexFq
    cdef pFastqProxy_t read1, read2
    cdef cystr BC, bin, fq1name, fq2name
    cdef dict bcHash1, bcHash2
    fq1 = pFastqFile(Fastq1)
    fq2 = pFastqFile(Fastq2)
    indexFq = pFastqFile(IndexFq)
    ifq1n = fq1.next
    ifq2n = fq2.next
    bcHash1 = {}
    bcHash2 = {}
    lenPrefix = len(Prefix)
    pl("now starting dmp on prefix %s" % (Prefix))
    for bcRead in indexFq:
        read1 = ifq1n()
        read2 = ifq2n()
        BC = bcRead.sequence
        if Head:
            BC = (read1.sequence[1:Head + 1] + BC +
                       read2.sequence[1:Head + 1])
        bin = BC[:lenPrefix]
        if Prefix != bin:
            continue
        read1.comment = cMakeTagComment(BC, read1, hpLimit)
        read2.comment = cMakeTagComment(BC, read2, hpLimit)
        try:
            bcHash1[BC].append(read1)
            bcHash2[BC].append(read2)
        except KeyError:
            bcHash1[BC]=[read1]
            bcHash2[BC]=[read2]
    fq1name = Fastq1.split(".")[0]+"."+Prefix+".fastq"
    fq2name = Fastq2.split(".")[0]+"."+Prefix+".fastq"
    output1 = open(fq1name,'w')
    output2 = open(fq2name,'w')
    with open(fq1name, 'w') as output1, open(fq2name, 'w') as output2:
        for barcode in bcHash1.keys():
            output1.write(FastFisherFlattening(bcHash1[barcode], barcode))
            output2.write(FastFisherFlattening(bcHash2[barcode], barcode))
    if cutAdapt:
        cafq1, cafq2 = CutadaptPaired(fq1name, fq2name, p3Seq, p5Seq)
        pl("runnning cutadapt on temporary fastq with prefix %s" %(Prefix))
        subprocess.check_call(["rm", fq1name])
        subprocess.check_call(["rm", fq2name])
        pl("completed dmp on prefix %s" % (Prefix))
        if(profile):
            s = cStringIO.StringIO()
            pr.disable()
            sortby = "cumulative"
            ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
            ps.print_stats()
            open("cProfile.stats.%s.txt" % Prefix, "w").write(s.getvalue())
        return cafq1, cafq2
    pl("completed dmp on prefix %s" % (Prefix))
    if(profile):
        s = cStringIO.StringIO()
        pr.disable()
        sortby = "cumulative"
        ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
        ps.print_stats()
        open("cProfile.stats.%s.txt" % Prefix, "w").write(s.getvalue())
    return fq1name, fq2name


def get_uncompressed_size(file):
    """
    Used to get uncompressed Fastq file sizes
    possibly ineffiecent, not currently Used.
    """
    fileobj = open(file, 'r')
    fileobj.seek(-8, 2)
    crc32 = gzip.read32(fileobj)
    isize = gzip.read32(fileobj)  # may exceed 2GB
    fileobj.close()
    return isize


def calcMaxRam(maxRam, ncpus, fastq):
    """
    Someday I will use this to estimate the proper prefix length
    for splitting a fastq based on desired maxRam and nCPUs.
    Today is not that day.
    """
    cdef long fqSize, mRam
    cdef int lprefix
    mRam = maxRam*1000000000
    fqSize = get_uncompressed_size(fastq)*2
    for x in range(3,10):
        topRam = (fqSize/(4**x))*ncpus
        if topRam < mRam:
            lprefix = x
            break
    return lprefix


def deleter(fname):
    subprocess.check_call(["rm", fname])


def profile_worker(Fastq1, Fastq2, cystr Prefix, int bcLen, IndexFq="default",
                    int hpLimit=100, int Head=0, cutAdapt=False,
                    p3Seq="default", p5Seq="default"):
    impFqs = cProfile.runctx("pairedDMPWorker(Fastq1, Fastq2, Prefix, bcLen, IndexFq, "
                        "hpLimit, Head, cutAdapt, p3Seq, p5Seq)", globals(),
                         locals(), 'profile-%s.out' %Prefix)
    return impFqs


def multiProcessingDemulitplex(inFqs, indexFq="default", int head=0,
                                int ncpus=1, int len_prefix=3,
                                double hpLimit=0.8, cutAdapt=False, p3Seq=None,
                                p5Seq=None, profile=False):
    """
    Args I need:
        1. In Fastq, 1 or 2 fastqs in a list, call worker based on number
        2. Index fastq containing barcodes
        3. amount of sequence to salt into barcode (head) default = 0
        4. homopolymer proportion (default 80%) to fail reads
        5. Runnign cut adapt? True/False
        6. if above true, p3Seq, p5Seq, and overlap len
        7. number of CPUS to run across
    Similar to DispatchParallelDMP, but redesigned for multiprocessing
     of the DMP process.
    """
    if len_prefix != 3:
        pl("using custom number of nucleotides for splitting temporary files"
        ", recommended value is 3, used here %s" % (len_prefix))
    if indexFq == "default":
        raise UnsetRequiredParameter("Index fastq with barcodes is required")
    if head < 0:
        raise UnsetRequiredParameter("Improper or unset head value defaulting"
                                     "to 0")
        head = 0
    if(len(inFqs) > 2 or len(inFqs) < 1):
        raise UnsetRequiredParameter("Improper number of Fastqs specified,"
            "How did you even do this?")
    if(cutAdapt == False):
        pl("Running without cutadapt calls, DMP'd reads will not be adapter"
           " trimmed.")
    if(cutAdapt == True):
        if not p3Seq or not p5Seq:
            raise UnsetRequiredParameter("Must specifiy adapter sequence,"
            " to run cutadapt")
        pl("DMP will be followed by cut adapt on temporary fastq files,"
           " slightly less IO efficent because cutadapt can't be run in buffer")
    allPrefixes = permuteNucleotides(4**len_prefix, kmerLen=len_prefix)
    bcLen = len(pFastqFile(indexFq).next().sequence)
    pl("inferred barcode length is %s" % (bcLen))
    hpLimit = int(hpLimit * bcLen)
    pl("length of homopolymer for barcode be be marked QC fail: %s" % (hpLimit))
    kwargsDict = {
    'IndexFq': indexFq,
    'Head': head,
    'hpLimit': hpLimit,
    'cutAdapt': cutAdapt,
    'p3Seq': p3Seq,
    'p5Seq': p5Seq,
    'profile': profile}
    pl("running multiprocessed DMP using %s CPUs" % (ncpus))
    pool = mp.Pool(processes=ncpus)
    """
    Need to return all the names of teh Fastqs that are created.  These
    Will be system called to cat (using mp?), then remove the temp fastqs, and
    gzip the combined fastq.
    """
    if(len(inFqs) == 2):
        outFq1 = inFqs[0].split('.')[0]+".dmp.fastq"
        outFq2 = inFqs[1].split('.')[0]+".dmp.fastq"
        if cutAdapt:
            outFq1 = outFq1.split('.fastq')[0]+"cutadapt.fastq"
            outFq2 = outFq2.split('.fastq')[0]+"cutadapt.fastq"
        #if profile:
        #    tmpFqs = [pool.apply_async(profile_worker, args=(inFqs[0],
        #        inFqs[1], prefix, bcLen), kwds=kwargsDict) for prefix
        #        in allPrefixes]
        tmpFqs = [pool.apply_async(pairedDMPWorker, args=(inFqs[0],
            inFqs[1], prefix, bcLen), kwds=kwargsDict) for prefix
            in allPrefixes]
        fq1List = [p.get()[0] for p in tmpFqs]
        fq2List = [p.get()[1] for p in tmpFqs]
        pl("Demultiplexing complete, concatenating temp files...")
        subprocess.check_call("cat %s > %s" % (" ".join(fq1List), outFq1),
                                shell=True)
        subprocess.check_call("cat %s > %s" % (" ".join(fq2List), outFq2),
                                shell=True)
        pl("concatination complete, gzipping fastq and deleting temp files")
        check = [pool.apply_async(deleter, args=(f, )) for f in fq1List+fq2List]
        empty = [p.get() for p in check]
        subprocess.check_call(["gzip", outFq1])
        subprocess.check_call(["gzip", outFq2])
    if(len(inFqs) == 1):
        raise Tim("There is no one here.  Go away! (single fastq DMP not yet"
                  "implemented")
    return outFq1, outFq2