# -*- coding: utf-8 -*-
# 
#  setup.py
#  pyobserver
#  
#  Created by Alexander Rudy on 2013-04-19.
#  Copyright 2012 Alexander Rudy. All rights reserved.
# 


from setuptools import setup, find_packages

setup(
    name = "pyobserver",
    version = "0.3.0",
    packages = find_packages(exclude=['tests']),
    package_data = {'pyobserver': ['pyobserver/data/*']},
    author = "Alexander Rudy",
    author_email = "arrudy@ucsc.edu",
    install_requires = [
        # 'numpy>=1.8.0',
        # 'matplotlib>=1.3.0',
        'Jinja2>=2.7.2',
        'PyYAML>=3.10',
        'astropy>=0.3',
        'numpy>=1.8.0',
        'six>=1.5.2',
        # 'pyds9>=1.6',
        'pyshell==1.0-dev',
        'astropyephem>=0.1.1',
    ],
    dependency_links = [
        'http://hea-www.harvard.edu/RD/download/pyds9/pyds9-1.6.tar.gz#egg=pyds9-1.6',
        'git+https://github.com/alexrudy/pyshell.git@develop#egg=pyshell-1.0-dev',
        'git+https://github.com/alexrudy/astropyephem.git@v0.1.1#egg=astropyephem-0.1.1',
    ],
    entry_points = {
        'console_scripts' : [
            "PO = pyobserver.fits.cli:POcommand.script",
            "PyVisibility = pyobserver.visibility.cli:VIScommand.script"
        ],
    },
    )