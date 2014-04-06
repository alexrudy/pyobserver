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
from pyobserver.starlist import read_skip_comments, parse_starlist, _starlist_re_raw, verify_starlist_line, parse_starlist_line

from pyshell.util import ipydb
ipydb()

import sys
import os, os.path

import re

test_parts_A = [
    "PG_0844+349    ",
    "8 47 42.5  ",
    "+34 45 04.3    ",
    "2000 ",
    "lgs=1 skip=3"
]
test_parts_B = [
    "PG 0026+129     ",
    "00 29 13.7000 ",
    "13 16 03.720 ",
    "2000 ",
    "lgs=1 skip=3"
]
test_parts_C = [
    "PG 0026+129      ",
    "00 29 13.7000  ",
    "13 16 03.720 ",
    "2000 ",
    "lgs=1 skip=3 bad==2=2 badkeyword"
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
        
def test_verify_starlist_tokens(test_parts):
    """Test the verification of starlist tokens."""
    
    print("Verifying Line:")
    print("".join(test_parts))
    verify_starlist_line("".join(test_parts))

if __name__ == '__main__':
    if not len(sys.argv) == 2:
        # test_parse_starlist_tokens(test_parts_A)
        test_verify_starlist_tokens(test_parts_A)
        # test_parse_starlist_tokens(test_parts_B)
        test_verify_starlist_tokens(test_parts_B)
        test_verify_starlist_tokens(test_parts_C)
        sys.exit(0)
    
    filename = sys.argv[1]
    
    print("Parsing starlist...")
    for line_no, target_line in enumerate(read_skip_comments(filename)):
        verify_starlist_line(target_line, "'{0}' line {1:d}".format(os.path.basename(filename), line_no))
        print(parse_starlist_line(target_line))
     