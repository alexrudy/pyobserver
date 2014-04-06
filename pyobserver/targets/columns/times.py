# -*- coding: utf-8 -*-
# 
#  times.py
#  pyobserver
#  
#  Created by Alexander Rudy on 2014-03-04.
#  Copyright 2014 University of California. All rights reserved.
# 

from __future__ import (absolute_import, unicode_literals, division,
                        print_function)


import sqlalchemy.types as types
from astropy.time import Time
import astropy.units as u

class TimeType(types.TypeDecorator):
    """A type for handling the input and output of astropy Time."""
    
    impl = types.DateTime
    
    python_type = Time
    
    def process_bind_param(self, value, dialect):
        """Bind the Time to this parameter."""
        return value.datetime
        
    def process_return_value(self, value, dialect):
        """Return the Time object constructed from the database."""
        return self.python_type(value, scale='utc')