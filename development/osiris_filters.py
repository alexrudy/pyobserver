#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 
#  osiris_filters.py
#  pyobserver
#  
#  Created by Alexander Rudy on 2014-03-06.
#  Copyright 2014 Alexander Rudy. All rights reserved.
# 

from __future__ import (absolute_import, unicode_literals, division, print_function)

import numpy as np
import astropy.table
import astropy.units as u
from pyobserver.instruments.osiris import osiris_scales_at_redshift

physical, angular = osiris_scales_at_redshift(0.1)

for p,a in zip(physical, angular):
    print("Pixels {0} = {1:.1f} out to {2:.1f} {3:.1f}".format(a, p.to(u.pc), 64 * a, 64 * p.to(u.pc)))