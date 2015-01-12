# -*- coding: utf-8 -*-
# 
#  nirc2script.py
#  pynirc2
#  
#  Created by Alexander Rudy on 2012-12-21.
#  Copyright 2012 Alexander Rudy. All rights reserved.
# 
from __future__ import division, unicode_literals
from modgrammar import (Grammar, L, WORD, OPTIONAL, OR, EOL, REPEAT, EMPTY, REST_OF_LINE, SPACE, ANY, EXCEPT)
from pyshell import CLIEngine
import collections
import re
import six
import json
import os
from astropy.table import Table, vstack
from six import StringIO

from textwrap import fill

grammar_whitespace_mode = 'optional'

class ParseScript(CLIEngine):
    """Parse an observing script for statistics"""
        
    help = """Parse a NIRC2 Observing Script to estimate overheads."""
    
    description = fill("""Uses the NIRC2 instrument tools to parse a NIRC2 script and return overhead and resulting integration time.""")
        
    def configure(self):
        super(ParseScript, self).configure()
        self.parser.add_argument('script',help="script file name.",action='store', type=six.text_type)
        self.parser.add_argument('--ipy',help="expect an iPython notebook",action='store_true')
        self.parser.add_argument('-o',help="Set output script name",action='store',dest='output',default=False)
        
        
    def _from_ipynb(self,filename):
        """Return source stream from an ipython notebook."""
        with open(filename,'r') as stream:
            self.source_json = json.load(stream)
        
        script = ""
        
        for cell in self.source_json["worksheets"][0]["cells"]:
            if cell["cell_type"] == "markdown":
                cell_source = cell["source"]
                for line in cell_source:
                    if line.startswith("    ") or line.startswith("\t"):
                        script += line.lstrip(" \t")
        
        return script.rstrip("\n")
        
    def _to_ipynb(self,filename):
        """Write the original JSON back to ipynb format, with a timing summary cell"""
        
        cells = self.source_json["worksheets"][0]["cells"][:]
        cells.reverse()
        # Find the last heading cell, and see if it is a Timing Summary
        found = False
        for i,cell in enumerate(cells):
            if cell["cell_type"] == "heading":
                cell_source = cell["source"]
                if cell_source[0] == "Timing Summary":
                    found = True
                    break
        
        if not found or i == 0:
            head_cell = {
                'cell_type': "heading",
                'level' : 3,
                'metadata' : {},
                'source' : ["Timing Summary"],
            }
            if i == 0:
                self.source_json["worksheets"][0]["cells"][-1] = head_cell
            else:
                self.source_json["worksheets"][0]["cells"].append(head_cell)
            self.source_json["worksheets"][0]["cells"].append({
                'cell_type': "raw",
                'metadata' : {},
                'source' : map(lambda l : l+"\n",self.summary),
            })
        else:
            hn = len(cells) - i
            self.source_json["worksheets"][0]["cells"][hn]["source"] = map(lambda l : l+"\n",self.summary)
            self.source_json["worksheets"][0]["cells"][hn]["cell_type"] = "raw"
            
        with open(filename,'w') as stream:
            json.dump(self.source_json,stream)
        
    def do(self):
        """Parse the script"""
        self.sparser = Script.parser()
        
        root,extension = os.path.splitext(self.opts.script)
        
        if extension == ".ipynb" or self.opts.ipy:
            self.source = StringIO(self._from_ipynb(self.opts.script))
        else:            
            with open(self.opts.script,"r") as stream:
                self.source = StringIO(stream.read())
            
        self.results = self.sparser.parse_string(self.source.read(),eof=True)
        
        if not self.results:
            print "No RESULTS FOUND!"
        
        if len(self.sparser.remainder()) > 0:
            print "---UNPARSED---"
            print "".join(self.sparser.remainder())
            print "--------------"
        self.state = self.results.execute()
        self.state.summary()
        self.finish()
        
    def finish(self):
        """Print out summary tables"""
        self.summary = []
        self.summary += ["For script '%s':" % self.opts.script]
        subtotal = self.state.subtotal().pformat(max_width=120, show_unit=False)
        self.summary += subtotal[:-2]
        self.summary += [subtotal[1]]
        self.summary += subtotal[-2:]
        
        if self.opts.output:
            root,extension = os.path.splitext(self.opts.output)
            if extension == ".ipynb":
                self._to_ipynb(self.opts.output)
            else:
                with open(self.opts.output,'w') as stream:
                    self.source.seek(0)
                    stream.write(self.source.read())
                    stream.write("\n#\n#")
                    stream.write("\n#".join(self.summary))
        else:
            print "\n".join(self.summary)


class ScriptError(Exception):
    """Exception scripting error"""
    pass

class NIRC2(object):
    """The state of the NIRC2 system.
    
    This state machine tracks the parsing of a nirc2 script"""
    def __init__(self):
        super(NIRC2, self).__init__()
        self.params = {}
        self.exposures = []
        self.commands = []
        self.output = []
        
    def summary(self):
        """Summary of exposure time/overhead by object."""
        zero = lambda : 0.0
        cols = "Object Imaging Acquisition Read Total".split()
        im_time = collections.defaultdict(zero)
        ac_time = collections.defaultdict(zero)
        rd_time = collections.defaultdict(zero)
        time = collections.defaultdict(zero)
        for exposure in self.exposures:
            im_time[exposure.object] += exposure.im_time
            ac_time[exposure.object] += exposure.ac_time
            rd_time[exposure.object] += exposure.rd_time
            time[exposure.object] += exposure.time
        objects = time.keys()
        objects.sort()
        
        table = Table([objects], names=('Objects',))
        for col, data in zip(cols[1:], (im_time, ac_time, rd_time, time)):
            table[col] = [ data[obj] for obj in objects ]
            table[col].format = "{0:.1f}"
        self.table = table
        return table
        
    def expose(self, **kwargs):
        """Track a new individual exposure."""
        params = dict(**self.params)
        params.update(kwargs)
        self.exposures.append(Exposure(**params))
    
    @property
    def nd_time(self):
        """Summary of non-dark time"""
        nd_time = collections.defaultdict(lambda : 0.0)
        for r,obj in enumerate(self.table["Object"]):
            if obj != "dark":
                nd_time[obj] = self.table["Total"][r]
        return nd_time
        
    def subtotal(self):
        """Total table"""
        subtotal = Table([["Total", "(min)"]], names=('Objects',))
        for col in self.table.colnames[1:]:
            total = sum(self.table[col]) 
            subtotal[col] = [ total, total/60.0 ]
            subtotal[col].format = "{0:.1f}"
        
        
        return vstack((self.table, subtotal))

class Exposure(object):
    def __init__(self, **kwargs):
        super(Exposure, self).__init__()
        self.params = kwargs
        try:
            self.ndither = self.params.get("ndither",1)
            self.nframes = self.params.get("nframes",1)
            self.coadd = self.params.get("coadds",1)
            self.nread = self.params.get("nreads",2)
            self.tread = self.params.get("tread",0.18)
            self.tint = self.params["tint"]
            self.object = self.params["object"]
            self.wait4ao = self.params["wait4ao"]
            self.ao = "with AO" if self.wait4ao else ""
        except KeyError as ke:
            raise ScriptError("Exposure must have %r set!" % ke.args[0])
        
    def __str__(self):
        return "%(ndither)d dither x %(coadd)d x %(tint)ds exposure of %(object)s %(ao)s" % self.__dict__
        
    def __repr__(self):
        return "<Exposure '%s' >" % str(self)
        
    @property
    def ac_time(self):
        return 6. * (self.ndither + 1) + 12.*self.ndither*self.nframes
    
    @property
    def rd_time(self):
        return self.ndither*self.nframes*self.coadd*(self.tread * (self.nread - 1))
        
    @property
    def im_time(self):
        return self.ndither*self.nframes*self.coadd*self.tint
        
    @property
    def time(self):
        return self.ac_time + self.rd_time + self.im_time
        
class N2Grammar(Grammar):
    
    kwtarget = tuple()
    
    @property
    def keyword(self):
        return self.elements[0].string
    
    def execute(self,state):
        """execute for keyword"""
        parsed = self.find(*self.kwtarget)
        if parsed is not None:
            state.params[self.keyword] = parsed.value
        elif self.keyword in state.params:
            state.output.append("%s = %s" % (self.keyword,state.params[self.keyword]))
        else:
            state.output.append("%s = KEYWORD NOT SET" % (self.keyword))

class INT(Grammar):
    """Integer"""
    grammar = (WORD("0123456789"),)
    
    @property
    def value(self):
        return int(str(self))

class NUM(Grammar):
    grammar = (WORD("0123456789."),)
    
    @property
    def value(self):
        return float(str(self))

class BOOL(Grammar):
    grammar = (L("on") | L("off"),)
    
    @property
    def value(self):
        if str(self) == "on":
            return True
        elif str(self) == "off":
            return False
            
class KWValue(Grammar):
    grammar = (OR(INT,NUM,BOOL),)
    
    @property
    def value(self):
        return self.elements[0].value

class Coadd(N2Grammar):
    grammar = (L("coadds") | L("coadd"), OPTIONAL(INT))
    kwtarget = (INT,)

class NGoi(Grammar):
    grammar = (INT,)

class Goi(Grammar):
    grammar = (L("goi"),OPTIONAL(NGoi))
    
    def execute(self,state):
        if self.find(NGoi) is not None:
            ngoi = self.find(NGoi,INT).value
        else:
            ngoi = 1
        for i in range(ngoi):
            state.expose()
        return state

class ObjectName(Grammar):
    grammar = (WORD("A-Za-z","A-Za-z0-9_\-"))
    
    @property
    def value(self):
        return self.string
    
class Object(N2Grammar):
    grammar = (L("object"),ObjectName)
    kwtarget = (ObjectName,)
    
class Rotate(N2Grammar):
    grammar = (L("rotate"),OPTIONAL(INT))
    kwtarget = (INT,)
    
class CameraVal(N2Grammar):
    grammar = (L("wide") | L("narrow"),)
    
    @property
    def value(self):
        return self.string
    
class Camera(N2Grammar):
    grammar = (L("camera"),CameraVal)
    kwtarget = (CameraVal,)
    
class Tint(N2Grammar):
    grammar = (L("tint"),OPTIONAL(NUM))
    kwtarget = (NUM,)
    
class KeyValuePair(Grammar):
    """A keyword-value pair."""
    grammar = (WORD("A-Za-z","A-Za-z0-9_\-"),L("="),KWValue)
    kwtarget = (KWValue,)
    
class Modify(N2Grammar):
    """Direct keyword modification"""
    grammar = (L("modify"), L("-s"), REPEAT(KeyValuePair))
    
    def execute(self, state):
        """Don't do anything for modify."""
        for element in self.find_all(KeyValuePair):
            element.execute(state)
    
class ConfigAOforFlats(Grammar):
    """Direct keyword modification"""
    grammar = (L("configAOforFlats"),)
    
    def execute(self, state):
        """Don't do anything for modify."""
        pass
    
class SampmodeVal(Grammar):
    grammar = ( (INT, OPTIONAL(INT)) | L("CDS") | (L("MCDS"), OPTIONAL(INT)),)
    
    @property
    def mode(self):
        return self.elements[0].string
    
class Sampmode(Grammar):
    grammar = (L("sampmode"),OPTIONAL(SampmodeVal))
    
    def execute(self,state):
        if self.find(SampmodeVal):
            smv = self.find(SampmodeVal)
            if len(smv.elements) == 2:
                state.params['nreads'] = smv.elements[1].value
            else:
                state.params.setdefault("nreads",2)
            state.params["sampmode"] = smv.mode
        else:
            state.output.append("sampmode = %s" % params["sampmode"])
        return state
            
class Filter(Grammar):
    filters = "kp Kp J j H h".split()
    grammar = (OR(*tuple(map(L,filters))),)
    
    @property
    def value(self):
        return self.string

class Filt(N2Grammar):
    grammar = (L("filt"),OPTIONAL(Filter))
    kwtarget = (Filter,)
        
class NKWD(Grammar):
    grammar = (L("n="),INT)
    
    @property
    def value(self):
        return self.get(INT).value

class DitherLength(Grammar):
    grammar = (NUM,OPTIONAL(NUM))
    
    @property
    def value(self):
        d = [element.value for element in self.find_all(NUM)]
        if len(d) == 1:
            d += d
        return d

class Dither(Grammar):
    ndither = { "bxy{:d}".format(i) : i for i in range(2,6) }
    grammar = (OR(*tuple(map(L,ndither.keys()))),DitherLength,OPTIONAL(NKWD))
    
    def execute(self,state):
        if self.find(NKWD):
            state.params['nframes'] = self.find(NKWD).value
        else:
            state.params.setdefault('nframes', 1)
        
        state.params['xdither'] = self.get(DitherLength).value[0]
        state.params['ydither'] = self.get(DitherLength).value[1]
        state.params["ndither"] = self.ndither[self.elements[0].string]
        state.expose()
        state.params["ndither"] = 1
        state.params["nframes"] = 1
        return state
        
class WaitAO(N2Grammar):
    grammar = (L("wait4ao"),OPTIONAL(BOOL))
    kwtarget = (BOOL,)
    
    
class ShutterPos(Grammar):
    grammar = (L("close") | L("open"))
    
    def value(self):
        return self.string
        
class Shutter(N2Grammar):
    grammar = (L("shutter"),OPTIONAL(ShutterPos))
    kwtarget = (ShutterPos,)

class ShellCommand(Grammar):
    grammar = (WORD("A-Za-z","A-Za-z0-9_\-"),REPEAT(EXCEPT(ANY, L(";") | EOL)))
    
    def execute(self, state):
        """Execute this command"""
        pass

class Command(Grammar):
    grammar = ((Coadd | Goi | Object | Tint | Sampmode | Filt | Dither | WaitAO | Rotate | Camera | Shutter | Modify | ConfigAOforFlats | ShellCommand),OPTIONAL(L(";")))
    
    def execute(self,state):
        state.commands.append(self.string)
        state.output.append("$ %s" % self.string.rstrip("\n"))
        return self.elements[0].execute(state)
    
class Comment(Grammar):
    grammar = (L(";") | L("#"), REST_OF_LINE)
    

class BlankLine(SPACE):
    grammar_desc = "blank line"
    regexp = re.compile(r"[\s]*")
        

class CommandStatement(Grammar):
    grammar = ((Command | Comment | (SPACE + EOL) | EOL | L(";")),)

class Script(Grammar):
    grammar = (REPEAT(CommandStatement))
    
    def execute(self,state=None):
        if state is None:
            state = NIRC2()
        for command in self.find_all(Command):
            command.execute(state)
        return state