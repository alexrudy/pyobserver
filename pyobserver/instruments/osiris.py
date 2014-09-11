# -*- coding: utf-8 -*-
# 
#  osiris.py
#  pyobserver
#  
#  Created by Alexander Rudy on 2014-03-06.
#  Copyright 2014 University of California. All rights reserved.
# 

from __future__ import (absolute_import, unicode_literals, division, print_function)

import numpy as np
import astropy.table
import astropy.cosmology
import pkg_resources
import pyshell.config
import astropy.units as u

def get_osiris_filters():
    """Retrieve an astropy table containing the OSIRIS filters."""
    config = get_osiris_configuration()
    table = astropy.table.Table.read(pkg_resources.resource_stream('pyobserver','data/{}'.format(config["filters.table"])), format='ascii.tab')
    return table
    
_config = pyshell.config.StructuredConfiguration.fromresource('pyobserver', 'data/osiris_info.yml')
def get_osiris_configuration():
    """Get the osiris configuration."""
    return _config

def osiris_scales_at_redshift(z, cosmo=None):
    """Return a table of OSIRIS filters and their respective scales."""
    if cosmo is None:
        cosmo = astropy.cosmology.default_cosmology.get()
    config = get_osiris_configuration()
    kpc_per_arcmin = cosmo.kpc_proper_per_arcmin(z)
    pixel_scales = (np.array(config["scales"]) * u.arcsec)
    physical_scales = pixel_scales * kpc_per_arcmin
    return physical_scales, pixel_scales
    

