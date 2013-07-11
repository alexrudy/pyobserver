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
        
    def start(self):
        """Set up all of the details for the airmass plot."""
        if self.opts.date == "<<TODAY>>":
            self.date = date.today()
        else:
            self.date = datetime.strptime(self.opts.date,"%Y/%m/%d")
        filename,ext = os.path.splitext(self.opts.plot)
        self.filename = filename + self.date.strftime("%Y-%m-%d") + ext
        from . import observer
        self.site = observer.Observer(self.config.get("Site"))
        
    def do(self):
        """Make the airmass plot"""
        from . import observer
        self.targets = parse_starlist(self.opts.starlist)
        for star in self.targets:
            star["target"] = self.site.target(star["name"],star["ra"],star["dec"],star["epoch"])
        self.site.almanac(self.date.strftime("%Y/%m/%d"))
        self.site.airmass(*tuple([ star["target"] for star in self.targets ]))
        observer.plots.plot_airmass(self.site,self.filename,**self.pltparams)
        
    def end(self):
        """docstring for end"""
        pass
    