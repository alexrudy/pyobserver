#!/opt/local/Library/Frameworks/Python.framework/Versions/2.7/bin/python
# -*- coding: utf-8 -*-
# 
#  try_target.py
#  pyobserver
#  
#  Created by Alexander Rudy on 2014-03-03.
#  Copyright 2014 Alexander Rudy. All rights reserved.
# 

from __future__ import (absolute_import, unicode_literals, division,
                        print_function)

import os, os.path
if "VIRTUAL_ENV" in os.environ:
    activate_this = os.path.join(os.environ["VIRTUAL_ENV"],'bin/activate_this.py')
    execfile(activate_this, dict(__file__=activate_this))
    del activate_this


from pyobserver.ephem import VisibilityPlot, Target, Observer


import sys
import six
import argparse
import matplotlib
import astropy.units as u
from astropy.units import imperial
from astropy.coordinates import ICRS, Latitude, Longitude
from astropy.time import Time

from pyshell.util import ipydb
ipydb()

import matplotlib.pyplot as plt
import subprocess


def visibility_main():
    """Plot a single target."""
    parser = argparse.ArgumentParser(description="A visibility plotter for a single target.")
    parser.add_argument("target", type=six.text_type, help="Object name as resolved by SIMBAD")
    parser.add_argument("-d","--date", help="Date before night, as parsed by Astropy.", default=Time.now())
    parser.add_argument("-o","--output", type=six.text_type, help="Output filename.")
    parser.add_argument("--tz", type=six.text_type, help="Local Timezone.")
    parser.add_argument("--show", action="store_true", help="Show, don't save.")
    options = parser.parse_args()
    
    # Setup Target
    t = Target(name=options.target, position=ICRS.from_name(options.target))
    date = Time(options.date, scale='utc')
    
    if not options.output:
        options.output = "visibility_{0}_{1:%Y%m%d}.pdf".format(t.name.replace(" ", "_"), date.datetime)
    
    o = Observer(
        lat = Latitude("19 49 35.61788", u.degree),
        lon = Longitude("-155 28 27.24268", u.degree, wrap_angle=180 * u.deg),
        name = "Keck II")
    o.elevation = 13646.92 * imperial.ft
    o.timezone = "US/Hawaii"
    print(o)
    t.compute(o)
    print(t)
    
    # Setup Figure
    fig = plt.figure()
    bbox = (0.1, 0.1, 0.65, 0.8) # l, b, w, h
    v_ax = fig.add_axes(bbox)
    v = VisibilityPlot(o, date)
    v.add(t)
    v(v_ax, moon_distance_maximum=(60 * u.degree))
    
    if options.show:
        plt.show()
    else:
        plt.savefig(options.output)
        subprocess.call(["open", options.output])
        
if __name__ == '__main__':
    visibility_main()