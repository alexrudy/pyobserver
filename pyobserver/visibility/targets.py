# -*- coding: utf-8 -*-
# 
#  targets.py
#  pyobserver
#  
#  Created by Alexander Rudy on 2014-03-23.
#  Copyright 2014 Alexander Rudy. All rights reserved.
# 

from __future__ import (absolute_import, unicode_literals, division, print_function)


from astropyephem import FixedBody
from ..starlist import parse_starlist_line

def from_starlist(cls, text):
    """Produce a fixed-body item from a starlist."""
    data = parse_starlist_line(text)
    for key in data:
        data[key.lower()] = data.pop(key)
    return cls(position = data['position'], name = data['name'])
    
FixedBody.from_starlist = classmethod(from_starlist)