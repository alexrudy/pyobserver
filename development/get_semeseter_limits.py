#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 
#  get_semeseter_limits.py
#  pyobserver
#  
#  Created by Alexander Rudy on 2014-03-06.
#  Copyright 2014 University of California. All rights reserved.
# 


from __future__ import (absolute_import, unicode_literals, division,
                        print_function)

from pyshell.util import ipydb
from pyobserver.ephem.observers import get_observatory
from pyobserver.ephem import Sun
import astropy.time
import astropy.units as u
ipydb()
K2O = get_observatory("Keck II")
K2O.date = astropy.time.Time("2014-08-01", scale='utc')
K2O.date = K2O.next_setting(Sun())
print(K2O)
print("Semester 2014B Start:")
print(K2O.date.iso)
print(K2O.sidereal_time().to_string(u.hourangle, sep="hms"))

K2O.date = astropy.time.Time("2014-10-15", scale='utc')
K2O.date = K2O.next_antitransit(Sun())
sun = Sun()
sun.compute(K2O)
print(sun.altaz)
print("Semester 2014B Middle:")
print(K2O.date.iso)
print(K2O.sidereal_time().to_string(u.hourangle, sep="hms"))

K2O.date = astropy.time.Time("2015-02-01", scale='utc')
K2O.date = K2O.previous_setting(Sun())
print("Semester 2014B End:")
print(K2O.date.iso)
print(K2O.sidereal_time().to_string(u.hourangle, sep="hms"))