from HTSUtils import printlog as pl

'''
TODO: Filter based on variants supported by reads going both ways.
TODO: Create a tsv file containing all passing variants, frequencies.
TODO: Run a variant-caller on the sample as a whole to make a list
    from which to subtract variants and heterozygotes

'''


class VCFFile:

    """A simple VCFFile object, consisting of a header, a name for the file
    from which they came, and a list of all VCFRecords.
    Access header through self.header (list of strings, one for each line)
    Access VCF Entries through self.Records (list of VCFRecord objects)
    """

    def __init__(self, VCFEntries, VCFHeader, inputVCFName):
        self.sampleName = inputVCFName
        self.header = VCFHeader
        self.Records = VCFEntries
        self.sampleNamesArray = [inputVCFName]
        self.numSamples = len(self.sampleNamesArray)

    def cleanRecords(self):
        NewRecordList = [entry for entry in self.Records if entry.ALT != "X"]
        self.Records = NewRecordList

    def filter(self, filterOpt="default", param="default"):
        if(filterOpt == "default"):
            try:
                raise ValueError(
                    "Filter method required")
            except ValueError:
                print("Returning nothing.")
                return
        NewVCFEntries = []
        for entry in self.Records:
            if(VCFRecordTest(entry, filterOpt, param=param) is True):
                NewVCFEntries.append(entry)
        if(filterOpt == "bed"):
            if(param == "default"):
                try:
                    raise ValueError("Bed file required for bedfilter.")
                except ValueError:
                    print("Returning nothing.")
            filterOpt = filterOpt + "&" + param
        NewVCFFile = VCFFile(NewVCFEntries, self.header, self.sampleName
                             + "FilteredBy{}".format(filterOpt))
        # TODO: make a new VCFFile object based on location.
        return NewVCFFile

    def update(self):
        SetNames = []
        for record in self.Records:
            record.update()
            SetNames.append(record.VCFFilename)
        self.sampleNamesArray = list(set(SetNames))
        self.numSamples = len(self.sampleNamesArray)

    def len(self):
        try:
            return len(self.Records)
        except AttributeError:
            raise AttributeError("VCFFile object not initialized.")

    def write(self, Filename):
        FileHandle = open(Filename, "w")
        for headerLine in self.header:
            FileHandle.write("{}\n".format(headerLine))
        for VCFEntry in self.Records:
            FileHandle.write("{}\n".format(VCFEntry.toString()))
        FileHandle.close()
        return


class VCFRecord:

    """A simple VCFRecord object, taken from an item from
    the list which ParseVCF returns as "VCFEntries" """

    def __init__(self, VCFEntry, VCFFilename):
        self.CHROM = VCFEntry[0]
        self.POS = VCFEntry[1]
        self.ID = VCFEntry[2]
        self.REF = VCFEntry[3]
        if("X" != VCFEntry[4]):
            self.ALT = '.'.join(VCFEntry[4].split(',').remove("X"))
        else:
            self.ALT = "X"
        self.QUAL = VCFEntry[5]
        self.FILTER = VCFEntry[6]
        self.INFO = VCFEntry[7]
        self.InfoKeys = [entry.split(
            '=')[0] for entry in self.INFO.split(';') if entry != "NoCG"]
        self.InfoValues = []
        self.InfoUnpaired = []
        for entry in self.INFO.split(';'):
            #  print("entry: {}. INFO: {}".format(entry, self.INFO))
            try:
                self.InfoValues.append(entry.split('=')[1])
            except IndexError:
                self.InfoUnpaired
                continue
        #  print(self.InfoValues)
        #  Might not reproduce the original information when written to file.
        tempValArrays = [entry.split(',') for entry in self.InfoValues]
        try:
            self.InfoValArrays = [
                [entry for entry in array] for array in tempValArrays]
        except ValueError:
            self.InfoValArrays = [
                [entry for entry in array] for array in tempValArrays]
        self.InfoDict = dict(zip(self.InfoKeys, self.InfoValues))
        self.InfoArrayDict = dict(zip(self.InfoKeys, self.InfoValArrays))
        try:
            self.FORMAT = VCFEntry[8]
        except IndexError:
            self.FORMAT = ""
        try:
            self.GENOTYPE = VCFEntry[9]
        except IndexError:
            self.GENOTYPE = ""
        self.GenotypeDict = dict(
            zip(self.FORMAT.split(':'), self.GENOTYPE.split(':')))
        self.GenotypeKeys = self.FORMAT.split(':')
        self.GenotypeValues = self.GENOTYPE.split(':')
        self.Samples = [""]
        if(len(VCFEntry) > 10):
            for field in VCFEntry[10:]:
                self.Samples.append(field)
        self.VCFFilename = VCFFilename

    def update(self):
        self.InfoValues = [','.join(
            InfoValArray) for InfoValArray in self.InfoValArrays]
        infoEntryArray = [InfoKey + "=" + InfoValue for InfoKey,
                          InfoValue in zip(self.InfoKeys, self.InfoValues)]
        self.INFO = ';'.join(infoEntryArray) + ';'.join(self.InfoUnpaired)
        self.InfoKeys = [entry.split('=')[0] for entry in self.INFO.split(';')]
        self.InfoValues = [
            entry.split('=')[1] for entry in self.INFO.split(';')]
        tempValArrays = [entry.split(',') for entry in self.InfoValues]
        try:
            self.InfoValArrays = [
                [entry for entry in array] for array in tempValArrays]
        except ValueError:
            self.InfoValArrays = [
                [entry for entry in array] for array in tempValArrays]
        self.InfoDict = dict(zip(self.InfoKeys, self.InfoValues))
        self.InfoArrayDict = dict(zip(self.InfoKeys, self.InfoValArrays))
        self.GenotypeKeys = self.FORMAT.split(':')
        self.GenotypeValues = self.GENOTYPE.split(':')
        self.FORMAT = ":".join(self.GenotypeKeys)
        self.GENOTYPE = ":".join(self.GenotypeValues)
        self.GenotypeDict = dict(
            zip(self.FORMAT.split(':'), self.GENOTYPE.split(':')))
        if(len(self.Samples) == 0):
            recordStr = '\t'.join([self.CHROM, self.POS,
                                   self.ID, self.REF, self.ALT, self.QUAL,
                                   self.FILTER, self.INFO, self.FORMAT,
                                   self.GENOTYPE])
        else:
            sampleStr = "\t".join(self.Samples)
            recordStr = '\t'.join([self.CHROM, self.POS, self.ID,
                                   self.REF, self.ALT, self.QUAL,
                                   self.FILTER, self.INFO, self.FORMAT,
                                   self.GENOTYPE, sampleStr])
        self.str = recordStr.strip()

    def toString(self):
        self.update()
        return self.str

# TODO: I also want to be able to grab all of the records for a given record,
# as well as grab the file from which the records came.


# @Deprecated
def CleanupPileup(inputPileup, outputPileup="default"):
    import subprocess
    if(outputPileup == "default"):
        outputPileup = '.'.join(inputPileup.split('.')[0:-1]) + ".xrm.vcf"
    cmd = "awk '$5!=\"X\"' {} | sed 's:,X::g' > {}".format(
        inputPileup, outputPileup)
    subprocess.call(cmd, shell=True)
    return outputPileup


def fixVCF(inputVCF, outputVCF="default"):
    if(outputVCF == "default"):
        outputVCF = '.'.join(inputVCF.split('.')[0:-1]) + '.fixed.vcf'
    startVCF = ParseVCF(inputVCF)
    outVCFHeader = startVCF.header
    stdEntries = [i for i in startVCF.Records if(
                  len(i.REF) != len(i.ALT) or len(i.REF) == 1)]
    elseEntries = [i for i in startVCF.Records if(
                   len(i.REF) == len(i.ALT) and len(i.REF) > 1)]
    NewEntries = []
    for e in elseEntries:
        for pair in zip(e.REF, e.ALT):
            e.REF, e.ALT = pair[0], pair[1]
            newRecord = VCFRecord(e.toString().split('\t'), outputVCF)
            if(newRecord.ALT != newRecord.REF):
                stdEntries.append(newRecord)
    for s in stdEntries:
        NewEntries.append(s)
    outVCF = VCFFile(NewEntries, outVCFHeader, outputVCF)
    outVCF.write(outputVCF)
    return outVCF


def FreeBayesCall(inputBAM, ref="default", bed="default", ):
    """"""
    pass
    return


def MPileup(inputBAM, ref,
            bed="default",
            outputBCF="default",
            minbqual="20",
            minmqual="10"):
    import subprocess
    if(outputBCF == "default"):
        if(len(inputBAM.split('.')) >= 6):
            outputBCF = inputBAM.split('.')[0] + ".fullMP.vcf"
        else:
            outputBCF = '.'.join(inputBAM.split('.')[0:-1]) + ".fullMP.vcf"
    if(bed != "default"):
        cmd = ("samtools mpileup -f {} -F 0.00001 ".format(ref) +
               "-I -S -g -D -R -q " + minmqual + " -Q " + minbqual +
               " -l {} {}".format(bed, inputBAM) +
               " | bcftools view - > {}".format(outputBCF))
    else:
        cmd = ("samtools mpileup -f {} -F 0.00001 ".format(ref) +
               "-I -S -g -D -R -q " + minmqual + " -Q " + minbqual +
               " " + inputBAM + " | bcftools view - > {}".format(outputBCF))
    pl("{} is command string".format(cmd))
    subprocess.call(cmd, shell=True)
    return outputBCF


def ParseVCF(inputVCFName):
    infile = open(inputVCFName, "r")
    VCFLines = [entry.strip().split('\t') for entry in infile.readlines(
    ) if entry[0] != "#"]
    infile.seek(0)
    VCFHeader = [entry.strip(
    ) for entry in infile.readlines() if entry[0] == "#"]
    VCFEntries = [VCFRecord(
        entry, inputVCFName) for entry in VCFLines if entry.split(
            '\t')[4] != "X"]
    ParsedVCF = VCFFile(VCFEntries, VCFHeader, inputVCFName)
    return ParsedVCF


def VCFRecordTest(inputVCFRec, filterOpt="default", param="default"):
    lst = "bed,I16".split(',')
    # print("lst = {}".format(lst))
    if(filterOpt.lower() not in lst):
        raise ValueError(
            "Filter option not supported. Available options: " + lst)
    passRecord = True
    if(filterOpt == "default"):
        raise ValueError("Filter option required.")
    if(filterOpt == "bed"):
        if(param == "default"):
            raise ValueError("Bedfile req. for bed filter.")
        bedReader = open(param, 'r')
        bedEntries = [l.strip().split('\t') for l in bedReader.readlines()]
        chr, pos = inputVCFRec.CHROM, inputVCFRec.POS
        chrMatches = [ent for ent in bedEntries if ent[0] == chr]
        try:
            posMatches = [match for match in chrMatches if match[
                          2] + 1 >= pos and match[1] + 1 <= pos]
            if len(posMatches) >= 1 and passRecord is True:
                passRecord = True
            else:
                passRecord = False
        except ValueError:
            raise ValueError("Malformed bedfile.")
            # return False
    # Set param to int, where it is the minimum dissent reads
    if(filterOpt == "I16"):
        if(param == "default"):
            raise ValueError("Men# dissenting reads must be set.")
        if(inputVCFRec.InfoArrayDict['I16'][0] +
           inputVCFRec.InfoArrayDict['I16'][1] <
           inputVCFRec.InfoArrayDict['I16'][2] +
           inputVCFRec.InfoArrayDict['I16'][3]):
            if(inputVCFRec.InfoArrayDict['I16'][0] +
               inputVCFRec.InfoArrayDict['I16'][1] >= param):
                return True
            else:
                return False
        else:
            if(inputVCFRec.InfoArrayDict['I16'][2] +
               inputVCFRec.InfoArrayDict['I16'][3] >= param):
                return True
            else:
                return False
    return passRecord
