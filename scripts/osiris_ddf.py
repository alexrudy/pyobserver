#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import (absolute_import, unicode_literals, division, print_function)

import six
import re
import os, os.path
import argparse
import astropy.units as u
from pyshell.util import ipydb
import subprocess
import glob
ipydb()    

def guidestar_circle(position, radius = 0.5 * u.arcsec, color='white', text='Guide Star'):
    """Create a guidestar circle object."""
    
    return 'circle({ra:s},{dec:s},{radius:.2f}") # color={color} text={{{text:s}}}'.format(
        ra = position.ra.to_string(u.hourangle, sep=":", pad=False),
        dec = position.dec.to_string(u.degree, sep=":", pad=False),
        radius = radius.to(u.arcsec).value,
        text = text,
        color = color,
    )
    
def osiris_fov(position, pa=0 * u.degree, filter='Kbb', scale=(0.035 * u.arcsec / u.pix), offset = (0 * u.arcsec, 0 * u.arcsec), text='Origin', color='red'):
    """Make an OSIRIS FOV region."""
    from pyobserver.instruments.osiris import get_osiris_filters
    table = get_osiris_filters()
    scale_col = "FOV{:.3f}".format(scale.to(u.arcsec/u.pixel).value)
    if scale_col[-1] == "0":
        scale_col = scale_col[:-1]
    
    row = (table['Filter'] == filter)
    fov = table[scale_col][(table['Filter'] == filter)][0]
    width, height = map(lambda v : u.Quantity(float(v), u.arcsec), fov.split("x"))
    return 'box({ra:s},{dec:s},{width:f}",{height:f}",{pa}) # color={color} text={{{text:s}}}'.format(
        ra = (position.ra + offset[0]).to_string(u.hourangle, sep=":", pad=False),
        dec = (position.dec + offset[1]).to_string(u.degree, sep=":", pad=False),
        width = width.to(u.arcsec).value,
        height = height.to(u.arcsec).value,
        text = text,
        pa = pa.to(u.degree).value,
        color = color,
    )
    
def offset_ruler(start, end, text, color='white'):
    """Produce an offset ruler"""
    return "# ruler({start_ra:s},{start_dec:s},{end_ra:s},{end_dec:s}) ruler=fk5 arcsec color={color}, text={{{text:s}}}".format(
        start_ra = start.ra.to_string(u.hourangle, sep=":", pad=False),
        start_dec = start.dec.to_string(u.degree, sep=":", pad=False),
        end_ra = end.ra.to_string(u.hourangle, sep=":", pad=False),
        end_dec = end.dec.to_string(u.degree, sep=":", pad=False),
        text = text,
        color = color,
    )

region_header = """# Region file format: DS9 version 4.1
global color=green dashlist=8 3 width=1 font="helvetica 10 normal roman" select=1 highlite=1 dash=0 fixed=0 edit=1 move=1 delete=1 include=1 source=1
fk5"""

def make_target_region(target, starlist, filter='Kbb', scale=(0.035 * u.arcsec / u.pix)):
    """Make a region for a given target."""
    gs = starlist.get_guidestars(target)
    region = [region_header]
    
    # Add the origin
    region.append(osiris_fov(target.fixed_position, pa = getattr(target, 'pa', 0) * u.degree, filter=filter, scale=scale))
    
    # Add the guidestars
    for gs_target in gs:
        region.append(guidestar_circle(gs_target.fixed_position, text=gs_target.name))
        region.append(offset_ruler(target.fixed_position, gs_target.fixed_position, 'Guide Star Offset'))
    
    # Add the sky position. Place it along the vector to the guidestar.
    offset_size = 20 * u.arcsec if target.separation(gs_target) > 30 * u.arcsec else target.separation(gs_target) / 2.0
    pa = target.position_angle(gs_target)
    offset = (np.sin(pa) * offset_size, np.cos(pa) * offset_size)
    region.append(osiris_fov(target.fixed_position, pa = getattr(target, 'pa', 0) * u.degree, filter=filter, scale=scale, offset=offset, text = "Sky"))
    
    return "\n".join(region)
    
def make_fov_from_dither(base, ditherPosition, filter='Kbb', scale=None, offset_units=u.arcsec, label='', color='white', pa=0.0* u.degree):
    """Make the FOV from a dither positon."""
    from astropy.coordinates import SkyCoord
    ra_offset = float(ditherPosition.get('xOff')) * offset_units
    dec_offset = float(ditherPosition.get('yOff')) * offset_units
    position = SkyCoord(ra=base.ra + ra_offset, dec=base.dec + dec_offset, frame=base.frame.__class__)
    return osiris_fov(position, pa=pa, filter=filter, scale=scale, text=label, color=color)
    
def make_ddf_region(target, starlist, ddf):
    """Make a DDF-based region."""
    from pyobserver.instruments.osiris import parse_ddf
    import astropy.units as u
    region = [region_header]
    tree = parse_ddf(ddf)
    root = tree.getroot()
    
    dataset = root.find('./dataset')
    spec = dataset.find('./spec')
    fov_string = spec.get('scale')
    fov = float(fov_string[:fov_string.find('"')]) * u.arcsec / u.pixel
    spec_filter = spec.get('filter')
    
    # Add the origin
    region.append(guidestar_circle(target.fixed_position, text='Origin', color='red'))
    
    gs = starlist.get_guidestars(target)
    for gs_target in gs:
        region.append(guidestar_circle(gs_target.fixed_position, color='white', text=gs_target.name))
        region.append(offset_ruler(target.fixed_position, gs_target.fixed_position, 'Guide Star Offset', color='white'))
    
    
    ditherPattern = dataset.find('./ditherPattern')
    pa = float(ditherPattern.get("skyPA", 0.0)) * u.degree
    units = u.Unit(ditherPattern.get('units'))
    for i,ditherPosition in enumerate(ditherPattern.iter('ditherPosition')):
        if ditherPosition.get('sky').lower() == 'true':
            label = '{:d}: Sky'.format(i)
            color = 'cyan'
        else:
            label = '{:d}: Target'.format(i)
            color = 'green'
        region.append(make_fov_from_dither(target.fixed_position, ditherPosition, filter=spec_filter, scale=fov, offset_units=units, label=label, color=color, pa=pa))
    return "\n".join(region)
    
def main():
    """Handle the arguments, etc."""
    parser = argparse.ArgumentParser(description="Produce a simple region file for help making OSIRIS DDFs")
    parser.add_argument('starlist', help='Starlist filename', type=six.text_type)
    parser.add_argument('target', help='Target name', type=six.text_type)
    parser.add_argument('--filter', help='Filter name', type=six.text_type, default='Kbb')
    parser.add_argument('--fov', help='Scale (in arcsec/pixel)', type=float, default = 0.035)
    parser.add_argument('--output', help='Output region name', type=six.text_type)
    parser.add_argument('--ds9', help='Open with DS9', action='store_true')
    parser.add_argument('--ddf', help='DDF filename', type=six.text_type)
    args = parser.parse_args()
    print("Parsing starlist '{}'".format(args.starlist))
    from pyobserver.visibility.targets import Starlist
    starlist = Starlist.from_starlist(args.starlist)
    
    region = None
    for target in starlist:
        if target.name == args.target:
            if args.ddf is None:
                print("Making automatic region file for {}".format(target))
                region = make_target_region(target, starlist, args.filter, args.fov * u.arcsec / u.pixel)
            else:
                print("Making region file for {}: {}".format(target, args.ddf))
                region = make_ddf_region(target, starlist, args.ddf)
            break
    if region is None:
        parser.error("Target '{}' not found in starlist '{}'".format(args.target, args.starlist))
    
    # Write file.
    if args.output is None: 
        filename = "{}-auto.reg".format(target.name)
    else:
        filename = args.output
    print("Saving region file to '{}'".format(filename))
    with open(filename, 'w') as stream:
        stream.write(region)
    
    # Handle opening DS9
    if args.ds9:
        ddf_open_ds9(target, filename)

def ddf_open_ds9(target, filename):
    """Assemble the arguments to open DS9"""
    ds9args = ["ds9", '-view', 'layout', 'vertical']
    for idx, image in enumerate(glob.glob("{}*.fits".format(target.name))):
        if idx:
            ds9args += ['-frame', 'new']
        ds9args += [image, '-cmap', 'hsv', '-scale', 'log', '-bg', 'black']
    ds9args += ["-regions", "load", 'all', filename ]
    ds9args += ["-pan", "to",
        "{:s}".format(target.fixed_position.ra.to_string(u.hourangle, sep=":", pad=False)), 
        "{:s}".format(target.fixed_position.dec.to_string(u.degree, sep=":", pad=False)), "wcs", "fk5"]
    if idx:
        ds9args += ['-frame', 'match', 'wcs']
        ds9args += ['-frame', 'lock', 'wcs']
        ds9args += ['-frame', six.text_type(idx+1)]
    ds9args += ['-geometry', '1300x900']
    print(" ".join(ds9args))
    subprocess.Popen(ds9args)

if __name__ == '__main__':
    main()
