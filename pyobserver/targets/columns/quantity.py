# -*- coding: utf-8 -*-
# 
#  quantity.py
#  pyobserver
#  
#  Created by Alexander Rudy on 2014-03-04.
#  Copyright 2014 University of California. All rights reserved.
# 

from __future__ import (absolute_import, unicode_literals, division,
                        print_function)


import sqlalchemy.types as types
import astropy.units as u

class QuantityType(types.TypeDecorator):
    """A type for handling the input and output of astropy quantities."""
    
    impl = types.Float
    
    unit = u.dimensionless_unscaled
    
    python_type = u.Quantity
    
    def serialize(self, value):
        """Prepare a value for serialization."""
        return value.to(self.unit).value
        
    def deserialize(self, value):
        """Retrieve a value from its serialized form."""
        return self.python_type(value, unit=self.unit)
    
    def process_bind_param(self, value, dialect):
        """Bind the angle to this parameter."""
        return value.to(self.unit).value
        
    def process_result_value(self, value, dialect):
        """Return the angle object constructed from the database."""
        return self.python_type(value, unit=self.unit)