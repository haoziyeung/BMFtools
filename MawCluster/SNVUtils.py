import subprocess

from MawCluster.PileupUtils import *

"""
This module contains a variety of tools for calling variants.
Currently, it primarily works with SNPs primarily with experimental
features present for structural variants
TODO: Filter based on variants supported by reads going both ways.
TODO: Make calls for SNPs, not just reporting frequencies.
"""


def SNVCrawler(inBAM,
               bedfile="default",
               ):
    if(isinstance(bedfile, str)):
        bedfile = HTSUtils.ParseBed(bedfile)
        
    return None