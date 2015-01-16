# -*- coding: utf-8 -*-
# 
#  visibility.py
#  pyobserver
#  
#  Created by Alexander Rudy on 2014-03-03.
#  Copyright 2014 Alexander Rudy. All rights reserved.
# 


from __future__ import (absolute_import, unicode_literals, division,
                        print_function)

import numpy as np
import pytz
import datetime
import astropy.units as u
import astropy.time
import astropy.table
from astropy.utils.console import ProgressBar
import pandas as pd
from astropyephem.targets import Sun, Moon
from astropy.coordinates import SkyCoord
import sys
import warnings
import matplotlib
import matplotlib.dates

from ..closures import FixedRegion

def latex_verbose(text):
    """Make LaTeX verbose text if matplotlib is using TeX for rendering."""
    if matplotlib.rcParams['text.usetex']:
        return r"\verb|{:s}|".format(text)
    else:
        return "{:s}".format(text)

class Night(object):
    """An object to represent an observing night."""
    
    _sun = Sun()
    _moon = Moon()
    
    def __init__(self, observer, date):
        super(Night, self).__init__()
        self.observer = observer
        self.date = date
        
    def __repr__(self):
        repr_str = "<{}".format(self.__class__.__name__)
        if hasattr(self, '_date'):
            repr_str += " @{0:%Y-%m-%d}".format(self.date.datetime)
            repr_str += " for {0.value:.1f} {0.unit}".format(self.length.to(u.hour))
        return repr_str + ">"
        
    @property
    def date(self):
        """Date"""
        return self._date
        
    @date.setter
    def date(self, value):
        """Set the date, night start and night end."""
        self._date = value
        self.observer.date = value
        self.end = self.observer.next_rising(self.sun)
        self.observer.date = self.end
        self.start = self.observer.previous_setting(self.sun)
        
    @property
    def length(self):
        """Night length."""
        return self.end - self.start
        
    @property
    def sun(self):
        """The state of the sun on this night."""
        self._sun.compute(self.observer)
        return self._sun
        
    @property
    def moon(self):
        """The state of the sun on this night."""
        self._moon.compute(self.observer)
        return self._moon
        
    def times(self, increment):
        """Iterate through a night at a given increment, from sunset to sunrise."""
        data = []
        for i in range(int((self.length.to(u.day)/increment).to(1)) + 1):
            data.append(self.start + increment * i)
        data.append(self.end)
        return astropy.time.Time([ d.datetime for d in data ], scale='utc')
        
    @staticmethod
    def extract_value(attr_value, attr_unit):
        """Extract value in unit"""
        return attr_value
        
    def collect(self, target, increment, attrs, timecol='Time'):
        """Collect a list of attributes across a target over a night."""
        times = self.times(increment)
        result = {}
        self.observer.date = self.start
        target.compute(self.observer)
        for attr in attrs:
            attr_value = getattr(target, attr)
            result[attr] = np.zeros((len(times),), dtype=getattr(attr_value, 'dtype', type(attr_value))) * getattr(attr_value, 'unit', 0)
        
        for i, time in enumerate(times):
            self.observer.date = time
            target.compute(self.observer)
            for attr in attrs:
                result[attr][i] = getattr(target, attr)
        result[timecol] = [ time.datetime for time in times ]
        return pd.DataFrame(result)


def airmass(altitude):
    """Compute airmass from altitude."""
    zenith_angle = 90 * u.degree - altitude
    airmass = 1.0 / np.cos(zenith_angle)
    return airmass
    
def setup_dual_axis(ax1, top=True):
    """Set up an axis for dual-scales.
    
    Dual scales are those where the left and right y-axes refer to the same
    data, and the top and bottom x-axes refer to the same data. The plot
    then shows two related scales.
    
    This method uses the private :meth:`~matplotlib.axes.Axes._make_twin_axes` command, then changes
    thea axis behaviors using normal matplotlib commands.
    
    """
    ax2 = ax1._make_twin_axes()
    
    # New X-Axis
    ax2.xaxis.tick_top()
    ax2.xaxis.set_label_position('top')
    
    # New Y-Axis
    ax2.yaxis.tick_right()
    ax2.yaxis.set_label_position('right')
    ax2.yaxis.set_offset_position('right')
    
    
    # Hide the patch of the top axis
    if top:
        ax1.patch.set_visible(False)
    else:
        ax2.patch.set_visible(False)
    
    # Tick only where necessary on the old axis.
    ax1.xaxis.tick_bottom()
    ax1.yaxis.tick_left()
    if top:
        ax1.set_zorder(ax2.get_zorder()+1)
    
    return (ax1, ax2)

class EphemerisPlotBase(object):
    """Base class for Ephemeris Plotting"""
    
    def setup_dual_axis(self, ax):
        """Setup a dual axis for use with the airmass chart."""
        ax, ax2 = setup_dual_axis(ax)
        return ax2
    
    @staticmethod
    def format_timezone_axis(axis, timezone, label="Time", fmt=None):
        """Set up an axis with formatters for a specific timezone."""
        import matplotlib.dates
        if not isinstance(timezone, datetime.tzinfo):
            timezone = pytz.timezone(timezone)
        date_locator = matplotlib.dates.AutoDateLocator()
        if fmt is None:
            date_formatter = matplotlib.dates.AutoDateFormatter(date_locator, tz=timezone)
        else:
            date_formatter = matplotlib.dates.DateFormatter(fmt, tz=timezone)
        axis.set_major_locator(date_locator)
        axis.set_major_formatter(date_formatter)
        if label:
            axis.set_label_text("{0:s} ({1:s})".format(label, timezone))
        
    @staticmethod
    def format_units_axis(axis, unit, label=""):
        """Set an axis to have unit formatting."""
        import matplotlib.ticker
        if matplotlib.rcParams['text.usetex']:
            unit_formatter = matplotlib.ticker.FuncFormatter(lambda x,p: "{0.value} {0.unit:latex}".format(x * unit))
        else:
            unit_formatter = matplotlib.ticker.FuncFormatter(lambda x,p: "{0.value} {0.unit:unicode}".format(x * unit))
        axis.set_major_formatter(unit_formatter)
        if label and matplotlib.rcParams['text.usetex']:
            axis.set_label_text("{0:s} ({1:latex})".format(label, unit))
        elif label:
            axis.set_label_text("{0:s} ({1:unicode})".format(label, unit))
            
        
    @staticmethod
    def format_airmass_axis(axis, unit, label=r"Airmass sec(z)"):
        """Format an axis in airmass."""
        import matplotlib.ticker
        airmass_formatter = matplotlib.ticker.FuncFormatter(lambda x,p: "{0.value:.2f}".format(airmass(x * u.degree)))
        axis.set_major_formatter(airmass_formatter)
        if label:
            axis.set_label_text(label)


class ObservabilityPlot(EphemerisPlotBase):
    """A plot of observability throughout a Semester."""
    def __init__(self, observer):
        super(ObservabilityPlot, self).__init__()
        self.observer = observer
        

def _console_output_functions(output):
    """Prepare console output functions."""
    if hasattr(output, 'write') and hasattr(output, 'flush'):
        stream = output
    else:
        stream = sys.stdout
    
    def progress():
        if output:
            stream.write(".")
            stream.flush()
            
    def finish():
        if output:
            stream.write("\n")
            stream.flush()
    
    return progress, finish, stream

class VisibilityPlot(EphemerisPlotBase):
    """A single observing night at a specific observatory."""
    
    increment = 6 * u.minute
    
    def __init__(self, observer, date):
        super(VisibilityPlot, self).__init__()
        self.night = Night(observer, date)
        self.targets = list()
        self._lines = set()
        
    def add(self, target):
        """Add a target."""
        if target not in self.targets:
            self.targets.append(target)
    
    def filter_gs_targets(self, sep=(2 * u.arcmin), targetfilter=lambda target : True):
        """Find science targets and eliminate GS/TT targets"""
        targets = {}
        for target in self.targets:
            if not targetfilter(target):
                continue
            if target.name not in targets:
                # Trying a new target.
                found_target = False
                
                for other_target in targets.values():
                    
                    # Only act if we are close to the other target.
                    if other_target.fixed_position.separation(target.fixed_position) <= sep:
                        found_target = True
                        if hasattr(other_target, 'lgs'):
                            continue
                        if hasattr(target, 'lgs'):
                            targets[target.name] = target
                            targets.pop(other_target.name)
                            continue
                        if hasattr(other_target, 'rmag'):
                            targets[target.name] = target
                            targets.pop(other_target.name)
                            continue
                        if hasattr(target, 'rmag'):
                            continue
                        warnings.warn("Two close targets found: {} and {}, can't differentiatie between them. Using first one: {}".format(
                            other_target.name, target.name, other_target.name
                        ))
                if not found_target:
                    targets[target.name] = target
            else:
                warnings.warn("Two targets with the same name found: {!r} and {!r}".format(target, targets[target.name]))
            
        return targets.values()
        
    def teardown_pickers(self):
        """docstring for teardown_pickers"""
        self._canvas.mpl_disconnect(self._connection)
        
    def setup_pickers(self, ax):
        """Set up target line pickers."""
        for artist in self._lines:
            artist.set_picker(5.0)
        self._canvas = ax.figure.canvas
        self._connection = self._canvas.mpl_connect('pick_event', self.on_pick)
        self._annotation = None
        self._marker = None
        self._last_pick = None
        self._timeline = ax.axvline(datetime.datetime.utcnow(), color='k', zorder=0.1, alpha=0.75)
        
    def time_now(self):
        """Return a tuple of (utc, local) datetime objects."""
        utc_now = pytz.UTC.localize(datetime.datetime.utcnow())
        local_now = utc_now.astimezone(self.night.observer.timezone)
        return (utc_now, local_now)
        
    def clock_text(self):
        """Get the pair of clock texts."""
        utc_now, local_now = self.time_now()
        local_tz = self.night.observer.timezone
        utc_tz = pytz.UTC
        local_text = "{0:%Y/%m/%d} {0:%H:%M:%S} {1:s}".format(local_now, local_tz)
        utc_text = "{0:%Y/%m/%d} {0:%H:%M:%S} {1:s}".format(utc_now, utc_tz)
        return (utc_text, local_text)
        
        
    def setup_clock(self, ax):
        """Set up the clock display."""
        utc, local = self.clock_text()
        self._local_text = ax.text(1+0.35/2, -0.01, local, transform=ax.transAxes, va='bottom', ha='center')
        self._utc_text = ax.text(1+0.35/2, 0.05, utc, transform=ax.transAxes, va='bottom', ha='center')
        self._clock_timer = ax.figure.canvas.new_timer(interval=100)
        self._clock_timer.add_callback(self.update_clock)
        self._clock_timer.add_callback(self.refresh_timeline, ax)
        self._clock_timer.start()
        
    def update_clock(self):
        """docstring for update_clock"""
        utc, local = self.clock_text()
        self._utc_text.set_text(utc)
        self._local_text.set_text(local)
        self._canvas.draw()
        
    def refresh_timeline(self, ax):
        """Refresh a timeline on an axes."""
        now = datetime.datetime.utcnow()
        self._timeline.set_xdata([now, now])
    
    def on_pick(self, event):
        """Action to take on a pick event."""
        if event.artist not in self._lines:
            return
            
        # Unpack the event information.
        artist = event.artist
        x, y = event.mouseevent.xdata, event.mouseevent.ydata
        ax = artist.axes
        
        # Get the distance to the nearest point on the line.
        xd, yd = artist.get_data()
        xp, yp = xd[event.ind[0]], yd[event.ind[0]]
        
        # Transform into display coordinates.
        xf, yf = ax.transData.transform((matplotlib.dates.date2num(xp), yp))
        
        # Deterime if the last click was actually closer to 
        # the line than this one.
        if self._last_pick is not None:
            xm, ym = ax.transData.transform((x, y))
            this_distance = (xm-xf)**2 + (ym-yf)**2
            xl, yl = self._last_pick
            other_distance = (xm-xl)**2 + (ym-yl)**2
            if other_distance < this_distance:
                return
        
        self._last_pick = (xf, yf)
        
        # Remove the old annotations.  
        if self._annotation is not None:
            self._annotation.remove()
        if self._marker is not None:
            self._marker.remove()
        self._marker, = ax.plot(xp, yp, 'o')
        self._marker.set_color(artist.get_color())
        text = "\n".join([artist.get_label(), "Airmass: {0.value:.2f}".format(airmass(yp*u.degree)), "UT: {:}".format(xp.strftime("%H:%M"))])
        
        self._annotation = ax.annotate(
            s = text,
            xy = (xp, yp),
            xytext = (x, y + 3.0),
            size = 'small',
            bbox=dict(boxstyle="round", fc="white", ec=artist.get_color()),
        )
        
        self.refresh_timeline(ax)
        self._canvas.draw()
        
    def show_closures(self, region, alt):
        """Show the closures lines."""
        lines = []
        for closure in region.closures:
            s = (self._times > closure.start) & (self._times < closure.end)
            t = astropy.time.Time(np.concatenate((np.array([closure.start.datetime]), self._times[s].datetime, np.array([closure.end.datetime]))))
            a = np.interp(t.plot_date, self._times.plot_date, alt.to(self._unit).value) * self._unit
            l, = self._ax.plot(t.datetime, a.to(self._unit).value, 'r-', lw=3)
            lines.append(l)
        return tuple(lines)
    
    def show_target(self, target, moon_pos, moon_distance_spacing, moon_distance_maximum):
        """Show a single target on the visibility plotter."""
        altitude_angle = np.zeros((len(self._times),), dtype=float) * u.degree
        moon_distance = np.zeros((len(self._times),), dtype=float) * u.degree
        last_moon_distance = self.night.start
        for i,time in enumerate(self._times):
            
            # Compute this postion.
            self.night.observer.date = time
            target.compute(self.night.observer)
            altitude_angle[i] = target.alt
            moon_distance[i] = moon_pos[i].separation(target.position)
            
            # Only add the moon distance every few minutes, and when the moon is realtively close to the object
            if ((last_moon_distance + moon_distance_spacing <= time) and 
                (altitude_angle[i] >= self._text_el_limit and moon_distance[i] <= moon_distance_maximum)):                    
                annotate = self._ax.annotate(
                    s = "{0.value:0.0f} {0.unit:latex}".format(moon_distance[i]),
                    xy = (time.datetime, altitude_angle[i].to(self._unit).value),
                    xytext = [-5.0, 0.0],
                    textcoords = 'offset points',
                    size = 'x-small',
                    alpha = 0.5)
                last_moon_distance = time
        
        # Finally, do the plotting!
        target_z, = self._ax_z.plot(self._times.datetime, altitude_angle.to(self._unit).value, ':')                
        target_l, = self._ax.plot(self._times.datetime, altitude_angle.to(self._unit).value, '-', label=latex_verbose(target.name))
        if isinstance(target, FixedRegion):
            self.show_closures(target, altitude_angle)
        self._lines.add(target_l)
        
    def show_moon(self):
        """Show the moon."""
        moon_pos = []
        altitude_angle = np.zeros((len(self._times),), dtype=float) * u.degree
        for i, time in enumerate(self._times):
            self.night.observer.date = time
            moon_pos.append(self.night.moon.position)
            altitude_angle[i] = self.night.moon.alt
        moon_z, = self._ax_z.plot(self._times.datetime, altitude_angle.to(self._unit).value, 'k--', alpha=0.0)
        moon, = self._ax.plot(self._times.datetime, altitude_angle.to(self._unit).value, 'k--', label=r"Moon", alpha=0.5)
        self._lines.add(moon)
        return SkyCoord([ m.ra for m in moon_pos],[ m.dec for m in moon_pos ], frame='icrs')
    
    def show_sunrise_sunset(self):
        """Show the sunrise and sunset times."""
        # Sunrise and Sunset lines.
        xmin, xmax = (self.night.start - 1.0 * u.hour), (self.night.end + 1.0 * u.hour)
        self._ax.set_xlim(xmin.datetime, xmax.datetime)
        self._ax.axvspan(xmin.datetime, self.night.start.datetime, color='k', alpha=0.2)
        self._ax.axvspan(xmax.datetime, self.night.end.datetime, color='k', alpha=0.2)
        
        # Label Bright Zones
        self._ax.text(0.02, 0.5, "Before Sunset", transform=self._ax.transAxes, va='center', ha='left', rotation=90)
        self._ax.text(0.98, 0.5, "After Sunrise", transform=self._ax.transAxes, va='center', ha='right', rotation=90)
    
    def format_xaxes(self):
        """Format the xaxes."""
        self._ax.xaxis.tick_bottom()
        self._ax.xaxis.set_label_position('bottom')
        self.format_timezone_axis(self._ax.xaxis, "UTC", fmt="%H:%M")
        
        # Add dates to UTC axis.
        self._ax.text(-0.015, -0.05, "{0.datetime:%Y/%m/%d}".format(self.night.start), transform=self._ax.transAxes, va='top', ha='right',
             color='k')
        self._ax.text(1.02, -0.05, "{0.datetime:%Y/%m/%d}".format(self.night.end), transform=self._ax.transAxes, va='top', ha='left',
             color='k')
        
        # 2nd Axis Formatting
        self._ax_z.xaxis.tick_top()
        self._ax_z.xaxis.set_visible(True)
        self._ax_z.xaxis.set_label_position('top')
        self.format_timezone_axis(self._ax_z.xaxis, self.night.observer.timezone, fmt="%H:%M")
        
        # Add dates to localtime axis.
        local_tz = self.night.observer.timezone
        utc_tz = pytz.UTC
        local_start = utc_tz.localize(self.night.start.datetime).astimezone(local_tz)
        local_end = utc_tz.localize(self.night.end.datetime).astimezone(local_tz)
        self._ax.text(-0.015, 1.05, "{0:%Y/%m/%d}".format(local_start), transform=self._ax.transAxes, va='bottom', ha='right',)
        self._ax.text(1.02, 1.05, "{0:%Y/%m/%d}".format(local_end), transform=self._ax.transAxes, va='bottom', ha='left',)
        self._ax.text(1+0.35/2, 0.02, "{0:s}".format(self.night.observer.name), transform=self._ax.transAxes, va='bottom', ha='center',)
        
    
    
    def __call__(self, ax, el=(1.0 * u.degree, 90 * u.degree), unit=u.degree, legend="Outside",
                    moon_distance_spacing=(60 * u.minute), moon_distance_maximum=(50 * u.degree),
                    output=False, min_elevation = None):
        """Make a visibility plot on a given axes object."""
        if hasattr(self, '_ax') and self._ax is not None:
            raise ValueError("Can't re-plot!")
        
        # Persist a few settings.
        self._unit = unit
        self._times = self.night.times(self.increment)
        
        # Values for the elevation limits.
        ylim_values = (el[0].to(unit).value, el[1].to(unit).value)
        self._text_el_limit = el[0] + 0.1 * (el[1] - el[0])
        
        # Set up the axes.
        self._ax = ax
        self._ax_z = self.setup_dual_axis(ax)
        
        progress, finish, stream = _console_output_functions(output)
            
        # Handle the moon.
        moon_pos = self.show_moon()
        
        # Show the targets.
        for target in ProgressBar(self.targets, file=stream):
            self.show_target(target, moon_pos, moon_distance_spacing, moon_distance_maximum)
        
        self.show_sunrise_sunset()
        
        if min_elevation is not None:
            # Label minimum elevation
            ax.axhline(u.Quantity(min_elevation, u.degree).to(u.degree).value, ls=':', lw = 2, color = 'r', alpha = 0.75, label="Minimum Elevation")
        
        # Axis formatting
        self._ax.grid(True, axis='both')
        self.format_xaxes()
        self.format_units_axis(self._ax.yaxis, unit, "Elevation")
        self.format_airmass_axis(self._ax_z.yaxis, unit)
        
        # Axis limits
        self._ax.set_ylim(*ylim_values)
        # We have to keep the 2nd axis limits in sync with the first axis, by hand.
        self._ax_z.set_ylim(*self._ax.get_ylim())
        self._ax_z.set_xlim(*self._ax.get_xlim())
        
        # Apply the legend.
        legend_bboxes = {
            'Outside' : (0.0, 0.0, 1.35, 1.0), # l b w h
            'Inside' : (0.0, 0.0, 1.0, 1.0),
        }
        
        ax.legend(bbox_to_anchor=legend_bboxes[legend], fontsize=8, title="Targets")
        
        