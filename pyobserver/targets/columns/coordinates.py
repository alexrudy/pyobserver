# -*- coding: utf-8 -*-
# 
#  coordinates.py
#  pyobserver
#  
#  Created by Alexander Rudy on 2014-03-04.
#  Copyright 2014 University of California. All rights reserved.
# 

from __future__ import (absolute_import, unicode_literals, division,
                        print_function)


from sqlalchemy import Column
import astropy.units as u
from astropy.coordinates import Angle, ICRS
from .quantity import QuantityType
        
class AngleType(QuantityType):
    """A type for handling the input and output of astropy angles."""
    
    unit = u.degree
    
    python_type = Angle
    
class ICRSPositionMixin(object):
    """A mixin class for adding an IRCS Position object to a SQLAlchemy ORM"""
    
    dec = Column(AngleType)
    ra = Column(AngleType)
    
    @property
    def position(self):
        """Return the position as an IRCS position"""
        return ICRS(dec=self.dec, ra=self.ra)
        
    @position.setter
    def position(self, value):
        """Set the postion."""
        ra, dec = value.ra, value.dec # Extract the angles.
        # Set the angles in a second statement to prevent 
        # an error setting the angles only partially.
        self.ra, self.dec = ra, dec
        
    
    