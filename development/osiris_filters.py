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
    max_distance = 64 * p.to(u.pc)
    if max_distance >= 1 * u.kpc:
        max_distance = max_distance.to(u.kpc)
    px_distance = p.to(u.pc)
    if px_distance >= 1 * u.kpc:
        px_distance = px_distance.to(u.kpc)
    print("Pixels {0} = {1:.1f} out to {2:.1f} = {3:.1f}".format(a, px_distance, 64 * a, max_distance))