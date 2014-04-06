# -*- coding: utf-8 -*-
# 
#  cli.py
#  pyobserver
#  
#  Created by Alexander Rudy on 2014-04-05.
#  Copyright 2014 Alexander Rudy. All rights reserved.
# 

from __future__ import (absolute_import, unicode_literals, division, print_function)

import six
import abc
import subprocess
import os, os.path

from pyshell.subcommand import SCController, SCEngine
import pyshell.loggers
from pyshell import PYSHELL_LOGGING_STREAM_ALL
from astropy.time import Time
from astropy.coordinates import ICRS

from pyobserver.visibility import VisibilityPlot, Observatory, Target
from pyobserver.starlist import read_skip_comments

def _ll(value=0):
    """Return the logging level."""
    return pyshell.loggers.INFO - value

@six.add_metaclass(abc.ABCMeta)
class VisibilityCLI(SCEngine):
    """A base class for command line interfaces using pyshell for observing plots."""
    
    supercfg = [ PYSHELL_LOGGING_STREAM_ALL ]
    
    def init(self):
        """Setup basic arguments for this command."""
        self.parser.add_argument("-d","--date", help="Date before night, as parsed by Astropy.", default=Time.now())
        self.parser.add_argument("-o","--output", type=six.text_type, help="Output filename.")
        self.parser.add_argument("-O","--observatory", type=six.text_type, help="Observatory Name", default="Mauna Kea")
        self.parser.add_argument("--show", action="store_true", help="Show, don't save.")
        self.parser.add_argument("-v","--verbose", action='count', help="Verbosity", default=0)
        
    def do(self):
        """Show a visibility plot! With certain abstract parent methods."""
        self.set_date()
        self.log.log(_ll(1), self.opts.date)
        self.set_filename()
        self.log.log(_ll(2), "Saving file to '{}'".format(self.opts.output))
        self.set_observatory()
        self.log.log(_ll(1), self.opts.observatory)
        
        self.log.log(_ll(3), "Importing 'matplotlib.pyplot'")
        import matplotlib.pyplot as plt
        
        self.log.log(_ll(3), "Setting up figure and axes")
        fig = plt.figure()
        bbox = (0.1, 0.1, 0.65, 0.8) # l, b, w, h
        v_ax = fig.add_axes(bbox)
        
        self.log.log(_ll(3), "Building visibility plotter")
        v_plotter = VisibilityPlot(self.opts.observatory, self.opts.date)
        self.log.log(_ll(2), v_plotter.night)
        self.set_targets(v_plotter)
        
        self.log.log(_ll(3), "Creating plot...")
        
        show_progress = (len(v_plotter.targets) > 3) and (self.opts.verbose > 1)
        v_plotter(v_ax, output = show_progress)
        if show_progress:
            print("\n")
        
        self.log.log(_ll(3), "Outputting plot...")
        if self.opts.show:
            plt.show()
        else:
            fig.savefig(self.opts.output)
            self.log.log(_ll(3), "Opening plot...")
            subprocess.call(["open", self.opts.output])
        
        
        
    def after_configure(self):
        """Setup verbosity/logger."""
        self.log.setLevel(_ll(self.opts.verbose))
        self.init_positional()
        
    def set_date(self):
        """Set the date from command-line arguments."""
        self.opts.date =  Time(self.opts.date, scale='utc')
        
    def set_filename(self):
        """Set the filename from command-line arguments."""
        if not self.opts.output:
            self.opts.output = "visibility_{0.datetime:%Y%m%d}.pdf".format(self.opts.date)
            
    def set_observatory(self):
        """Setup the observatory object."""
        self.opts.observatory = Observatory.from_name(self.opts.observatory)
        

    
class StarlistVisibility(VisibilityCLI):
    """A class for plotting the visibility of a starlist."""
    
    description = "Create a visibility plot for the contents of a Keck-format starlist."
    
    command = "starlist"
    
    def init_positional(self):
        """Setup positional arguments"""
        self.parser.add_argument("starlist", type=six.text_type, help="Starlist Filename")
        
    def set_targets(self, v_plotter):
        """Setup targets"""
        for target_line in read_skip_comments(self.opts.starlist):
            t = Target.from_starlist(target_line)
            self.log.log(_ll(2), t)
            v_plotter.add(t)
            
    def set_filename(self):
        """Set the filename from command-line arguments."""
        if not self.opts.output:
            basename = os.path.splitext(os.path.basename(self.opts.starlist))[0]
            self.opts.output = "visibility_{1:s}_{0.datetime:%Y%m%d}.pdf".format(self.opts.date, basename)
    
            
class TargetVisibility(VisibilityCLI):
    """A visibility plotter for a single target."""
    
    description = "Create a visibility plot for a single target, resolved by SIMBAD."
    
    command = "target"
    
    def init_positional(self):
        """Setup positional arguments"""
        self.parser.add_argument("target", type=six.text_type, help="Object name as resolved by SIMBAD")
    
    def set_filename(self):
        """Set the filename from command-line arguments."""
        if not self.opts.output:
            self.opts.output = "visibility_{1:s}_{0.datetime:%Y%m%d}.pdf".format(self.opts.date, self.opts.target)
    
    def set_targets(self, v_plotter):
        """Setup the single target."""
        t = Target(name=self.opts.target, position=ICRS.from_name(self.opts.target))
        self.log.log(_ll(2), t)
        v_plotter.add(t)
        
class VIScommand(SCController):
    
    description = "Visibility Plotters."
    
    defaultcfg = False
    
    _subparsers_help = "Available Commands:"
    
    subEngines = [
        TargetVisibility,
        StarlistVisibility
    ]