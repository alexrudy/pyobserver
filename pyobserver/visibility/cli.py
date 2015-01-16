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
import re
import datetime

from pyshell.subcommand import SCController, SCEngine
import pyshell.loggers
from pyshell import PYSHELL_LOGGING_STREAM_ALL
from astropy.time import Time
from astropy.coordinates import SkyCoord
from astropy.coordinates.name_resolve import NameResolveError
import astropy.units as u
import numpy as np

from . import VisibilityPlot, Observatory, Target, Starlist
from ..starlist import read_skip_comments
from ..closures import parse_closures_list, FixedRegion

def _ll(value=0):
    """Return the logging level."""
    return pyshell.loggers.INFO - value

@six.add_metaclass(abc.ABCMeta)
class VisibilityCLI(SCEngine):
    """A base class for command line interfaces using pyshell for observing plots."""
    
    supercfg = PYSHELL_LOGGING_STREAM_ALL
        
    def do(self):
        """Show a visibility plot! With certain abstract parent methods."""
        self.log.setLevel(_ll(self.opts.verbose))
        self.set_date()
        self.log.log(_ll(1), self.opts.date)
        self.set_filename()
        self.log.log(_ll(2), "Saving file to '{}'".format(self.opts.output))
        self.set_observatory()
        self.log.log(_ll(1), self.opts.observatory)
        
        self.log.log(_ll(3), "Importing 'matplotlib.pyplot'")
        import matplotlib
        if self.opts.show:
            matplotlib.rcParams['text.usetex'] = False
        matplotlib.rcParams['axes.color_cycle'] = 'b, g, c, m, y'
        import matplotlib.pyplot as plt
        
        self.log.log(_ll(3), "Setting up figure and axes")
        fig = plt.figure(figsize=(10,9))
        bbox = (0.1, 0.1, 0.65, 0.8) # l, b, w, h
        v_ax = fig.add_axes(bbox)
        fig.canvas.set_window_title("PyVisibility")
        
        self.log.log(_ll(3), "Building visibility plotter")
        v_plotter = VisibilityPlot(self.opts.observatory, self.opts.date)
        self.log.log(_ll(2), v_plotter.night)
        self.set_targets(v_plotter)
        
        self.log.log(_ll(3), "Creating plot...")
        
        show_progress = (len(v_plotter.targets) > 3) and (self.opts.verbose > 1)
        v_plotter(v_ax, output = show_progress, min_elevation = self.opts.min_elevation)
        if show_progress:
            print("\n")
        
        self.log.log(_ll(3), "Outputting plot...")
        if self.opts.show:
            v_plotter.setup_pickers(v_ax)
            v_plotter.setup_clock(v_ax)
            plt.show()
        else:
            fig.savefig(self.opts.output)
            self.log.log(_ll(3), "Opening plot...")
            subprocess.call(["open", self.opts.output])
        
    def after_configure(self):
        """Setup verbosity/logger."""
        self.parser.add_argument("-d","--date", help="Date before night, as parsed by Astropy.", default=Time.now())
        self.parser.add_argument("-o","--output", type=six.text_type, help="Output filename.")
        self.parser.add_argument("-O","--observatory", type=six.text_type, help="Observatory Name", default="Mauna Kea")
        self.parser.add_argument("--show", action="store_true", help="Show, don't save.")
        self.parser.add_argument("-v","--verbose", action='count', help="Verbosity", default=0)
        self.parser.add_argument("--no-filter", dest='gsfilter', action='store_false', help="Don't filter out guide stars.")
        self.parser.add_argument("--include-psf", dest='psffilter', action='store_false', help="Don't fileter out PSF stars.")
        self.parser.add_argument("--min-elevation", help="Minimum elevation line.", type=float)
        self.init_positional()
        super(VisibilityCLI, self).after_configure()
        
    def set_date(self):
        """Set the date from command-line arguments."""
        try:
            self.opts.date =  Time(self.opts.date, scale='utc')
        except ValueError:
            self.parser.error("Can't parse '{}' as a date.".format(self.opts.date))
        
    def set_filename(self):
        """Set the filename from command-line arguments."""
        if not self.opts.output:
            self.opts.output = "visibility_{0.datetime:%Y%m%d}.pdf".format(self.opts.date)
            
    def set_observatory(self):
        """Setup the observatory object."""
        try:
            self.opts.observatory = Observatory.from_name(self.opts.observatory)
        except KeyError:
            from pyobserver.visibility.observatory import _observatories_data
            self.parser.error("Observatory '{!s}' does not exist.\nObservatories: {!r}".format(self.opts.observatory, list(_observatories_data.keys())))
            
    def filter_targets(self, plotter):
        """Filter the targets, if required."""
        if self.opts.psffilter:
            plotter.targets = filter(lambda target : not bool(getattr(target, 'psf', False)), plotter.targets)
        if self.opts.gsfilter:
            plotter.targets = list(plotter.filter_gs_targets())


class ClosureVisibility(VisibilityCLI):
    """A visibility plotter which uses a closure list"""
    
    description = "Create a visibility plot for the contents of a closure list."
    
    command = "closures"
    
    help = "Closures from a file."
    
    def init_positional(self):
        """Setup positional arguments"""
        self.parser.add_argument("--no-eng", dest='eng', action='store_false', help="Exclude engineering stars.")
        self.parser.add_argument("--starlist", dest='starlist', type=six.text_type, help="Starlist, used to limit chosen targets.")
        self.parser.add_argument("closures", type=six.text_type, help="Closure Filename")
    
    def set_date(self):
        """Set the date from command line arguments, or from the closure filename."""
        m = re.match(r"opens(?:Unix|Dos)(?P<date>[\d]{6})\.txt", self.opts.closures)
        if m:
            date = datetime.datetime.strptime(m.groupdict()['date'], "%y%m%d")
            self.opts.date = Time(date, scale='utc')
        else:
            super(ClosureVisibility, self).set_date()
    
    def set_targets(self, v_plotter):
        """Set the targets"""
        
        if not os.path.exists(self.opts.closures):
            self.parser.error("Closure file '{}' does not exist.".format(self.opts.closures))
            
        with open(self.opts.closures, 'r') as stream:
            for region in parse_closures_list(stream, self.opts.closures, date=self.opts):
                if not self.opts.eng and region.name[:3] == 'eng':
                    continue
                if isinstance(region, FixedRegion):
                    v_plotter.add(region)
        self.filter_targets(v_plotter)
        
    def filter_targets(self, plotter):
        """docstring for filter_targets"""
        sep = 2 * u.arcmin
        if hasattr(self.opts, 'starlist'):
            if not os.path.exists(self.opts.starlist):
                self.parser.error("Starlist file '{}' does not exist.".format(self.opts.starlist))
            sl = Starlist.from_starlist(self.opts.starlist)
            cl = sl.catalog()
            for target in list(plotter.targets):
                matches, sep2d, distances = target.fixed_position.match_to_catalog_sky(cl, nthneighbor=2)
                if not sum(1 for i in np.atleast_1d(matches)[sep2d <= sep]):
                    self.log.log(_ll(2),"Removing {}".format(target))
                    plotter.targets.remove(target)
                else:
                    self.log.log(_ll(2),"Keeping {}, matched to {}".format(target, sl[np.atleast_1d(matches)[0]]))
        super(ClosureVisibility, self).filter_targets(plotter)
    
    def set_filename(self):
        """Set the filename from command-line arguments."""
        if not self.opts.output:
            basename = os.path.splitext(os.path.basename(self.opts.closures))[0]
            self.opts.output = "visibility_{1:s}_{0.datetime:%Y%m%d}.pdf".format(self.opts.date, basename)

class StarlistVisibility(VisibilityCLI):
    """A class for plotting the visibility of a starlist."""
    
    description = "Create a visibility plot for the contents of a Keck-format starlist."
    
    command = "starlist"
    
    help = "Starlist from a file."
    
    def init_positional(self):
        """Setup positional arguments"""
        self.parser.add_argument("starlist", type=six.text_type, help="Starlist Filename")
        
    def set_targets(self, v_plotter):
        """Setup targets"""
        if not os.path.exists(self.opts.starlist):
            self.parser.error("Starlist '{}' does not exist.".format(self.opts.starlist))
        
        for target_line in read_skip_comments(self.opts.starlist):
            try:
                t = Target.from_starlist(target_line)
            except ValueError:
                self.parser.error("Can't parse line '{}' as starlist.".format(target_line))
            self.log.log(_ll(2), t)
            v_plotter.add(t)
        self.filter_targets(v_plotter)
            
    def set_filename(self):
        """Set the filename from command-line arguments."""
        if not self.opts.output:
            basename = os.path.splitext(os.path.basename(self.opts.starlist))[0]
            self.opts.output = "visibility_{1:s}_{0.datetime:%Y%m%d}.pdf".format(self.opts.date, basename)
            
    
            
class TargetVisibility(VisibilityCLI):
    """A visibility plotter for a single target."""
    
    description = "Create a visibility plot for a single target, resolved by SIMBAD."
    
    command = "target"
    
    help = "Single Target"
    
    def init_positional(self):
        """Setup positional arguments"""
        self.parser.add_argument("target", type=six.text_type, help="Object name as resolved by SIMBAD", nargs="+", default=[])
    
    def set_filename(self):
        """Set the filename from command-line arguments."""
        if not self.opts.output:
            self.opts.output = "visibility_{1:s}_{0.datetime:%Y%m%d}.pdf".format(self.opts.date, self.opts.target)
    
    def set_targets(self, v_plotter):
        """Setup the single target."""
        for tname in self.opts.target:
            try:
                t = Target(name=tname, position=SkyCoord.from_name(tname, frame='icrs'))
            except NameResolveError:
                self.parser.error("Can't parse/locate '{}' as a target.".format(tname))
            self.log.log(_ll(2), t)
            v_plotter.add(t)
        
        self.filter_targets(v_plotter)
        
class VIScommand(SCController):
    
    description = "Visibility Plotters."
    
    defaultcfg = "visibility.yml"
    
    _subparsers_help = "Available Commands:"
    
    subEngines = [
        TargetVisibility,
        StarlistVisibility,
        ClosureVisibility
    ]