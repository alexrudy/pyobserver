#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 
#  get_semeseter_limits.py
#  pyobserver
#  
#  Created by Alexander Rudy on 2014-03-06.
#  Copyright 2014 University of California. All rights reserved.
# 


from __future__ import (absolute_import, unicode_literals, division,
                        print_function)

from pyshell.util import ipydb
from pyobserver.visibility import get_observatory
from astropyephem import Sun
import astropy.time
import astropy.units as u
import argparse
import six
ipydb()

def parse_arguments():
    """Handle possible arguments"""
    parser = argparse.ArgumentParser()
    parser.add_argument("semester", type=six.text_type, help="Semester, in the format '2014B'")
    parser.add_argument("-O","--observatory", type=six.text_type, help="Observatory name", default="Keck")
    return parser.parse_args()

def main():
    """Run the program!"""
    opts = parse_arguments()
    observatory = get_observatory(opts.observatory)
    start, mid, stop = get_dates(opts.semester)
    observatory.date = start
    observatory.date = observatory.next_setting(Sun())
    print(observatory)
    print("Semester {} Start:".format(opts.semester))
    print(" ",observatory.date.iso)
    print(" ",observatory.sidereal_time().to_string(u.hourangle, sep="hms"))

    observatory.date = mid
    observatory.date = observatory.next_antitransit(Sun())
    sun = Sun()
    sun.compute(observatory)
    print("Semester {} Middle:".format(opts.semester))
    print(" ",observatory.date.iso)
    print(" ",observatory.sidereal_time().to_string(u.hourangle, sep="hms"))

    observatory.date = stop
    observatory.date = observatory.previous_setting(Sun())
    print("Semester {} End:".format(opts.semester))
    print(" ",observatory.date.iso)
    print(" ",observatory.sidereal_time().to_string(u.hourangle, sep="hms"))
    
def get_dates(semester):
    """Given a semester, return the start and end dates."""
    if len(semester) != 5:
        raise ValueError("Can't understand semester {!r}".format(semester))
    year = int(semester[:4])
    sem = semester[4]
    if sem == "A":
        start = astropy.time.Time("{:4d}-02-01".format(year), scale='utc')
        mid = astropy.time.Time("{:4d}-04-15".format(year), scale='utc')
        stop = astropy.time.Time("{:4d}-08-01".format(year), scale='utc')
    elif sem == "B":
        start = astropy.time.Time("{:4d}-08-01".format(year), scale='utc')
        mid = astropy.time.Time("{:4d}-10-15".format(year), scale='utc')
        stop = astropy.time.Time("{:4d}-02-01".format(year+1), scale='utc')
    else:
        raise ValueError("Can't understand semester {!r}".format(semester))
    return start, mid, stop
        
if __name__ == '__main__':
    main()