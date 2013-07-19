# -*- coding: utf-8 -*-
# 
#  airmass.py
#  pynirc2
#  
#  Created by Alexander Rudy on 2012-12-22.
#  Copyright 2012 Alexander Rudy. All rights reserved.
# 

from pyshell.subcommand import SCEngine
from datetime import date, datetime
import os.path

from .util import parse_starlist

class AirmassChart(SCEngine):
    """Display target airmass charts"""
    pltparams = {}
    
    def __init__(self, command = "airmass"):
        super(AirmassChart, self).__init__(command=command)
        
    def configure(self):
        super(AirmassChart, self).configure()
        self.parser.add_argument('starlist',help="stalist file name.",action='store',default=self.config["Defaults.Starlist"])
        self.parser.add_argument('--plot',help="make airmass plot",action='store',default="airmass.pdf")
        self.parser.add_argument('--date',help="set airmass date",action='store',default="<<TODAY>>",metavar="YYYY/MM/DD")
        
    def do(self):
        """Make the airmass plot"""
        self.targets = parse_starlist(self.opts.starlist)
        if self.opts.date == "<<TODAY>>":
            self.date = date.today()
        else:
            self.date = datetime.strptime(self.opts.date,"%Y/%m/%d")
        
        
    def end(self):
        """docstring for end"""
        pass
    