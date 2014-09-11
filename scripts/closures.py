#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import (absolute_import, unicode_literals, division, print_function)

import six
import re
import os, os.path

def parse_closures(filename, date=None):
    """Parse and understand closures."""
    from pyobserver.closures import parse_closures_list
    with open(filename, 'r') as stream:
        closures = list(parse_closures_list(stream, name=filename, date=date))
    return closures
    
def parse_lick_closures(starlist, filenames, date=None):
    """Parse and understand closures in the lick format."""
    from pyobserver.closures import LCHClosureParserLick
    parser = LCHClosureParserLick(starlist, date)
    return list(parser(starlist, filenames).values())
    
def main():
    """Argument parsing and main."""
    import argparse
    import glob
    
    # Find the default closure filename.
    default_filenames = glob.glob('opensUnix*.txt')
    if len(default_filenames) > 0:
        default_filename = default_filenames[0]
    else:
        default_filename = False
    
    parser = argparse.ArgumentParser()
    parser.add_argument('filename', nargs='?', type=six.text_type, default=default_filename)
    parser.add_argument('--soon', action='store_true', help='Show upcoming closures.')
    parser.add_argument('--target', type=six.text_type, help='Show a specific target.')
    parser.add_argument('--when', help='When this closure list applies.')
    parser.add_argument('--compact', type=six.text_type, help="Use the compact file format. Specify a directory for .lsm files.", default=False)
    opts = parser.parse_args()
    
    if not opts.filename:
        parser.error("Must specify a filename!")
    
    import astropy.time
    if opts.when is not None:
        opts.when = astropy.time.Time(opts.when, scale='utc', format='iso')
    else:
        m = re.match(r"opens[Unix|Dos](?P<date>[\d]{6})\.txt", opts.filename)
        if m:
            iso_str = "-".join(m.groupdict()['date'][::2])
            opts.when = astropy.time.Time(iso_str, scale='utc', format='iso')
        else:
            opts.when = astropy.time.Time.now()
    
    if opts.compact:
        filenames = os.path.join(opts.compact, "*.lsm")
        closures = parse_lick_closures(opts.filename, filenames, opts.when)
    else:
        closures = parse_closures(opts.filename, opts.when)
    
    if opts.soon:
        show_upcoming_closures(closures)
    elif hasattr(opts, 'target') and opts.target is not None:
        show_target_closures(closures, opts.target)
    else:
        show_closures(closures)
        
def show_upcoming_closures(closures):
    """Show the upcoming closures."""
    from pyobserver.closures import upcoming_closures
    for closure in upcoming_closures(closures):
        print("In {3:s}: At {0.datetime:%H:%M:%S} for {1:4.0f} : {2:s}".format(closure.start, closure.duration, closure.region.name, closure.time_to(string=True)))
        
def show_target_closures(closures, target):
    """Show an individual target."""
    targets = { region.name:region for region in closures }
    show_region(targets[target])

def show_region(region):
    """Show a closure region."""
    print("{0.name} at {1}".format(region, region.position_string()))
    for event in region.closures:
        if event.time_to().to('s').value > 0:
            print(" {3} in {0:s} at {1.datetime:%H:%M:%S} for {2:4.0f}".format(
                event.time_to(string=True), event.start, event.duration, event.__class__.__name__))
        else:
            print(" "+repr(event)[1:-1])

def show_closures(regions):
    """Show all closures."""
    for region in regions:
        show_region(region)
        print("-" * 75)
        
    
if __name__ == '__main__':
    from pyshell.util import ipydb
    ipydb()
    main()