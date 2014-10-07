# -*- coding: utf-8 -*-
# 
#  cli.py
#  pyobserver
#  
#  Created by Alexander Rudy on 2013-04-19.
#  Copyright 2013 Alexander Rudy. All rights reserved.
# 

from __future__ import (absolute_import, unicode_literals, division,
                        print_function)

import os, os.path, glob, sys
import shlex
import re, ast
import warnings, logging
import datetime
import collections
from textwrap import fill
import six

import numpy as np

from pyshell.subcommand import SCController, SCEngine
from pyshell.util import query_yes_no, force_dir_path, collapseuser, check_exists, deprecatedmethod, query_string, query_select

from astropy.coordinates import ICRS
import astropy.units as u
from astropy.io import fits

from .core import FITSHeaderTable, readfilelist
from ..starlist import StarlistToRegion

class FITSCLI(SCEngine):
    """A base class for command line interfaces using pyshell."""
    
    options = []
    
    def after_configure(self):
        """Configure the logging"""
        super(FITSCLI, self).after_configure()
        # Input settings
        if "i" in self.options:
            self.parser.add_argument('-i','--input',help="Either a glob or a list contianing the files to use.",
                action='store',nargs="+",type=unicode,default=unicode(self.config.get("Defaults.Files.Input","*.fits")))
        
        if "s" in self.options:
            self.parser.add_argument('-s','--single',help="Use only the first found file.",
                action='store_true')
        
        # Output settings:
        if "ol" in self.options:
            self.parser.add_argument('-o','--output',help="Output file name",
                default=self.config.get("Defaults.Files.OutputLog",False),action='store',dest='output')
            self.opts.log = True
        
        if "oi" in self.options or "oil" in self.options:
            self.parser.add_argument('-o','--output',action='store',
                default=self.config.get("Defaults.Files.OutputList",False),help="Output list file name.",metavar="files.list")
        
        if "oil" in self.options:
            self.parser.add_argument('-l','--log',action='store_true',
                help="Store a full log file, not just a list of files that match this keyword.")
        elif "oi" in self.options:
            self.opts.log = False
        
        # Search settings:
        if "skw" in self.options:
            self.parser.add_argument('--re',action='store_true',
                help="Use regular expressions to parse header values.")
            self.parser.add_argument('keywords',nargs="*",action='store',
                help="File Header search keywords. 'KWD' is the FITS header keyword to seach for, and 'value' is the search value. See `--re` to use 'value' as a regular expression.",metavar='KWD=value')
        if "gkw" in self.options:
            self.parser.add_argument('keywords',nargs="*",help="Keywords to group.",action='store',default=self.config.get("Log.Keywords"))
                
            
        
    
    def get_files(self):
        """Get the list of files used by the -i command line argument."""
        from pyshell.util import check_exists, warn_exists
        if not hasattr(self.opts,'input'):
            raise AttributeError("Missing input option!")
        if not isinstance(self.opts.input,list):
            inputs = [ self.opts.input ]
        else:
            inputs = self.opts.input
        files = []
        for _input in inputs:
            if check_exists(_input) and not (_input.endswith(".fit") or _input.endswith(".fits") or _input.endswith("fits.gz")):
                files += readfilelist(_input)
            else:
                infiles = shlex.split(_input)
                for infile in infiles:
                    files += glob.glob(infile)
        for _file in files:
            warn_exists(_file, "FITS File", True)
        
        if getattr(self.opts, 'single', False):
            files = [files[0]]
        
        return files
    
    def get_keywords(self):
        """Get the dictionaries for search keywords"""
        search = collections.OrderedDict()
        for pair in self.opts.keywords:
            if len(pair.split("=",1)) == 2:
                key,value = pair.split("=",1)
                if self.opts.re:
                    value = re.compile(value)
                else:
                    try:
                        value = ast.literal_eval(value)
                    except:
                        value = value
            elif len(pair.split("=")) == 1:
                key,value = pair,True
            else:
                self.parser.error("Argument for Malformed Keyword Pair: '%s'" % pair)
            search[key] = value
        return search
    
    def get_ds9(self, target=None):
        """Open DS9"""
        target = self.__class__.__name__ if target is None else target
        try:
            import ds9 as pyds9
            ds9 = pyds9.ds9(target=target)
        except ImportError:
            raise
        except Exception:
            self.log.critical("Can't get to DS9! Try closing all open DS9 windows...")
            raise
        return ds9
    
    def output_table(self, table, more=None, less=None, verb="found"):
        """Output a table to the command line.
        
        :param table: The astropy.table.Table
        :param bool more: Whether to use Table.more() for streming output.
        :param bool less: Whether to stream to the unix ``less`` command.
        :param string verb: The verb to use for end-user output.
        
        """
        if more is None:
            more = self.config.get("UI.Table.more", False)
        if less is None:
            less = self.config.get("UI.Table.less", False)
        log = getattr(self.opts,'log',False)
        output = getattr(self.opts,'output',False)
        
        if not log:
            include = [ table.colnames[0] ]
            _format = 'ascii.fixed_width_no_header'
        else:
            include = table.colnames
            _format = 'ascii.fixed_width'
        
        if output:
            table.write(output, format=_format, bookend=False, delimiter=None, include_names=include)
            print("Wrote file {:s} to '{:s}'".format("log" if log else "list", output))
        elif less:
            from ..util import stream_less
            writer = lambda stream : table.write(stream, format=_format, bookend=False, delimiter=None, include_names=include)
            stream_less(writer)
            print("{size:d} files {verb:s}.".format(size=len(table),verb=verb))
        elif more:
            if not log:
                table[ table.colnames[0] ].more()
            else:
                table.more()
            print("{size:d} files {verb:s}.".format(size=len(table),verb=verb))
        elif not output:
            table.write(sys.stdout, format=_format, bookend=False, delimiter=None, include_names=include)
            print("{size:d} files {verb:s}.".format(size=len(table),verb=verb))
        


class FITSInfo(FITSCLI):
    """Show information about a fits file"""
    
    command = 'info'
    
    help = "Show details about a group of FITS files."
    
    description = fill("Shows HDU info for the FITS files found.")
    
    options = [ "i", "ol", "skw", "s" ]
    
    def do(self):
        """Do the work"""
        files = self.get_files()
        search = self.get_keywords()
        data = FITSHeaderTable.fromfiles(files).search(**search)
        print("Will get info on %d files." % len(data))
        if self.opts.output is False:
            self.opts.output = None
        [ pf.info(header["OPENNAME"], self.opts.output) for header in data ]


class FITSHead(FITSCLI):
    """Show a FITS header"""
    
    command = 'head'
    
    help = "Show the headers of a bunch of FITS files."
    
    description = fill("Shows FITS headers for found FITS files.")
    
    options = [ "i", "skw", "s" ]
    
    def do(self):
        """Do the work!"""
        from ..util import stream_less
        files = self.get_files()
        search = self.get_keywords()
        data = FITSHeaderTable.fromfiles(files).search(**search)
        print("Will show header for %d files." % len(data))
        for header in data:
            write = lambda stream : stream.write(repr(header))
            stream_less(write)
        print("Examined {:d} headers.".format(len(data)))
    


class FITSGroup(FITSCLI):
    """Create a list of groups from FITS header attributes."""
    
    command = 'group'
    
    help = "Make a list of groups for a collection of FITS files."
    
    description = fill("Creates a text table with the requested header information grouped for a bunch of FITS files. Groups are collections of files which have identical header values. Files can be filtered before grouping using the 'KEYWORD=value' search syntax.")
    
    options = [ "i", "skw" ]
    
    def after_configure(self):
        """docstring for after_configure"""
        super(FITSGroup, self).after_configure()
        self.opts.log = True
        self.parser.add_argument('--list', help="Collect list names for addition to the grouping.", nargs="+", default=[])
    
    def do(self):
        """Make the log table"""
        files = self.get_files()
        search = self.get_keywords()
        
        if not isinstance(self.opts.list,list):
            olists = [ self.opts.list ]
        else:
            olists = self.opts.list
        lists = []
        for _list in olists:
            lists += glob.glob(_list)
        
        
        print("Will group %d files." % len(files))
        data = FITSHeaderTable.fromfiles(files).search(**search).group(search.keys())
        [ data.addlist(_list) for _list in lists ]
        table = data.table()
        self.output_table(table, verb="grouped")

class FITSLog(FITSCLI):
    """Create a log from FITS header attributes."""
    
    command = 'log'
    
    options = [ "i", "ol", "skw" ]
    
    help = "Make a log file for a collection of FITS files."
    
    description = fill("Creates a text table with the requested header information for a bunch of FITS files.")
    
    def do(self):
        """Make the log table"""
        from pyshell.util import check_exists
        if self.opts.output and check_exists(self.opts.output):
            print("Log %r already exists. Will overwirte." % self.opts.output)
        
        files = self.get_files()
        search = self.get_keywords()
        
        print("Will log %d files." % len(files))
        data = FITSHeaderTable.fromfiles(files).search(**search).normalize(search.keys())
        table = data.table(order=search.keys())
        self.output_table(table)
        
    
class FITSETC(FITSCLI):
    """Exposure time calculator"""
    command = 'exposure'
    
    options = [ "i", "skw" ]
    
    help = "Compute the exposure time for a collection of FITS files."
    
    description = fill("Computes the total exposure time for a collection of fits files.")
    
    def after_configure(self):
        """docstring for after_configure"""
        super(FITSETC, self).after_configure()
        self.opts.log = True
        self.parser.add_argument('--list', help="Collect list names for addition to the grouping.", nargs="+", default=[])
        self.parser.add_argument('--coadds', help='Keyword for number of coadds', default=False)
        self.parser.add_argument('--itime', help='Keyword for number of coadds', default="ITIME")
    
    def do(self):
        """Make the log table"""
        files = self.get_files()
        search = self.get_keywords()
        search.setdefault(self.opts.itime, True)
        if self.opts.coadds:
            search.setdefault(self.opts.coadds, True)
        
        if not isinstance(self.opts.list,list):
            olists = [ self.opts.list ]
        else:
            olists = self.opts.list
        lists = []
        for _list in olists:
            lists += glob.glob(_list)
        
        
        print("Will group %d files." % len(files))
        data = FITSHeaderTable.fromfiles(files).search(**search).group(search.keys())
        [ data.addlist(_list) for _list in lists ]
        table = data.table()
        
        etc = np.sum(table[self.opts.itime] * table[self.opts.coadds] * table['N'])
        self.output_table(table, verb="grouped")
        print("Total exposure: {:.2f}s".format(etc))


class FITSList(FITSCLI):
    """Make a list of files with certain header attributes"""
    
    command = "list"
    
    options = [ "i", "skw", "oil" ]
    
    help = "Make a list of FITS files that match criteria."
    
    description = "Make a list of FITS files that match given criteria using direct matching, substring matching, or regular expressions."
    
    def do(self):
        """Run the search itself"""
        search = self.get_keywords()
        files = self.get_files()
        print("Searching %d files." % len(files))
        data = FITSHeaderTable.fromfiles(files).search(**search)
        table = data.table(order=search.keys())
        self.output_table(table)
        

class FITSInspect(FITSCLI):
    """Inspect FITS files and create a list of only the approved files."""
    
    command = "inspect"
    
    options = [ "i", "skw", "oil" ]
    
    help = "Make a list of FITS files that match critera, inspecting each one in ds9."
    
    description = "Works just like the 'list' command, except that  each item to be added to the list is shown in DS9, and then can be approved/removed."
    
    def do(self):
        """Inspect files!"""
        search = self.get_keywords()
        files = self.get_files()
        print("Searching {:d} files".format(len(files)))
        data = FITSHeaderTable.fromfiles(files).normalize(search.keys()).search(**search)
        print("Inspecting {:d} files".format(len(data.files)))
        
        self.log.info("Command: {:s} {:s}".format(sys.argv[0],self.command))
        self.log.info("Inspecting {:d} of {:d} files.")
        
        print("Launching ds9")
        self.ds9 = self.get_ds9()
        use_files = []
        kept, discard = 0, 0
        for filename in data.files:
            basename = os.path.basename(filename)
            if not check_exists(filename):
                print("Input File '{:s}' does not exist! Discarding...".format(filename))
                self.log.info("Discarding '{:s}', it does not exist.".format(filename))
                discard += 1
                continue
            self.ds9inspect(filename)
            if query_yes_no("'{}' is good?".format(basename),default="yes"):
                self.log.info("Keeping '{:s}'.".format(basename))
                use_files.append(filename)
                kept += 1
            else:
                self.log.info("Discarding '{:s}'.".format(basename))
                discard += 1
        
        print("Kept {:d} files out of {:d} original files".format(kept,kept+discard))
        self.log.info("Kept {:d} files out of {:d} original files".format(kept,kept+discard))
        
        inspected_data = FITSHeaderTable.fromfiles(use_files)
        
        self.output_table(inspected_data.table(order=search.keys()))
    
    
    def ds9inspect(self, filename):
        """Inspect the file in ds9"""
        self.ds9.set("file {:s}".format(filename))
        self.ds9.set('zoom to fit')
        self.ds9.set('scale log')
        self.ds9.set('cmap sls')
    
class FITSFixHeader(FITSCLI):
    """docstring for FITSFixHeader"""
    
    command = "fix"
    
    options = [ "i", "skw"]
    
    help = "Fix a bunch of header keywords, especially targets."
    
    description = "Tries to identify targets and fix header keyword values to match targets."
    
    tolerance = 20 * u.arcsec
    
    def do(self):
        """Inspect files!"""
        search = self.get_keywords()
        files = self.get_files()
        print("Searching {:d} files".format(len(files)))
        data = FITSHeaderTable.fromfiles(files).normalize(search.keys()).search(**search)
        print("Fixing {:d} files".format(len(data.files)))
        
        self.log.info("Command: {:s} {:s}".format(sys.argv[0],self.command))
        self.log.info("Fixing {:d} of {:d} files.".format(len(data.files), len(files)))
        
        self.locations = {}
        self.files = collections.defaultdict(list)
        self.updated = collections.Counter()
        
        exceptions = 0
        
        for header in data:
            
            try:
                location = header["OBJECT"]
                coords = ICRS(header["RA"], header["DEC"], unit=(u.deg, u.deg))
            except Exception as e:
                self.log.exception(e)
                exceptions += 1
                if exceptions > 10:
                    raise
                continue
            
            if len(self.locations):
                if self.check_for_collision(coords, location):
                    location = self.handle_collision(header.filename, location, coords)
            
                if location in self.locations:
                    location = self.handle_match(header.filename, location, coords)
            
            self.locations[location] = coords
            self.files[location] += [header.filename]
        
        for location in self.files:
            for filename in self.files[location]:
                with fits.open(filename, mode='update', ignore_missing_end=True) as HDUs:
                    if HDUs[0].header.get("OBJECT") != location:
                        old_location = HDUs[0].header.get("OBJECT")
                        print("Fixing header for '{}'".format(filename))
                        print("{} -> {}".format(old_location, location))
                        HDUs[0].header["OBJECT"] = (location, "MODIFIED")
                        HDUs[0].header["HISTORY"] = "OLD OBJECT {}".format(old_location)
                        HDUs[0].header["HISTORY"] = "OBJECT changed {} -> {}".format(old_location, location)
                        HDUs.flush(output_verify='fix')
                        self.updated[location] += 1
        print("Updated {} OBJECT keywords for {} locations.".format(sum(self.updated.values()), len(self.updated)))
    
    
    def handle_match(self, filename, location, coords):
        """Target matches based on object name"""
        separation = coords.separation(self.locations[location]).to(u.arcsec)
        if separation > self.tolerance:
            print(" Too far away from target coordinates:")
            print("File '{0}' appears to be ∆{1.value}{1.unit:unicode} from target {2}.".format(filename, separation, location))
            if query_yes_no("Is it a new target?", default=None):
                location = query_string("Enter the target name:")
                if location in self.locations:
                    return self.handle_match(filename, location, coordss)
        else:
            print("File '{0}' is consistent with target {2}, ∆{1.value}{1.unit:unicode}".format(filename, separation, location))
        
        return location
    
    def check_for_collision(self, coords, location):
        """docstring for check_for_collision"""
        distances = [ ocoords.separation(coords).arcsec for ocoords in self.locations.values() ]
        if len(distances) and min(distances) < self.tolerance.value:
            if self.locations.keys()[distances.index(min(distances))] == location:
                return False
            else:
                return True
        else:
            return False
    
    def handle_collision(self, filename, location, coords):
        """Target collision"""
        distances = np.array([ ocoords.separation(coords).arcsec for ocoords in self.locations.values() ])
        collisions = distances <= self.tolerance.value
        locations = np.array(self.locations.keys())
        
        real_collisions = [ ctarget for ctarget in locations[collisions] if (not ctarget[:2] == "tt") and (ctarget != location) ]
        if len(real_collisions) == 0:
            return location
        
        print(" Too close to a different potential target:")
        print("File '{0}' target {1} appears to be the same as [{2}].".format(filename, location, ",".join(locations[collisions])))
        options = list(locations[collisions])
        if len(options) == 1:
            print("Distance ∆{0.value}{0.unit:unicode}".format(self.locations[options[0]].separation(coords).to(u.arcsec)))
            if query_yes_no("Normalize {0} to {1}".format(location, options[0]), default="yes"):
                return options[0]
        labels = [ "{0} ∆{1.value}{1.unit:unicode}".format(olocation, self.locations[olocation].separation(coords).to(u.arcsec)) for olocation in options ]
        if location not in options:
            options += [location]
            labels += [location]
        options += ["NEW TARGET"]
        labels += ["NEW TARGET"]
        location = query_select(options, labels=labels, default=options.index(location))
        if location == "NEW TARGET":
            location = query_string("New Target Name:")
        return location
        


class POcommand(SCController):
    
    description = "Observing and FITS file inspection tools."
    
    defaultcfg = "observing.yml"
    
    _subparsers_help = "Available Commands:"
    
    subEngines = [
        FITSGroup,
        FITSETC,
        FITSLog,
        FITSList,
        FITSInfo,
        FITSInspect,
        FITSHead,
        FITSFixHeader,
        StarlistToRegion,
    ]