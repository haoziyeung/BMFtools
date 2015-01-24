from MawCluster.SVUtils import *
from utilBMF import HTSUtils

import copy
import pudb


def BMFXLC(inBAM,
           minMQ=0,
           minBQ=0,
           bedfile="default",
           minClustDepth=5,
           minPileupLen=10,
           outfile="default",
           ref="default",
           insDistance="default",
           bedDist=10000):
    """
    Makes calls for translocations using SV Tags placed during SVUtils
    BAM must have these tags in order to find structural variants.
    Name Sorting required.
    Minimum BQ is not recommended for translocation calls.
    """
    # pudb.set_trace()
    if(outfile == "default"):
        outfile = inBAM[0:-4] + ".putativeSV.txt"
        print("Outfile: {}".format(outfile))
    outHandle = open(outfile, "w")
    if(bedfile == "default"):
        FacePalm("Capture bed file required for translocation detection.")
    if(ref == "default"):
        ThisIsMadness("Path to reference index required!")
    if(insDistance == "default" or insDistance is None):
        insDistance = 35
    else:
        insDistance = int(insDistance)
    print("Insert distance increment: {}".format(insDistance))
    # Do calls for LI first.
    # Now looking for intrachromosomal translocations
    LIBamRecords = HTSUtils.LoadReadPairsFromFile(inBAM, SVTag="LI,ORB",
                                                  minMQ=minMQ, minBQ=minBQ)
    MDCBamRecords = HTSUtils.LoadReadPairsFromFile(inBAM, SVTag="MDC,ORB",
                                                   minMQ=minMQ, minBQ=minBQ)
    inHandle = pysam.AlignmentFile(inBAM, "rb")
    AllBamRecs = []
    while True:
        try:
            AllBamRecs.append(inHandle.next())
        except StopIteration:
            print("All BAM records loaded.")
            break
    header = inHandle.header
    print("Number of records meeting requirements: {}".format(
        len(LIBamRecords)))
    ContigList = list(set([pair.read1_contig for pair in LIBamRecords]))
    PutativeIntraXLocs = []
    parsedBedfile = HTSUtils.ParseBed(bedfile)
    for contig in ContigList:
        print("Beginning contig: {}".format(contig))
        WorkingPairSet = [pair for pair in LIBamRecords
                          if pair.read1_contig == contig]
        print("For contig {}, I am about to cluster by insert size.".format(
            contig))
        Clusters = ClusterByInsertSize(WorkingPairSet, insDistance=insDistance)
        print("Number of clusters: {}".format(len(Clusters)))
        if(len(Clusters) == 0):
            continue
        PutXIntervals = PileupISClustersByPos(Clusters,
                                              minClustDepth=minClustDepth,
                                              bedfile=parsedBedfile,
                                              minPileupLen=minPileupLen)
        print("Number of putative events to check: {}".format(
            len(PutXIntervals)))
        if(len(PutXIntervals) == 0):
            print("No PutXIntervals for contig {}".format(contig))
            continue
        PutTransReadPairSets = [
            SVSupportingReadPairs(interval,
                                  inHandle=inHandle,
                                  recList=copy.copy(AllBamRecs),
                                  minMQ=minMQ,
                                  SVType="LI")
            for interval in PutXIntervals]
        print("PutXIntervals made. Repr: {}".format(repr(
            PutTransReadPairSets)))
        for event in PutTransReadPairSets:
            bedIntervalList = HTSUtils.CreateIntervalsFromCounter(
                HTSUtils.ReadPairListToCovCounter(event,
                                                  minClustDepth=minClustDepth,
                                                  minPileupLen=minPileupLen),
                minPileupLen=minPileupLen,
                contig=contig,
                bedIntervals=parsedBedfile,
                mergeDist=150)
            PutativeIntraXLocs.append(PutativeXLoc(
                intervalList=bedIntervalList, ReadPairs=event,
                bedIntervals=parsedBedfile, header=header,
                TransType="IntrachromosomalRearrangement",
                inBAM=inBAM))
        del WorkingPairSet
    ContigSets = [i.split(',') for i in list(set([','.join(sorted([
        pair.read1_contig,
        pair.read2_contig])) for pair in MDCBamRecords])) if "GL" not in i]
    PutativeInterXLocs = []
    XLocVCFLinesIntra = list(set([TranslocationVCFLine(
        xLoc, inBAM=xLoc.inBAM, TransType="InterchromosomalRearrangement",
        ref=ref)
        for xLoc in PutativeInterXLocs if xLoc.nsegments != 0]))
    for cSet in ContigSets:
        WorkingPairSet = [
            pair for pair in MDCBamRecords if
            sorted([pair.read1_contig, pair.read2_contig]) == cSet]
        IntervalsToCheck = PileupMDC(WorkingPairSet,
                                     minClustDepth=minClustDepth,
                                     bedfile=parsedBedfile,
                                     minPileupLen=minPileupLen,
                                     bedDist=bedDist)
        PutTransReadPairSets = [
            SVSupportingReadPairs(
                interval, inHandle=inHandle,
                recList=copy.copy(
                    AllBamRecs),
                minMQ=minMQ,
                SVType="MDC") for interval in IntervalsToCheck]
        for event in PutTransReadPairSets:
            bedIntervalList = []
            for contig in cSet:
                bedIntervalList.append(HTSUtils.CreateIntervalsFromCounter(
                    HTSUtils.ReadPairListToCovCounter(
                        event,
                        minClustDepth=minClustDepth,
                        minPileupLen=minPileupLen),
                    minPileupLen=minPileupLen,
                    contig=contig,
                    bedIntervals=parsedBedfile,
                    mergeDist=150))
            if(len(bedIntervalList) == 0 or len(bedIntervalList[0]) == 0):
                continue
            PutativeInterXLocs.append(PutativeXLoc(
                intervalList=bedIntervalList,
                ReadPairs=event,
                bedIntervals=parsedBedfile,
                header=header,
                TransType="Interchromosoma"
                "lRearrangement",
                inBAM=inBAM))
    XLocVCFLinesInter = list(set([TranslocationVCFLine(
        xLoc, inBAM=xLoc.inBAM,
        TransType="InterchromosomalRearrangement", ref=ref)
        for xLoc in PutativeInterXLocs if
        xLoc.nsegments != 0]))
    XLocVCFLines = XLocVCFLinesIntra + XLocVCFLinesInter
    for line in XLocVCFLines:
        if(line.TransType == "IntrachromosomalRearrangement"):
            if(line.NumPartners != 0 and line.TDIST >= 50000):
                outHandle.write(line.ToString() + "\n")
        if(line.TransType == "InterchromosomalRearrangement"):
            if(line.NumPartners != 0):
                outHandle.write(line.ToString() + "\n")
    outHandle.close()
    """
    Step 4: Try to create the consensus sequence using soft-clipped reads
    Step 5 (?): Create a variant graph using glia and verify the translocation.
    """
    # MDCBamRecords = HTSUtils.LoadReadPairsFromFile(inBAM, SVTag="MDC,ORB")
    # For MDC, Repeat, except that before doing the (within distance) filter,
    # get sets of reads which align to the same set of different contigs.
    return None