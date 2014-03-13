#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 
#  FHT_timing.py
#  pyobserver
#  
#  Created by Jaberwocky on 2013-07-18.
#  Copyright 2013 Jaberwocky. All rights reserved.
# 


import pyobserver.fitsfiles as pff
import re, glob

print("Loading...")
table = pff.FITSHeaderTable.fromfiles(glob.glob("*.fits"))
print("Searching...")
result = table.search(OBJECT=re.compile(r"[Cc]rab"))
print("Found {:d} files".format(len(result)))