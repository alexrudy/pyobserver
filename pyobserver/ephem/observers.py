# -*- coding: utf-8 -*-
# 
#  observers.py
#  pyobserver
#  
#  Created by Alexander Rudy on 2014-03-03.
#  Copyright 2014 Alexander Rudy. All rights reserved.
# 

from __future__ import (absolute_import, unicode_literals, division,
                        print_function)

import ephem

import astropy.units as u
from astropy.coordinates import ICRS, FK5, AltAz
from astropy.time import Time

from .types import convert, AttributeConverter, WrappedUnitAttribute, CelciusAttribute

class Observer(AttributeConverter):
    """Make an observer."""
    
    __wrapped_class__ = ephem.Observer
    
    def __init__(self, **kwargs):
        super(Observer, self).__init__()
        for keyword, value in kwargs.items():
            setattr(self, keyword, value)
    
    elevation = WrappedUnitAttribute("elevation", u.m)
    
    temp = CelciusAttribute("temp")
    
    pressure = WrappedUnitAttribute("pressure", 1e-3 * u.bar)
    

