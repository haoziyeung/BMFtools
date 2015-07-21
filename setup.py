import numpy as np
import operator
import os
import os.path
import pysam
import shlex
import subprocess
import sys
from itertools import chain
from Cython.Build import cythonize
# from setuptools import setup
from distutils.core import setup

marchFlag = "-march=native"

compilerList = ["-O2", "-pipe", marchFlag, "-mfpmath=sse", "-std=c99", "-DSAMTOOLS=1",
                "-Wno-error=declaration-after-statement"]

"""
compilerList = ["-O3", "-pipe", marchFlag, "-funroll-loops", "-floop-block",
                "-fvariable-expansion-in-unroller", "-fsplit-ivs-in-unroller",
                "-fivopts", "-ftree-loop-im", "-floop-nest-optimize",
                "-fprefetch-loop-arrays", "-floop-strip-mine", "-flto"]
compilerList = ["-O3", "-pipe", marchFlag, "-funroll-loops", "-floop-block",
print("Removing all .c files - this is "
      "important for making sure things get rebuilt."
      "Especially if you're using -flto")
subprocess.check_call(shlex.split("find . -name \"*.c\" -exec rm \{\} \\;"))

compilerList = ["-O3", "-pipe", marchFlag, "-funroll-loops", "-floop-block",
                "-fvariable-expansion-in-unroller", "-fsplit-ivs-in-unroller",
                "-fivopts", "-ftree-loop-im",
                "-fprefetch-loop-arrays", "-floop-strip-mine"]
"""

compilerList = ["-O3", "-pipe", marchFlag, "-mfpmath=sse", "-funroll-loops"]


ext = list(chain.from_iterable(map(cythonize, ['*/*.pyx', '*/*.py'])))

# If more complex optimizations fail, fall back to -O2
for x in ext:
    if(x.name in ['MawCluster.BCFastq', 'utilBMF.MPA', 'MawCluster.BCBam']):
        x.sources += ["include/cephes/igam.c", "include/cephes/const.c",
                      "include/cephes/gamma.c", "include/cephes/mtherr.c",
                      "include/cephes/sf_error.c"]
    if(x.name == "MawCluster.BCBam"):
        x.libraries.append("z")
    x.extra_compile_args += compilerList
    x.define_macros += [('_FILE_OFFSET_BITS', '64'),
                        ('_USE_KNETFILE', ''),
                        ('PATH_MAX', '1024')]

install_requires = ['pysam>=0.8.2', 'cytoolz', 'matplotlib', 'cython>=0.22',
                    'cutadapt>=1.5', 'lxml', 'scipy', 'entropy', 'statsmodels',
                    're2']

includes = [np.get_include(), os.path.abspath("include"), os.path.abspath("include/cephes"),
            "include/htslib/"] + pysam.get_include()

config = {
    'description': '',
    'author': 'Daniel Baker',
    'url': 'https://github.com/ARUP-NGS/BMFTools',
    'author_email': 'daniel.baker@aruplab.com',
    'version': '0.1.1alpha',
    'packages': ["BMFMain", "utilBMF", "MawCluster",
                 "SecC", "analyscripts"],
    'install_requires': ['pysam', 'biopython', 'cytoolz', 'matplotlib',
                         'cython', 'cutadapt', 'lxml', 'scipy', 'entropy'],
    'packages': ['BMFMain', 'utilBMF', 'MawCluster', 'SecC'],
    'ext_modules': ext,
    'include_dirs': includes,
    'scripts': ['utilBMF/bmftools', 'include/dnbtools'],
    'name': 'BMFTools',
    'license': 'GNU Affero General Public License, '
               'pending institutional approval',
    'include': 'README.md',
    'package_data': {'': ['README.md']}
}


setup(**config)

print("Installation successful!")

sys.exit(0)
