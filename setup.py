# -*- coding: utf-8 -*-
# 
#  setup.py
#  pyobserver
#  
#  Created by Alexander Rudy on 2013-04-19.
#  Copyright 2012 Alexander Rudy. All rights reserved.
# 

try:
    import setuptools
except ImportError:
    from distribute_setup import use_setuptools
    use_setuptools()

from setuptools import setup, find_packages

from pyobserver import version

setup(
    name = "pyobserver",
    version = version,
    packages = find_packages(exclude=['tests']),
    package_data = {'pyobserver': ['pyobserver/data/*']},
    install_requires = ['distribute','astropy>=0.2','pyshell>=0.3.0','pyds9==1.6'],
    dependency_links = [
        'https://github.com/alexrudy/pyshell/archive/0.3.0.tar.gz#egg=pyshell-0.3.0',
        'http://hea-www.harvard.edu/RD/download/pyds9/pyds9-1.6.tar.gz#egg=pyds9-1.6'
    ],
    author = "Alexander Rudy",
    author_email = "arrudy@ucsc.edu",
    entry_points = {
        'console_scripts' : [
            "PO = pyobserver.cli:POcommand.script"
        ],
    },
    )