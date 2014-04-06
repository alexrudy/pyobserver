#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 
#  load_table.py
#  pyobserver
#  
#  Created by Alexander Rudy on 2014-03-04.
#  Copyright 2014 University of California. All rights reserved.
# 

from __future__ import (absolute_import, unicode_literals, division,
                        print_function)



import sys
import astropy.table
import astropy.units as u
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pyobserver.targets.master import MasterTarget
from pyshell.util import ipydb

if __name__ == '__main__':
    
    ipydb()
    
    if len(sys.argv) != 2:
        print('Usage: {} data.hdf5'.format(sys.argv[0]))
        sys.exit(1)
    
    engine = create_engine('sqlite:///targets.sqlite', echo=True)
    Session = sessionmaker(bind=engine)
    
    print("Setting up database...")
    from pyobserver.targets.core import Base
    Base.metadata.create_all(engine)
    
    print("Loading table from a file...")
    datafile = sys.argv[1]
    table = astropy.table.Table.read(datafile, path='targets')
    
    print("Adding table rows to database...")
    session = Session()
    for target_row in table:
        target_sqobj = MasterTarget(name=target_row["Name"], ra=target_row["RA"] * u.degree, dec=target_row["DEC"] * u.degree, redshift=target_row['z'])
        session.add(target_sqobj)
    session.commit()
    
