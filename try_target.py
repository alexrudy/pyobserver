#!/usr/bin/env /opt/local/Library/Frameworks/Python.framework/Versions/2.7/bin/python
# -*- coding: utf-8 -*-
# 
#  try_target.py
#  pyobserver
#  
#  Created by Alexander Rudy on 2014-03-03.
#  Copyright 2014 Alexander Rudy. All rights reserved.
# 

from __future__ import (absolute_import, unicode_literals, division,
                        print_function)

import os, os.path
if "VIRTUAL_ENV" in os.environ:
    activate_this = os.path.join(os.environ["VIRTUAL_ENV"],'bin/activate_this.py')
    execfile(activate_this, dict(__file__=activate_this))
    del activate_this


from pyobserver.ephem import VisibilityPlot, Target, Observer


import sys
import six

import astropy.units as u
from astropy.units import imperial
from astropy.coordinates import ICRS, Latitude, Longitude
from astropy.time import Time

from pyshell.util import ipydb
ipydb()

import matplotlib.pyplot as plt

if len(sys.argv) != 2:
    print("Usage: {} OBJECT_NAME ".format(sys.argv[0]))
    sys.exit(1)
target = six.text_type(sys.argv[1])

t = Target()
t.name = target
t.fixed_position = ICRS.from_name(target)

o = Observer(
    lat = Latitude("19 49 35.61788", u.degree),
    lon = Longitude("155 28 27.24268", u.degree))
with imperial.enable():
    o.elevation = 13646.92 * imperial.ft
v = VisibilityPlot(o, Time.now())
v.targets.add(t)
v(plt.gca())
t.compute(o)
print(t)
print(t.position)
print(t.altaz)
print(t.to_starlist())
plt.show()