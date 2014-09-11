# -*- coding: utf-8 -*-
#
#  closures.py
#  pyobserver
#
#  Created by Alexander Rudy on 2014-07-19.
#  Copyright 2014 Alexander Rudy. All rights reserved.
#
"""
Handle LCH Closures
"""
from __future__ import (absolute_import, unicode_literals, division, print_function)

import re
import six
import itertools
import warnings
import collections
import itertools
import numpy as np

import astropy.units as u
from astropy.time import Time
from astropy.coordinates import FK5, AltAz, FK4
from astropy.utils.console import human_time

from .visibility.targets import Target, AltAzTarget, StarlistBase

class Region(StarlistBase):
    """Region for LCH Closures"""
    
    REGISTRY = {}
    RADIUS = 2 * u.arcmin
    
    def __init__(self, *args, **kwargs):
        super(Region, self).__init__(*args, **kwargs)
        self._openings = set()
    
    def contains(self, position):
        """Test whether a position is within this LCH region."""
        return (self.fixed_position - position) < self.RADIUS
    
    @property
    def openings(self):
        """A list of openings, in order."""
        openings = list(self._openings)
        openings.sort(key=lambda o : o.start)
        return openings
    
    def add(self, opening):
        """Add an opening"""
        self._openings.add(opening)
    
    def open(self, time):
        """Check if this window is open during a specific time."""
        for opening in self._openings:
            if (time > opening.start) and (time < opening.end):
                return True
    
    def closed(self, time):
        """Check if this window is closed during a specific time."""
        return (not self.open(time))
        
    @property
    def closures(self):
        """Get a closure list."""
        for open_start, open_end in self._iter_start_end:
            yield Closure(self, open_start.end, open_end.start)
            
    @property
    def _iter_start_end(self):
        """Iterate over pairs of openings, useful for iterating through closures, or through closures and openings."""
        openings = self.openings
        starts = itertools.islice(openings, len(openings)-1) # Take everything but the last element
        ends = itertools.islice(openings, 1, None) # Take everything but the first element
        return itertools.izip(starts, ends)
            
    @property
    def events(self):
        """Interleaved closures and openings."""
        for open_start, open_end in self._iter_start_end:
            yield open_start
            yield Closure(self, open_start.end, open_end.start)
        yield open_end

@Region.register(FK4)
@Region.register(FK5)
class FixedRegion(Region, Target):
    """A fixed position region."""
    PRIORITY = 0

@Region.register(AltAz)
class AltAzRegion(Region, AltAzTarget):
    """docstring for AltAzRegion"""
    pass


class WindowTimeProperty(object):
    """Descriptor for time properties."""
    def __init__(self, name):
        super(WindowTimeProperty, self).__init__()
        self.name = name
        
    @property
    def attr(self):
        """Attribute name."""
        return "_{}_{}".format(self.__class__.__name__, self.name)
        
    def __set__(self, obj, value):
        """Set the property."""
        setattr(obj, self.attr, Time(value))
        
    def __get__(self, obj, objtype=None):
        """Get the property"""
        if obj is None:
            return self
        if not hasattr(obj, self.attr):
            raise AttributeError("{:s}.{:s} has not been initialized".format(obj.__class__.__name__, self.name))
        return getattr(obj, self.attr)
        

class Window(object):
    """An LCH Window"""
    def __init__(self, region, start, end):
        super(Window, self).__init__()
        self.region = region
        self.start = start
        self.end = end
    
    start = WindowTimeProperty("start")
    end = WindowTimeProperty("end")
    
    def __repr__(self):
        """Representer for this LCH window object."""
        try:
            return "<{0:s} from {1.datetime:%H:%M:%S} to {2.datetime:%H:%M:%S} ({3:.0f})>".format(self.__class__.__name__, self.start, self.end, self.duration)
        except AttributeError:
            return super(Window, self).__repr__()
        
    @property
    def duration(self):
        """The duration of this closure."""
        return (self.end - self.start).to(u.s)
        
    def time_to(self, time = None, string = False):
        """Compute the time until this closure starts, from a given time.
        
        :param time: The reference time for this closure.
        :param string: Return the time to this closure as a six-character string.
        
        """
        time = Time.now() if time is None else time
        ttc = (self.start - time)
        if string:
            return human_time(ttc.to("s").value)
        return ttc
        
class Closure(Window):
    """An LCH closure window, when the laser cannot be propogated."""
    propogate = False
    
class Opening(Window):
    """An LCH Opening window, when the laser can be propogated."""
    propogate = True
    
    def __init__(self, region, start, end):
        super(Opening, self).__init__(region, start, end)
        self.region.add(self)
    
    @classmethod
    def from_openings(cls, region, text, date=None):
        """Parse a line of openings to create this object.
        
        :param region: The region to which this closure applied.
        :param text: The line of text for the closure.
        :param date: The date of the closure.
        
        """
        data = parse_openings_line(text, date)
        obj = cls(region, data["Start"], data["End"])
        if not np.abs(obj.duration - data["Opening"]) < 1.0 * u.second:
            raise ValueError("Duration of opening {} does not match parsed value: {}".format(obj, data["Opening"]))
        return obj
    

class LCHSummaryGroup(collections.OrderedDict):
    """LCH Summary group."""
    def __init__(self):
        super(LCHSummaryGroup, self).__init__()
        self._verified = [False, False]
        self._ordinal = None
        
    @property
    def ordinal(self):
        """Ordinal label."""
        return self._ordinal
        
    @property
    def verified(self):
        """Whether this summary has been verified."""
        return all(self._verified)
        
    def verify_count(self, ordinal, n_objects, n_closures):
        """Verify closure count."""
        self._verify_ordinal(ordinal)
        self._verify_regions(n_objects)
        if self.n_closures != n_closures:
            raise ValueError("{}: Number of closures mismatch: {} != {}".format(self, self.n_closures, n_closures))
        self._verified[0] = True
        
    def verify_duration(self, ordinal, n_objects, t_closures):
        """Verify closure duration."""
        self._verify_ordinal(ordinal)
        self._verify_regions(n_objects)
        if abs(self.t_closures - t_closures) > 1.0 * u.second:
            raise ValueError("{}: Duration of closures mismatch: {} != {}".format(self, self.t_closures, t_closures))
        self._verified[1] = True
        
    def _verify_regions(self, n_objects):
        """Verify the number of regions."""
        if self.n_objects != n_objects:
            raise ValueError("{}: Number of regions mismatch: {} != {}".format(self, self.n_objects, n_objects))
        
    def _verify_ordinal(self, ordinal):
        """Verify the ordinal for this summary."""
        if self._ordinal is None:
            self._ordinal = ordinal
        elif self._ordinal != ordinal:
            raise ValueError("{}: Can't change ordinal to {}".format(self, ordinal))
        
    def __repr__(self):
        """Represent this summary group."""
        repr_str = ["<{}".format(self.__class__.__name__)]
        if self._ordinal is not None:
            repr_str += ["'{}'".format(self.ordinal)]
        if self.verified:
            repr_str += ["[verified]"]
        repr_str += ["N={}".format(self.n_objects)]
        repr_str += ["({} for {})".format(self.n_closures, self.t_closures)]
        return " ".join(repr_str)
        
    @property
    def n_objects(self):
        """Number of regions held by this summary block."""
        return len(self)
        
    @property
    def n_closures(self):
        """Number of closures held by this summary block."""
        return sum([ len(region.openings) - 1 for region in self.values() ])
        
    @property
    def t_closures(self):
        """Total duration of closures held by this summary block."""
        return sum([ sum([ closure.duration.to('s').value for closure in region.closures ]) for region in self.values() ]) * u.second


class LCHRegions(collections.MutableMapping):
    """A dictionary interface for LCH regions."""
    def __init__(self, name):
        super(LCHRegions, self).__init__()
        self._summaries = {}
        self._summary = LCHSummaryGroup()
        self.name = name
        
    def __setitem__(self, key, value):
        """Set [key] = value"""
        self._summary.__setitem__(key, value)
        
    def __getitem__(self, key):
        """Get [key]"""
        if key in self._summary:
            return self._summary.__getitem__(key)
        for summary in self._summaries.values():
            if key in summary:
                return summary.__getitem__(key)
        raise KeyError("Key '{}' not in {}".format(key, self))
                
    def __delitem__(self, key):
        """Delete an item."""
        if key in self._summary:
            return self._summary.__delitem__(key)
        for summary in self._summaries.values():
            if key in summary:
                return summary.__delitem__(key)
        raise KeyError("Key '{}' not in {}".format(key, self))
        
    def __len__(self):
        """Length of this."""
        return sum([ len(summary) for summary in self._summaries.values() + [self._summary] ])
        
    def __iter__(self):
        """Iterator."""
        return itertools.chain.from_iterable([ iter(summary) for summary in self._summaries.values() + [self._summary] ])
        
    def verify(self, ordinal = None, objects = None, number = None, time = None):
        """Verify this summary."""
        if number is not None:
            self._summary.verify_count(ordinal, objects, number)
        if time is not None:
            self._summary.verify_duration(ordinal, objects, time)
        if self._summary.verified:
            self._summaries[self._summary.ordinal] = self._summary
            self._summary = LCHSummaryGroup()

class LCHClosureParser(object):
    """Closure Parsing State"""
    
    def __init__(self, name, date=None):
        super(LCHClosureParser, self).__init__()
        self._name = name
        self._date = date
        self.reset()
        
    def reset(self):
        """Reset the parser"""
        self._next_line = "header"
        self._this_line = None
        self._regions = LCHRegions(self._name)
        self._current_region = None
        self._line_number = 0
    
    def _warn(self, message):
        """Emit a formatted warning."""
        template = "[{name:s} line {ln:d}][{this:s}]{message:s}"
        warnings.warn(message.format(
            name = self._name,
            ln = self._line_number,
            this = self._this_line,
            message = message
        ))
    
    def header(self, text):
        """Handle the header line."""
        self._next_line = "blank"
        
    def blank(self, text):
        """Handle a blank line."""
        self._next_line = "starlist"
        
    def summary(self, text):
        """Handle a summary line."""
        self._next_line = "unknown"
        # data = parse_summary_line(text)
        # self._regions.verify(**data)
        
    def starlist(self, text):
        """Parse a starlist line."""
        self._next_line = "opening"
        self._current_region = Region.from_starlist(text)
        self._regions[self._current_region.name] = self._current_region
        
    def opening(self, text):
        """Parse an opening line."""
        self._next_line = "unknown"
        opening = Opening.from_openings(self._current_region, text)
        
    def __call__(self, stream):
        """Parse a stream line."""
        self.reset()
        for line in stream:
            self.parse_line(line)
        return self._regions
        
    def parse_line(self, text):
        """Parse a string/file."""
        text = text.strip()
        self._line_number += 1
        if self._next_line == "unknown":
            if re.match(r"^[\s]*$", text):
                self._this_line = "blank"
                self.blank(text)
            elif re.match(r"^[\s]*First", text):
                self._this_line = "summary"
                self.summary(text)
            else:
                self._this_line = "opening"
                self.opening(text)
        else:
            self._this_line = self._next_line
            getattr(self, self._this_line)(text)
        
    @classmethod
    def parse_file(cls, filename, date=None):
        """Parse a whole closure file."""
        parser = cls(filename, date)
        with open(filename, 'r') as stream:
            return parser(stream)
    
_openings_re = re.compile(
    r"""
    ^[\s]*(?P<Start>[\d]{2}:[\d]{2}:[\d]{2}) # Start time
    [\s]*(?P<End>[\d]{2}:[\d]{2}:[\d]{2})    # End time
    [\s]*open\(min:sec\)\ (?P<Opening>[\d]{2,4}:[\d]{2}) # Opening duration
    [\s]*(?:Closure\(sec\)[\s]*(?P<Closure>[\d]+))? # Closure duration
    """,
    re.VERBOSE
)

def parse_openings_line(line, date=Time.now()):
    """Parse an openings line.
    
    :param line: The text line to parse as an opening.
    :param date: The date for this openings line.
    """
    
    # Setup the reference date
    date = Time.now() if date is None else date
    date.out_subfmt = 'date'
    date_str = date.iso
    
    # Match the regular expression.
    match = _openings_re.match(line)
    if not match:
        raise ValueError("Can't parse line as opening: '{}'".format(line))
    data = match.groupdict("")
    
    # Handle date types
    for time_key in "Start End".split():
        data[time_key] = Time("{date:s} {time:s}".format(date=date_str, time=data[time_key]), scale='utc')
        
    # Handle quantity types
    for delta_key in "Opening Closure".split():
        if delta_key in data and len(data[delta_key]):
            if ":" in data[delta_key]:
                minutes, seconds = map(float,data[delta_key].split(":"))
            else:
                minutes = 0
                seconds = float(data[delta_key])
            data[delta_key] = minutes * u.minute + seconds * u.second
    
    return data

_summary_line_re = re.compile(r"""
    ^[\s]*(?P<ordinal>[\w]+)[\s]+(?P<objects>[\d]+)[\s]+objects\:[\s]+ # Number of objects
    # Only one of the two following options will appear in a closure line.
    (?:total\ time\ of\ closures:[\s]+(?P<time>[\d]+(?:\.[\d]+)?))| # Closure time
    (?:total\ number\ of\ closures:[\s]+(?P<number>[\d]+)) # Number of closures
    
    [\s]*$ # End the line.
    """, re.VERBOSE)
    
def parse_summary_line(line):
    """Parse a summary line."""
    match = _summary_line_re.match(line)
    if not match:
        raise ValueError("Can't parse line as summary: '{}'".format(line))
    data = match.groupdict()
    
    # Handle Time
    if data["time"] is not None:
        data["time"] = float(data["time"]) * u.second
    else:
        del data["time"]
    
    # Handle Number
    if data["number"] is not None:
        data["number"] = int(data["number"])
    else:
        del data["number"]
    
    data["objects"] = int(data["objects"])
    return data
    
def parse_closures_list(stream, name = "<stream>", date=None):
    """Parse a closure list"""
    parser = LCHClosureParser(name, date)
    return parser(stream).values()
            
def upcoming_closures(regions, limit = 1 * u.hour, when = Time.now()):
    """Yield upcoming closures."""
    upcoming = []
    for region in regions:
        for closure in region.closures:
            till_start = closure.start - when
            till_finish = closure.end - when
            if (till_start > 0 * u.s and till_start < limit) or (till_finish > 0 * u.s and till_finish < limit):
                upcoming.append(closure)
    upcoming.sort(key = lambda o : o.start)
    return upcoming