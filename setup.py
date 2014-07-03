#!/usr/bin/env python
from FileExporter.version import VERSION
from distutils.core import setup
import os
import os.path
import sys
from glob import glob


#########################################################################

setup(name="fes",
      version=VERSION,
      description="File Export Service",
      author="Chris Powell",
      author_email="powellchristoph@gmail.com",
      package_dir={'FileExporter': 'FileExporter'},
      packages=["FileExporter"],
      data_files=[
                  ('/opt/fes', glob("fes.py")),
                  ('/etc/init.d/', glob("fes")),
                  ('/opt/fes', glob("fes.conf"))
            ],
      license="GPL v2",
      long_description="""
fes is a simple program that exports files to a location via file move or FTP/SFTP.
      """
      )
