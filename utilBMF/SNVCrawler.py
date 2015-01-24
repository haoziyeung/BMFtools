#!/usr/bin/env python
import argparse
import os
import logging
import sys

from MawCluster.VCFWriters import SNVCrawler
from utilBMF.HTSUtils import printlog as pl

# Global Variables
Logger = logging.getLogger("Primarylogger")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--inBAM',
        '-i',
        help=(
            "Coordinate-sorted, indexed BAM")
        )
    parser.add_argument(
        "--bed",
        "-b",
        help="Full path to bed file.",
        default="default")
    parser.add_argument(
        "--minBQ",
        help="Minimum Base Quality to consider",
        default=30,
        type=int)
    parser.add_argument(
        "--minMQ",
        help="Minimum Mapping Quality to consider",
        default=10,
        type=int)
    parser.add_argument(
        "--MaxPValue",
        "-p",
        help="Maximum P value to consider, in e notation.",
        type=float,
        default=1e-15)
    parser.add_argument(
        "--keepConsensus",
        "-k",
        action="store_true")
    parser.add_argument(
        "--logfile",
        help="Name for logfile.",
        default="default")
    parser.add_argument(
        "-r",
        "--reference-fasta",
        help="Provide reference fasta.",
        required=True)
    args = parser.parse_args()
    commandStr = " ".join(sys.argv)

    # Begin logging
    global Logger
    if(args.logfile != "default"):
        logfile = args.logfile
    else:
        print("Basename for log: {}".format(os.path.basename(args.inBAM)))
        logfile = (os.getcwd() + "/" +
                   os.path.basename(args.inBAM).split('.')[0] +
                   '.bmf.vcf.log')
    if(os.path.isfile(logfile)):
        os.remove(logfile)
        pl("Log file existed - deleting!")

    # Logger which holds both console and file loggers
    Logger.setLevel(logging.DEBUG)

    # Console handler - outputs to console.
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    # create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # add formatter to ch
    ch.setFormatter(formatter)

    # add ch to logger
    Logger.addHandler(ch)

    # File logger - outputs to log file.
    fl = logging.FileHandler(filename=logfile)
    fl.setFormatter(formatter)
    fl.setLevel(logging.DEBUG)

    Logger.addHandler(fl)

    pl("Log file is {}".format(logfile))

    # Beckon the Kraken
    if(args.bed != "default"):
        OutVCF = SNVCrawler(args.inBAM,
                            bed=args.bed,
                            minMQ=args.minMQ,
                            minBQ=args.minBQ,
                            MaxPValue=args.MaxPValue,
                            keepConsensus=args.keepConsensus,
                            commandStr=commandStr,
                            reference=args.reference_fasta,
                            reference_is_path=True)
    else:
        OutVCF = SNVCrawler(args.inBAM,
                            minMQ=args.minMQ,
                            minBQ=args.minBQ,
                            MaxPValue=args.MaxPValue,
                            keepConsensus=args.keepConsensus,
                            commandStr=commandStr,
                            reference=args.reference_fasta,
                            reference_is_path=True)

    return OutVCF


if(__name__ == "__main__"):
    main()