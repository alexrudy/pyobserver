# -*- coding: utf-8 -*-
# 
#  astropy_table.py
#  pyobserver
#  
#  Created by Alexander Rudy on 2014-03-04.
#  Copyright 2014 University of California. All rights reserved.
# 
"""
Load data from an AstroPy Table
-------------------------------
"""

from __future__ import (absolute_import, unicode_literals, division,
                        print_function)

import astropy.table

def to_table(query_set):
    """Create an astropy table from a query set."""
    if hasattr(query_set, 'all'):
        items = query_set.all()
    else:
        items = query_set
    return astropy.table.Table([ item.as_serializable_dictionary() for item in items ])
    
def from_table(table, model):
    """Return a list of elements from a table."""
    colnames = table.colnames
    return [ model.from_serializeable_dictionary({ name:row[name] for name in colnames }) for row in table ]
        