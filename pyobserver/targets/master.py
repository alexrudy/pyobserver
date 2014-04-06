# -*- coding: utf-8 -*-
# 
#  master.py
#  pyobserver
#  
#  Created by Alexander Rudy on 2014-03-04.
#  Copyright 2014 University of California. All rights reserved.
# 

from __future__ import (absolute_import, unicode_literals, division,
                        print_function)


from .core import DataBase
from .columns.coordinates import ICRSPositionMixin
from sqlalchemy import Column, Integer, Float, Unicode

class MasterTarget(DataBase, ICRSPositionMixin):
    """A master target object."""
    
    name = Column(Unicode(100))
    redshift = Column(Float)
    
    def __repr__(self):
        """A useful representation here."""
        return "<{0:s} name='{1:s}', z={2:.4f} @ {3}>".format(
        self.__class__.__name__, self.name, self.redshift, self.position
        )