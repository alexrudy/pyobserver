# -*- coding: utf-8 -*-
# 
#  ned.py
#  pyobserver
#  
#  Created by Alexander Rudy on 2014-03-04.
#  Copyright 2014 University of California. All rights reserved.
# 

from __future__ import (absolute_import, unicode_literals, division,
                        print_function)



import astropy.units as u
from .core import SubDataBase
from .columns.coordinates import ICRSPositionMixin
from sqlalchemy import Column, Integer, Float, Unicode


class NEDData(SubDataBase):
    """Data from the NED"""
    
    __abstract__ = True
    

class NED_Primary_Data(NEDData, ICRSPositionMixin):
    """Primary lookup data from NED."""
    
    name = Column(Unicode(100))
    redshift = Column(Float)
    
    @classmethod
    def from_NED_row(cls, row, **kwargs):
        """Build a new object from a NED table row."""
        kwargs['name'] = row["Object Name"]
        kwargs['ra'] = row["RA(deg)"] * u.degree
        kwargs['dec'] = row["DEC(deg)"] * u.degree
        kwargs['redshift'] = row["Redshift"]
    