# -*- coding: utf-8 -*-
# 
#  setup.py
#  pyobserver
#  
#  Created by Alexander Rudy on 2013-04-19.
#  Copyright 2012 Alexander Rudy. All rights reserved.
# 

import sys

try:
    import setuptools
except ImportError:
    from distribute_setup import use_setuptools
    use_setuptools()
from setuptools import setup, find_packages

from distutils.extension import Extension
try:
    from Cython.Distutils import build_ext
except ImportError:
    print("Cython required!")
    sys.exit()

ext_modules = [ Extension("pyobserver.combine", ["pyobserver/combine.pyx"],
 include_dirs = ['/opt/local/Library/Frameworks/Python.framework/Versions/2.7/lib/python2.7/site-packages/numpy/core/include']
 ) ]

from pyobserver import version

setup(
    name = "pyobserver",
    version = version,
    packages = find_packages(exclude=['tests']),
    package_data = {'pyobserver': ['pyobserver/data/*']},
    install_requires = ['distribute','astropy>=0.2','pyshell','cython'],
    author = "Alexander Rudy",
    author_email = "arrudy@ucsc.edu",
    entry_points = {
        'console_scripts' : [
            "PO = pyobserver.cli:POcommand.script"
        ],
    },
    ext_modules = ext_modules,
    cmdclass = {'build_ext': build_ext},
    )