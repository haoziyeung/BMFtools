import re
import subprocess
import string

import BCBam
import BCFastq
import HTSUtils
import BCVCF
from HTSUtils import printlog as pl


def pairedBamProc(consfq1, consfq2, consfqSingle="default", opts="",
                  bamPrefix="default", ref="default", aligner="default"):
    if(ref == "default"):
        raise ValueError("Reference index required!")
    if(bamPrefix == "default"):
        bamPrefix = '.'.join(consfq1.split('.')[0:-1])
    if(aligner == "default"):
        pl("No aligner set, defaulting to bwa.")
        aligner = "bwa"
    outsamProperPair = bamPrefix + '.sam'
    outbamProperPair = bamPrefix + '.bam'
    outsamSingle = bamPrefix + "solo.sam"
    outbamSingle = bamPrefix + "solo.bam"
    pl("The output SAM file: {}. Output BAM file: {}".format(
        outsamProperPair, outbamProperPair))
    if(aligner == "bwa"):
        outsamProperPair, bwa_command = HTSUtils.align_bwa(
            consfq1, consfq2, ref, opts, outsamProperPair)
        pl("Aligner command was {}".format(bwa_command))
        if(consfqSingle != "default"):
            outsamSingle, bwase_command = HTSUtils.align_bwa_se(
                consfqSingle, ref, opts, outsamSingle)
            pl(
                "Aligner command for single-end was {}".format(bwase_command))
            pl("Converting single-end sam to bam")
            BCBam.Sam2Bam(outsamSingle, outbamSingle)
            pl("Tagging solo BAM")
            taggedSingleBAM = BCBam.singleBarcodeTagging(
                consfqSingle, outbamSingle)
            pl("Removing unmapped reads and those failing filters.")
            passTaggedSingleBAM, failTSB = BCBam.singleFilterBam(
                taggedSingleBAM,
                criteria="complexity,adapter,ismapped")
            pl("Now generating index for solo reads")
            singleIndex = BCBam.GenBCIndexBAM(
                passTaggedSingleBAM)
            pl("Now tagging BAM file with family size.")
            familySizeSoloBAM, famLst = BCBam.getFamilySizeBAM(
                passTaggedSingleBAM, singleIndex)
            sortFSSBam = BCBam.CorrSort(familySizeSoloBAM)
    else:
        raise ValueError("Sorry, only bwa is supported currently.")
    pl("Converting SAM to BAM")
    BCBam.Sam2Bam(outsamProperPair, outbamProperPair)
    pl("Now tagging BAM with custom SAM tags.")
    taggedBAM = BCBam.pairedBarcodeTagging(
        consfq1, consfq2, outbamProperPair)
    pl("Now splitting the BAM into read 1 and read 2 files.")
    read1BAM, read2BAM = BCBam.splitBAMByReads(taggedBAM)
    pl("Now merging the barcodes from each pair in the BAM files.")
    concatBS = BCBam.mergeBarcodes(read1BAM, read2BAM)
    pl("BAM with merged barcodes is {}".format(concatBS))
    pl("Now generating double barcode index.")
    mappedMerge, failures = BCBam.pairedFilterBam(
        concatBS, criteria="complexity,adapter,barcode")
    doubleIndex = BCBam.GenBCIndexBAM(mappedMerge)
    p = subprocess.Popen(["wc", "-l", doubleIndex], stdout=subprocess.PIPE)
    out, err = p.communicate()
    pl("Number of families found: {}".format(
        re.findall(r'\d+', out)[0]))
    histochart = BCBam.GenerateFamilyHistochart(doubleIndex)
    pl("Histochart of family sizes: {}".format(histochart))
    # UNCOMMENT THIS BLOCK IF YOU WANT TO START MESSING WITH RESCUE
    '''
        pl("Rescue step, marking the BD as their Hamming distance.")
        newRef = GenerateBarcodeIndexReference(uniqueBigFamilies)
        indexBowtie(newRef)
        mergedFastq = mergeSequencesFastq(tags1, tags2,)
        joiningSAM = CustomRefBowtiePaired(mergedFastq,newRef)
        return
        joinedFamilies = fuzzyJoining(familyMarked,joiningSAM)
        pl("joinedFamilies is {}".format(joinedFamilies))
    '''
    pl("Now determining family size for the doubled barcodes.")
    families, BCList = BCBam.getFamilySizeBAM(
        mappedMerge, doubleIndex)
    familyP, familyF = BCBam.pairedFilterBam(
        families, criteria="family")
    corrSorted = BCBam.CorrSort(familyP)
    if(consfqSingle != "default"):
        mergedSinglePair = BCBam.mergeBams(corrSorted, sortFSSBam)
        return mergedSinglePair
    return corrSorted


def pairedFastqEnd(argLst):
    inFastq = argLst[0]
    homing = argLst[1]
    if(homing == "default"):
        raise ValueError("Homing sequence required.")
    # For reads 1
    homingP, homingF = BCFastq.HomingSeqLoc(
        inFastq, homing=homing)
    pl("Homing sequences located, reads parsed out.")
    pl("Now removing the homing sequence and the barcode.")
    tags, trimfq = BCFastq.TrimHoming(homingP, homing)
    pl("Now generating the barcode index.")
    BarcodeIndex = BCFastq.GenerateSingleBarcodeIndex(tags)
    FamFq, AllRds, FamRds = BCFastq.GetFamilySizeSingle(
        trimfq, BarcodeIndex)
    BSortFq = BCFastq.BarcodeSort(FamFq)
    return BSortFq


def pFPD(
        inFastq1, inFastq2, homing="default", stringency="default"):
    from multiprocessing import Process
    if(homing == "default"):
        raise ValueError("Homing sequence required.")
    if(stringency == "default"):
        stringency = 0.75
    argLst = [inFastq1, homing]
    P1 = Process(target=pairedFastqEnd, args=(argLst,))
    P1.start()
    argLst2 = [inFastq2, homing]
    BSortFq2 = pairedFastqEnd(argLst2)
    P1.join()
    BSortFq1 = string.replace(BSortFq2, "_R2_", "_R1_")
    BConsFastq1, BConsFastq2 = BCFastq.pairedFastqConsolidate(
        BSortFq1, BSortFq2, stringency=stringency)
    BConsFqIndex1 = BCFastq.GenerateFullFastqBarcodeIndex(BConsFastq1)
    BConsFqIndex2 = BCFastq.GenerateFullFastqBarcodeIndex(BConsFastq2)
    BConsPair1, BConsPair2, BarcodeSingle = BCFastq.findProperPairs(
        BConsFastq1, BConsFastq2, index1=BConsFqIndex1, index2=BConsFqIndex2)
    return BConsPair1, BConsPair2, BarcodeSingle


def pairedFastqProc(inFastq1, inFastq2, homing="default",
                    stringency="default"):
    if(stringency == "default"):
        stringency = 0.75
    if(homing == "default"):
        homing = "CAGT"
    # For reads 1
    homingP1, homingF1 = BCFastq.HomingSeqLoc(
        inFastq1, homing=homing)
    pl("Homing sequences located, reads parsed out.")
    pl("Now removing the homing sequence and the barcode.")
    tags1, trimfq1 = BCFastq.TrimHoming(homingP1, homing)
    pl("Now generating the barcode index.")
    BarcodeIndex1 = BCFastq.GenerateSingleBarcodeIndex(tags1)
    FamFq1, AllRds1, FamRds1 = BCFastq.GetFamilySizeSingle(
        trimfq1, BarcodeIndex1)
    BSortFq1 = BCFastq.BarcodeSort(FamFq1)
    # For reads 2
    homingP2, homingF2 = BCFastq.HomingSeqLoc(
        inFastq2, homing=homing)
    pl("Homing sequences located, parsing reads.")
    pl("Now removing the homing sequence and the barcode.")
    tags2, trimfq2 = BCFastq.TrimHoming(homingP2, homing)
    pl("Now generating the barcode index.")
    BarcodeIndex2 = BCFastq.GenerateSingleBarcodeIndex(tags2)
    FamFq2, TotalReads2, FamReads2 = BCFastq.GetFamilySizeSingle(
        trimfq2, BarcodeIndex2)
    BSortFq2 = BCFastq.BarcodeSort(FamFq2)
    BConsFastq1, BConsFastq2 = BCFastq.pairedFastqConsolidate(
        BSortFq1, BSortFq2, stringency=stringency)
    BConsFqIndex1 = BCFastq.GenerateFullFastqBarcodeIndex(BConsFastq1)
    BConsFqIndex2 = BCFastq.GenerateFullFastqBarcodeIndex(BConsFastq2)
    BConsBSort1 = BCFastq.BarcodeSort(BConsFastq1)
    BConsBSort2 = BCFastq.BarcodeSort(BConsFastq2)
    BConsPair1, BConsPair2, BarcodeSingle = BCFastq.findProperPairs(
        BConsBSort1, BConsBSort2, index1=BConsFqIndex1, index2=BConsFqIndex2)
    return BConsPair1, BConsPair2, BarcodeSingle


def pairedVCFProc(consMergeSortBAM, ref="", opts="", bed=""):
    if(bed == ""):
        raise ValueError("Bed file location must be set!")
    if(ref == ""):
        raise ValueError("Reference index location must be set!")
    # Consolidating families into single reads
    # Variant Calling Step using MPileup
    # print("Now filtering for reads with NM > 0 only if you want to.")
    pl("Now sorting reads by coordinate to prepare for MPileup.")
    pl("Now creating a VCF using mpileup for variant calling.")
    MPileupVCF = BCVCF.MPileup(consMergeSortBAM, ref, bed=bed)
    pl("Initial mpileup: {}. Filtering.".format(MPileupVCF))
    ParsedVCF = BCVCF.ParseVCF(MPileupVCF)
    ParsedVCF.cleanRecords()
    CleanParsedVCF = BCVCF.CleanupPileup(MPileupVCF)
    return CleanParsedVCF


def singleBamProc(FamilyFastq, ref, opts, aligner="bwa", bamPrefix="default"):
    pl("Now tagging reads.")
    pl("Now filtering reads")
    if(bamPrefix == "default"):
        bamPrefix = FamilyFastq.split('.')[0] + '.FMS'
        outsam, outbam = bamPrefix + '.sam', bamPrefix + '.bam'
    pl("Output Sam: {}. Output Bam: {}".format(outsam, outbam))
    if(aligner == "bwa"):
        outsamFile, bwa_command = HTSUtils.align_bwa_se(
            FamilyFastq, ref, opts, outsam)
        pl("Aligner command was {}".format(bwa_command))
    else:
        raise ValueError("Sorry, I don't handle that aligner.")
    pl("Converting SAM to BAM")
    BCBam.Sam2Bam(outsam, outbam)
    taggedBAM = BCBam.singleBarcodeTagging(FamilyFastq, outbam)
    return taggedBAM


def singleFastqProc(inFastq, homing="default"):
    if(homing == "default"):
        homing = "CAGT"
    StdFilenames, ElseFilenames = BCFastq.HomingSeqLoc(inFastq, homing=homing)
    pl("Homing seq located, parsing these out.")
    pl("Now removing the homing and the barcode.")
    tags, trimfq = BCFastq.TrimHoming(StdFilenames, homing)
    pl("Now generating the barcode index.")
    BarcodeIndex = BCFastq.GenerateSingleBarcodeIndex(tags)
    FamilyFastq, TotalReads, FamReads = BCFastq.GetFamilySizeSingle(
        trimfq, BarcodeIndex)
    BSortFq = BCFastq.BarcodeSort(FamilyFastq)
    BConsFastq = BCFastq.singleFastqConsolidate(BSortFq, stringency=0.667)
    return BConsFastq


def singleVCFProc(ConsensusBam, bed, ref):
    pl("Now sorting reads by coordinate to prepare for MPileup.")
    CorrCons = BCBam.CorrSort(ConsensusBam)
    pl("Now creating a VCF using mpileup for variant calling.")
    MPileupVCF = BCVCF.MPileup(CorrCons, ref, bed=bed)
    pl("Initial mpileup: {}".format(MPileupVCF))
    ParsedVCF = BCVCF.ParseVCF(MPileupVCF)
    pl("Now removing those entries and parsing in the VCF Data")
    ParsedVCF.cleanRecords()
    CleanParsedVCF = BCVCF.CleanupPileup(MPileupVCF)
    return CleanParsedVCF
