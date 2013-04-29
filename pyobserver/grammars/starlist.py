# -*- coding: utf-8 -*-
# 
#  starlist.py
#  pynirc2
#  
#  Created by Alexander Rudy on 2012-12-22.
#  Copyright 2012 Alexander Rudy. All rights reserved.
# 

from __future__ import division
from modgrammar import (Grammar, L, WORD, OPTIONAL, OR, EOL, REPEAT, EMPTY, REST_OF_LINE)

class ObjectName(Grammar):
    grammar = (WORD("A-Za-z","A-Za-z0-9_\-"))
    
    @property
    def value(self):
        return self.string

class NUM(Grammar):
    grammar = (OPTIONAL((L("+") | L("-"))),WORD("0-9"),OPTIONAL((L("."),WORD("0-9"))))
    
    @property
    def value(self):
        return float(str(self))
