#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  starlist_check.py
#  pyobserver
#
#  Created by Alexander Rudy on 2014-07-18.
#  Copyright 2014 Alexander Rudy. All rights reserved.
#

import sys
import os, os.path
import argparse
import six
from pyobserver.starlist import (
    read_skip_comments, verify_starlist_line, parse_starlist_line
    )


if __name__ == '__main__':
    
    parser = argparse.ArgumentParser(description="Check a Keck format starlist for errors.")
    parser.add_argument("starlist", type=six.text_type)
    opt = parser.parse_args()
    
    print("Parsing starlist...")
    for line_no, target_line in enumerate(read_skip_comments(opt.starlist)):
        verify_starlist_line(target_line, "'{0}' line {1:d}".format(os.path.basename(opt.starlist), line_no))
        print(parse_starlist_line(target_line))