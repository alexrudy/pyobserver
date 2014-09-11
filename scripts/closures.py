#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import (absolute_import, unicode_literals, division, print_function)

import six
import re

def parse_closures(filename, date=None):
    """Parse and understand closures."""
    from pyobserver.closures import parse_closures_list
    with open(filename, 'r') as stream:
        closures = list(parse_closures_list(stream, date))
    return closures
    
def main():
    """Argument parsing and main."""
    import argparse
    import glob
    parser = argparse.ArgumentParser()
    parser.add_argument('filename', nargs='?', type=six.text_type, default=glob.glob('opensUnix*.txt')[0])
    parser.add_argument('--soon', action='store_true', help='Show upcoming closures.')
    parser.add_argument('--target', type=six.text_type, help='Show a specific target.')
    parser.add_argument('--when', help='When this closure list applies.')
    
    opts = parser.parse_args()
    
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