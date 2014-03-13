# -*- coding: utf-8 -*-
# 
#  util.py
#  pynirc2
#  
#  Created by Jaberwocky on 2013-02-11.
#  Copyright 2013 Jaberwocky. All rights reserved.
# 

from __future__ import (absolute_import, unicode_literals, division, print_function)

import astropy.units as u
import astropy.time
from astropy.coordinates import FK4, FK5

import re
_starlist_re_raw = r"""
    ^(?P<Name>.{1,15})[\ ]+ # Target name must be the first 15 characters.
    (?P<RA>[\d]{1,2}\ [\d]{2}\ [\d]{2}(?:\.[\d]+)?)[\ ]+  # Right Ascension, HH MM SS.SS+
    (?P<Dec>[+-]?[\d]{1,2}\ [\d]{2}\ [\d]{2}(?:\.[\d]+)?)[\ ]+ # Declination, (-)DD MM SS.SS+
    (?P<Equinox>(?:[\d]{4}(?:\.[\d]+)?)|(?:APP))[\ ]* # Equinox.
    (?P<Keywords>.+)?$ # Everything else must be a keyword.
    """
    
_starlist_re = re.compile(_starlist_re_raw, re.VERBOSE)

_starlist_re_strict = r"""
    ^(?P<Name>.{15})\  # Target name must be the first 15 characters.
    (?P<RA>[\d]{2}\ [\d]{2}\ [\d]{2}(?:\.[\d]+)?)\   # Right Ascension, HH MM SS.SS+
    (?P<Dec>[+-]?[\d]{1,2}\ [\d]{2}\ [\d]{2}(?:\.[\d]+)?)\  # Declination, (-)DD MM SS.SS+
    (?P<Equinox>(?:[\d]{4}(?:\.[\d]+)?)|(?:APP))[\ ]? # Equinox.
    (?P<Keywords>[^\ ].+)?$ # Everything else must be a keyword.
    """

def verify_starlist_line(text):
    """Verify that the given line is a valid starlist."""
    line = text
    warnings = []
    for tokenizer_strict, tokenizer_weak in zip(_starlist_re_strict.splitlines(), _starlist_re.splitlines()):
        match_strict = re.match(tokenizer_strict, text, re.VERBOSE)
        match_weak = re.match(tokenizer_weak, text, re.VERBOSE)
        if match_strict:
            continue
        elif not match_weak:
            warnings.append("Couldn't parse token '{}' with '{}'".format(text, tokenizer_weak))
            
    
def parse_starlist_line(text):
    """docstring for parse_starlist_line"""
    match = _starlist_re.match(text)
    if not match:
        raise ValueError("Couldn't parse '{}', no regular expression match found.".format(text))
    data = match.groupdict("")
    if data['Equinox'] == "APP":
        equinox = astropy.time.Time.now()
        coords = FK5
    else:
        equinox = astropy.time.Time(float(data['Equinox']), format='jyear', scale='utc')
        if float(data['Equinox']) <= 1950:
            equinox = astropy.time.Time(float(data['Equinox']), format='byear', scale='utc')
            coords = FK4
        else:
            coords = FK5
    
    position = coords(data["RA"], data["Dec"], unit=(u.hourangle, u.degree), equinox=equinox)
    
    results = dict(
        Name = data['Name'].strip(),
        Position = position,
    )
    for keywordvalue in data.get("Keywords","").split():
        keyword, value = keywordvalue.split("=",1)
        keyword = keyword.strip()
        if keyword in set(["Name", "Position"]):
            raise KeyError("Illegal Keyword Name: '{}'".format(keyword))
        results[keyword] = value.strip()
    return results
    
def read_skip_comments(filename, comments="#"):
    """Read a filename, yielding lines that don't start with comments."""
    with open(filename, 'r') as stream:
        for line in stream:
            if not line.startswith(comments):
                yield line.strip().strip("\n\r")
    
def parse_starlist(starlist):
    """Parse a starlist into a sequence of dictionaries."""
    for line in read_skip_comments(starlist):
        yield parse_starlist_line(line)
    
def stream_less(infunc):
    """Launch the terminal command `less` using an input stream."""
    import subprocess, sys
    
    args = ['less','-e']
    
    less = subprocess.Popen(args,stdin=subprocess.PIPE)
    try:
        infunc(less.stdin)
        less.stdin.flush()
        less.stdin = sys.stdin
        less.wait()
    except IOError:
        less.terminate()
        raise
    