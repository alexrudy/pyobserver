#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 
#  parse_starlist.py
#  pyobserver
#  
#  Created by Alexander Rudy on 2014-03-12.
#  Copyright 2014 Alexander Rudy. All rights reserved.
# 

from __future__ import (absolute_import, unicode_literals, division, print_function)

from pyobserver.ephem import VisibilityPlot, Target, Observer
from pyobserver.util import read_skip_comments, parse_starlist, _starlist_re_raw

from pyshell.util import ipydb
ipydb()

import sys

import re

test_parts_A = [
    "PG_0844+349    ",
    "8 47 42.5  ",
    "+34 45 04.3    ",
    "2000 ",
    "lgs=1 skip=3"
]
test_parts_B = [
    "PG 0026+129      ",
    "00 29 13.7000  ",
    "13 16 03.720 ",
    "2000 ",
    "lgs=1 skip=3"
]
    

def test_parse_starlist_tokens(test_parts):
    """Test parsing a set of tokens from a starlist."""
    # The first line of the regular expression is blank.
    re_lines = _starlist_re_raw.splitlines()[1:]
    for regexp, test in zip(re_lines, test_parts):
        print("Matching\n  {!r}\nagainst\n  {!r}".format(regexp, test))
        match = re.compile(regexp, re.VERBOSE).match(test)
        if match:
            print("Success: {!r}".format(match.groupdict()))
        else:
            print("Failed to parse!")
        print("")

if __name__ == '__main__':
    if not len(sys.argv) == 2:
        test_parse_starlist_tokens(test_parts_A)
        test_parse_starlist_tokens(test_parts_B)
        sys.exit(0)
    
    filename = sys.argv[1]
    
    print("Parsing as PyEphem Targets...")
    for target_line in read_skip_comments(filename):
        print(Target.from_starlist(target_line))
     
    print("Parsing as data dictionaries...")   
    for data in parse_starlist(filename):
        print(data)