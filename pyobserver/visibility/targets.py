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
from ..starlist import parse_starlist_line, read_skip_comments

class Target(FixedBody):
    """A subclass of FixedBody with a starlist interface."""
    
    @classmethod
    def from_starlist(cls, text):
        """Produce a fixed-body item from a starlist."""
        data = parse_starlist_line(text)
        for key in data:
            data[key.lower()] = data.pop(key)
        return cls(**data)
    
def parse_starlist_targets(starlist):
    """Parse a starlist into targets."""
    for line in read_skip_comments(starlist):
        yield Target.from_starlist(line)