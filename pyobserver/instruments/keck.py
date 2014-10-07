# -*- coding: utf-8 -*-
# 
#  keck.py
#  pyobserver
#  
#  Created by Alexander Rudy on 2014-03-31.
#  Copyright 2014 University of California. All rights reserved.
# 

from __future__ import (absolute_import, unicode_literals, division, print_function)

import numpy as np
import re
import astropy.time
import datetime

class Semester(object):
    """A single observing semester."""
    def __init__(self, name):
        super(Semester, self).__init__()
        self._parse_name(name)
    
    def __repr__(self):
        """Represent this semester."""
        return "<{0.__class__.__name__} '{0.name}' from {0.start} to {0.end}>".format(self)
    
    def _parse_name(self, name):
        """Parse the name of this semester."""
        name_re = re.compile(r"([0-9]{4})([AB])")
        name_match = name_re.match(name)
        if not name_match:
            raise ValueError("Can't parse name: '{0}'".format(name))
        year = int(name_match.group(1))
        semester = name_match.group(2)
        
        if semester == "A":
            self.start = astropy.time.Time(datetime.datetime(year, 2, 1), scale='utc')
            self.end = astropy.time.Time(datetime.datetime(year, 7, 31), scale='utc')
        elif semester == "B":
            self.start = astropy.time.Time(datetime.datetime(year, 8, 1), scale='utc')
            self.end = astropy.time.Time(datetime.datetime(year+1, 1, 31), scale='utc')
            
        self.name = name
        
    def __contains__(self, value):
        """Determine if the time is in this semester."""
        try:
            return (astropy.time.Time(value) >= self.start) and (astropy.time.Time(value) <= self.end)
        except Exception as e:
            return (value >= self.start) and (value <= self.end)
        
    