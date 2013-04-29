# -*- coding: utf-8 -*-
# 
#  fitsfiles.py
#  pynirc2
#  
#  Created by Alexander Rudy on 2013-02-15.
#  Copyright 2013 Alexander Rudy. All rights reserved.
# 
from __future__ import division, unicode_literals

from pyshell.subcommand import SCController, SCEngine
from pyshell.util import query_yes_no, force_dir_path, collapseuser, check_exists

import numpy as np
import pyfits as pf

import os, os.path, glob, sys
import re, ast
import warnings, logging
import datetime
import collections
from textwrap import fill

def silent_getheader(filename):
    """Get the headerfile without validation warnings.
    
    This is a simple wrapper function to silence warnings from PyFITS (which has gotten noisy) and to attempt to ignore inconsistencies in header validation. It seems that many instruments don't write strictly valid FITS headers, which is problematic, but not problematic enough that I want to see a warning every time I try to load one!"""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        header = pf.getheader(filename,ignore_missing_end=True)
    return header
    
class FITSHeaderTable(object):
    """Manages sets of FITS headers, search through them and collect approprate sets of information."""
    def __init__(self):
        super(FITSHeaderTable, self).__init__()
        self._collection = []
        self.files = []
        self._headers = []
        
    @property
    def collection(self):
        """The collected (and possibly filtered) set of files."""
        return self._collection
        
    def reset(self):
        """Reset this FITSHeaderTable to the post-read state.
        
        This simply reverts the ``collection`` attribute to its original value after :meth:`read` is called."""
        self._collection = self._headers
        
    def glob(self,globstring):
        """Use shell-style globbing (from :mod:`glob`) to assemble a list of files for loading."""
        self.files = glob.glob(globstring)
        
    def read(self,files=None,reset=True):
        """Get FITS Headers from each file in the `files` list (or stored from a call to :meth:`glob`).
        
        Files read in this method will appear in :attr:`collection` and :attr:`headers` as pyfits Header objects.
        
        :param files: The list of files to be loaded. If ``None``, use the prepared internal list of files.
        :param bool reset: ``True`` (default) will reset, not append to, the internal list of headers.
        """
        if files is not None:
            self.files = files
        if reset:
            self._headers = []
        with warnings.catch_warnings(record=True) as wlist:
            for file in self.files:
                header = silent_getheader(file)
                if "FILENAME" not in header:
                    header["FILENAME"] = (os.path.basename(file),'Original File name')
                if "OPENNAME" not in header:
                    header["OPENNAME"] = (os.path.relpath(file),'Opened File Name')
                self._headers.append(header)
        if not self._collection:
            self._collection = self._headers
        return self._headers
    
    def collect(self,*keywords):
        """Backwards compatibility for normalize header functions."""
        return self.normalize(keywords,blank="",warn=True,error=False)
    
    def normalize(self,keywords,blank="",warn=True,error=False):
        """Collect and normalize a set of headers by keyword.
        
        :args keywords: The keywords to search for.
        
        This function ensures that each collected header contains a minimal value for every requested keyword. The minimum value is by default the empty string. The function will raise a warning if the requested keyword is not present. This function acts on :attr:`collection` and returns the collection"""
        keywords = list(keywords)
        collection = []
        if "OPENNAME" not in keywords:
            keywords.append("OPENNAME")
        for header in self._collection:
            for key in keywords:
                if key not in header:
                    if error:
                        header[key] #Purposefully trigger a key error for missing header values
                    if warn:
                        warnings.warn("Couldn't find keyword '%s' in file '%s'" % (key,header["OPENNAME"]))
                    header[key] = blank
            collection.append(header)
        self._collection = collection
        return collection
        
    def search(self,**keywords):
        """Search for headers that match specific keyword values.
        
        :param keywords: Arbitrary keyword-style arguments specfiying the search criteria.
        
        All searches are performed with the "AND" operator. Keyword arguments should be of the form KEYWORD="search value" where "search value" can be one of the following types:
        - A string or other basic python literal. In this case, the keyword value is matched against the entire literal.
        - A regular expression object from :func:`re.compile`, where :meth:`match` is used to match the compiled regular expression to the keyword value.
        - A boolean value. True means that you only want headers which have the specified keyword. False means you only want headers which **don't** have the specified keyword. For ``False``, the keyword value will be normalized to the empty stirng (for logging/listing purposes). """ 
        collection = []
        if "OPENNAME" not in keywords:
            keywords["OPENNAME"] = True
        for header in self._collection:
            keep = True
            for key,search in keywords.iteritems():
                if key not in header and (search is not False):
                    warnings.warn("Couldn't find keyword '%s' in file '%s'" % (key,header["OPENNAME"]))
                    keep = False
                elif hasattr(search,'match'):
                    if not search.match(str(header[key])):
                        keep = False
                elif isinstance(search,bool):
                    if search and key in header:
                        pass
                    elif (not search) and (key not in header):
                        header[key] = ""
                    else:
                        keep = False
                elif search == header[key]:
                    pass
                else:
                    keep = False
            if keep:
                collection.append(header)
        self._collection = collection
        return collection
    
    def group(self,keys,key_fmt=None):
        """Using a list of keywords, collect groups of headers for which the value of each specified keyword matches among the whole group. This is done using a :class:`FITSDataGroups` object, and such an object is returned. :class:`FITSDataGroups` objects behave like sets, and so can be iterated over. To access individual elements, use the :meth:`FITSDataGroups.get` method."""
        if key_fmt is None:
            key_fmt = []
        groups = FITSDataGroups(keys,key_fmt)
        for header in self._collection:
            groups.add(header)
        self.groups = groups
        return groups
    
    def logstring(self,order=None,collection=None):
        """Create a log-file like string from a collection.
        
        :param collection: The collection to use. If ``None``, use the current internal collection."""
        if collection is None:
            collection = self._collection
        if order is None:
            order = collection[0].keys()
            order.sort()
        if "OPENNAME" in order:
            order.remove("OPENNAME")
        
        # Unfilled Format
        column_format = " {{{}!s:<20.20}} "
        fname_format = " {{{}:<30.30s}}"
        column_line = fname_format + column_format * (len(order))
        
        # List of keys in column order
        key_list = ["OPENNAME"] + order
        header_list = ["file"] + order
        header_data = dict(zip(key_list,header_list))
        
        # Format string ready for formatting
        column_keywords = column_line.format(*key_list)
        
        output = [column_keywords.format(**header_data)]
        for header in collection:
            output += [column_keywords.format(**header)]
        return output
        
    
    def liststring(self,collection=None):
        """Return a list of filenames from a collection."""
        if collection is None:
            collection = self._collection
        return [ header["OPENNAME"] for header in collection ]

class FITSDataGroups(collections.MutableSet):
    """A set of FITS data groups"""
    
    EMPTYFORMAT = "{!s}"
    
    def __init__(self,keywords,formats="{!s}"):
        super(FITSDataGroups, self).__init__()
        self._groups = {}
        self._keywords = keywords
        if isinstance(formats,list):
            _formats = formats
        else:
            _formats = [formats]
        if len(self._keywords) > len(_formats):
            _formats += [self.EMPTYFORMAT] * (len(self._keywords) - len(_formats))
        self._formats = []
        for format in _formats:
            if format is None:
                self._formats.append(self.EMPTYFORMAT)
            else:
                self._formats.append(format)
        
        
    def __iter__(self):
        """Iterable"""
        return self._groups.itervalues()
        
    def __len__(self):
        """Length"""
        return self._groups.__len__()
    
    def __contains__(self,item):
        """Check if this FITSDataGroups contains a specific item. Forms of item:
        
        pyfits header
        dictionary of header keywords and values
        string keyhash
        string groupname
        string filename
        """
        hhash = self.type_to_hash(item)
        if hhash not in self.hashes:
            return hhash in [group.name for group in self]
        else:
            return hhash in self.hashes
        
    @property
    def keywords(self):
        """docstring for keywords"""
        return self._keywords
        
    @property
    def formats(self):
        """docstring for formats"""
        return self._formats
        
    @property
    def hashes(self):
        """Return the data group's hashes"""
        return self._groups.keys()
        
    def get(self,hhash,value=None):
        """Return a specific data group"""
        return self._groups.get(hhash,value)
        
    def addlist(self,filename,asgroup=True):
        """docstring for addlist"""
        _files = []
        with open(filename,'r') as stream:
            for line in stream:
                fname = os.path.join(os.path.dirname(filename),line.rstrip("\n"))
                if not line.startswith("#") and os.path.exists(fname):
                    _files.append(fname)
        FHT = FITSHeaderTable()
        headers = FHT.read(_files)
        if len(headers) > 0 and not self.hasgroup(*headers):
            self.add(ListFITSDataGroup(filename,headers,self.keywords,self.formats))
             
        
        
    def isgroup(self,*headers):
        """docstring for isgroup"""
        headers = list(headers)
        header = headers.pop()
        masterhash = self.make_hash(header)
        for header in headers:
            if self.make_hash(header) != masterhash:
                return False
        return True
        
    def hasgroup(self,*headers):
        """docstring for findgroup"""
        if self.isgroup(*headers):
            khash = self.make_hash(headers[0])
            if khash in self:
                incfiles = self.get(khash).files
                incfiles.sort()
                hfiles = [ header["FILENAME"] for header in headers ]
                hfiles.sort()
                return hfiles == incfiles
        return False
        
    def islist(self,item):
        """Return whether this item is a list."""
        khash = self.type_to_hash(item)
        return isinstance(self._groups[khash],ListFITSDataGroup)
        
    def addmany(self,*items):
        """docstring for addmany"""
        return [self.add(item) for item in items]
            
        
    def add(self,item):
        """Add a data group"""
        
        if isinstance(item,FITSDataGroup):
            if item.keyhash not in self:
                self._groups[item.keyhash] = item
                return item.keyhash
            else:
                raise KeyError("DataGroup with hash {} already exists.".format(item.keyhash))
        hhash = self.type_to_hash(item)
        if item not in self:
            self._groups[hhash] = FITSDataGroup(item,hhash,self.keywords,self.formats)
        else:
            self._groups[hhash].append(item)
        return hhash
        
    def type_to_hash(self,item):
        """docstring for type_to_hash"""
        if isinstance(item,basestring) and check_exists(item) and item.endswith(".fits"):
            item = silent_getheader(item)
        if isinstance(item,pf.header.Header) or isinstance(item,collections.Mapping):
            hhash = self.make_hash(item)
        elif isinstance(item,basestring):
            hhash = unicode(item)
        else:
            raise TypeError("Can't convert {} to Header Hash".format(type(item)))
        return hhash
        
    def make_hash(self,dictionary):
        """Make the appropraite keyword hash for a given dictionary"""
        return unicode("".join([ unicode(key)+u"="+unicode(dictionary[key]) for key in self.keywords ]))
        
    def discard(self,item):
        """docstring for discard"""
        hhash = self.type_to_hash(item)
        del self._groups[hhash]
        
    def table(self):
        """Return a text table for this datagroup"""
        col = "{:<20}"
        row = "{:<30.30s}" + (col * (len(self.keywords)))
        head = row.format("Name",*[keyword for keyword in self.keywords]) + "  N"
        txt_row = "{{:<{}s}}".format(len(head)-6) + "{:>3d}"
        row = row + "{:>3d}"
        hashes = self.hashes
        hashes.sort()
        output = [head,"-"*(len(head))]
        for keyhash in hashes:
            if self.islist(keyhash):
                output += [txt_row.format(keyhash,len(self.get(keyhash).files))]
            else:
                rowtuple = [self.get(keyhash).name]
                for keyword in self.keywords:
                    rowtuple.append(self.get(keyhash).keylist[keyword])
                rowtuple.append(len(self.get(keyhash).files))
                output += [row.format(*rowtuple)]
        return output

class FITSDataGroup(collections.MutableSequence):
    """docstring for FITSDataGroup"""
    def __init__(self,header,keyhash,keywords,formats):
        """docstring for __init__"""
        super(FITSDataGroup, self).__init__()
        self._keyhash = keyhash
        self._keywords = keywords
        self._formats = formats
        self._headers = [header]
        
    def __contains__(self,value):
        return value in self._headers
    
    def __iter__(self):
        return iter(self._headers)
        
    def append(self,header):
        self._headers += [header]
        
    def __setitem__(self,key,value):
        return self._headers.__setitem__(key,value)
        
    def __getitem__(self,key):
        return self._headers.__getitem__(key)
        
    def __delitem__(self,key):
        return self._headers.__delitem__(key)
        
    def __len__(self):
        return len(self._headers)
        
    def insert(self,index,value):
        return self._headers.insert(index,value)
    
    @property
    def keywords(self):
        """docstring for keyword"""
        return self._keywords
    
    @property
    def keylist(self):
        """Get the uniform keylist for this object."""
        return { key:self._headers[0][key] for key in self.keywords }
        
    @property
    def keyhash(self):
        return self._keyhash
        
    @property
    def name(self):
        """Return the formatted name"""
        return "-".join([ format.format(self.keylist[keyword]) for format,keyword in zip(self._formats,self.keywords) ]).replace(" ","-")
        
    @property
    def files(self):
        """docstring for files"""
        return [ header["FILENAME"] for header in self._headers ]
        
class ListFITSDataGroup(FITSDataGroup):
    """A group of FITS files defined by an input list.ListFITSDataGroup"""
    def __init__(self,listfile,headers,keywords,formats):
        super(ListFITSDataGroup, self).__init__(header=headers[0],keyhash=listfile,keywords=keywords,formats=formats)
        self._headers = headers
        self._list = listfile
        
    @property
    def name(self):
        """FormattedName"""
        return os.path.basename(os.path.splitext(self._list)[0])
        
    @property
    def filename(self):
        """Return the full filename"""
        return self._list
        
    @property
    def keyhash(self):
        """Return the proper keyhash"""
        return os.path.basename(self.filename)
        
        
    

class FITSGroup(SCEngine):
    """Create a list of groups from FITS header attributes."""
    
    command = 'group'
    
    help = "Make a list of groups for a collection of FITS files."
    
    description = fill("Creates a text table with the requested header information for a bunch of FITS files.")
        
    def configure(self):
        """Configure the logging"""
        super(FITSGroup, self).configure()
        self.parser.add_argument('-i','--input',help="Either a glob or a list contianing the files to group.",action='store',nargs="?",type=unicode,default=unicode(self.config.get("Defaults.Log.Glob","*.fits")))
        self.parser.add_argument('keywords',nargs="*",help="Keywords to group.",action='store',default=self.config.get("Log.Keywords"))
        
    def do(self):
        """Make the log table"""
        if os.path.exists(self.opts.input):
            with open(self.opts.input,'r') as inlist:
                self.files = inlist.readlines()
        else:
            self.files = glob.glob(self.opts.input)
        
        print("Will group %d files." % len(self.files))
        self.data = FITSHeaderTable()
        self.data.read(self.files)
        self.data.normalize(self.opts.keywords)
        self.data.group(self.opts.keywords)
        output = self.data.groups.table()
        print("\n".join(output))
        print("%d files grouped." % len(self.data.collection))

class FITSLog(SCEngine):
    """Create a log from FITS header attributes."""
    command = 'log'
        
    help = "Make a log file for a collection of FITS files."
    
    description = fill("Creates a text table with the requested header information for a bunch of FITS files.")
        
    def configure(self):
        """Configure the logging"""
        super(FITSLog, self).configure()
        self.parser.add_argument('-o','--output',help="Output file name",default=self.config.get("Defaults.Log.OutputName",False),action='store',dest='log')
        self.parser.add_argument('-i','--input',help="Either a glob or a list contianing the files to log.",action='store',nargs="?",type=unicode,default=unicode(self.config.get("Defaults.Log.Glob","*.fits")))
        self.parser.add_argument('keywords',nargs="*",help="Keywords to log.",action='store',default=self.config.get("Log.Keywords"))
        
    def do(self):
        """Make the log table"""
        if not self.opts.log:
            cdir = os.path.split(os.getcwd())[-1]
            self.opts.log = "%s.log" % (cdir)
        elif os.path.exists(self.opts.log):
            print("Log %r already exists. Will overwirte." % self.opts.log)
        
        if os.path.exists(self.opts.input):
            with open(self.opts.input,'r') as inlist:
                self.files = inlist.readlines()
        else:
            self.files = glob.glob(self.opts.input)
        
        print("Will log %d files." % len(self.files))
        self.data = FITSHeaderTable()
        self.data.read(self.files)
        self.data.collect(*self.opts.keywords)
        output = self.data.logstring(order=self.opts.keywords)
        if self.opts.log:
            with open(self.opts.log,'w') as outputfile:
                outputfile.write("\n".join(output))
        else:
            print("\n".join(output))
            print("%d files found." % len(self.data.collection))
        
        
    
    
class MakeList(SCEngine):
    """Make a list of files with certain header attributes"""
    def __init__(self, command = 'list'):
        super(MakeList, self).__init__(command = command)
        
    help = "Make a list of FITS files that match criteria."
    
    description = "Make a list of FITS files that match given criteria using direct matching, substring matching, or regular expressions."
    
    def configure(self):
        super(MakeList, self).configure()
        self.parser.add_argument('-i','--input',action='store',
            default=self.config.get("Defaults.Log.Glob","*.fits"),help="Input file glob",metavar="*.fits")
        self.parser.add_argument('-o','--output',action='store',
            default=self.config.get("Defaults.List.Name",False),help="Output file list name",metavar="files.list")
        self.parser.add_argument('--re',action='store_true',
            help="Use regular expressions to parse header values.")
        self.parser.add_argument('-l','--log',action='store_true',
            help="Store a full log file, not just a list of files that match this keyword")
        self.parser.add_argument('keywords',nargs="*",action='store',
            help='header search keywords',metavar='KWD=value')
        
            
    def do(self):
        """Run the search itself"""
        self._search = {}
        self._order = []
        for pair in self.opts.keywords:
            if len(pair.split("=",1)) == 2:
                key,value = pair.split("=",1)
                if self.opts.re:
                    value = re.compile(value)
                else:
                    try:
                        value = ast.literal_eval(value)
                    except:
                        value = value
            elif len(pair.split("=")) == 1:
                key,value = pair,True
            else:
                self.parser.error("Argument for Malformed Keyword Pair: '%s'" % pair)
            self._search[key] = value
            self._order.append(key)
        if os.path.exists(self.opts.input):
            with open(self.opts.input,'r') as inlist:
                self.files = [line.rstrip("\n\r") for line in inlist]
            if not os.path.exists(self.files[0]):
                self.parser.error("Malformed input list '%s' \n File does not exist '%s'" % (self.opts.input,firstline))
        else:
            infiles = self.opts.input.split()
            self.files = []
            for infile in infiles:
                self.files = glob.glob(infile)
        if len(self.files) == 0:
            self.parser.error("No files specified to search")
        print("Searching %d files." % len(self.files))
        self.data = FITSHeaderTable()
        self.data.read(self.files)
        self.data.search(**self._search)
        output = self.data.logstring(order=self._order)
        print "\n".join(output)
        print "%d files found." % len(self.data.collection)
        
        if self.opts.output:
            if not self.opts.log:
                output = self.data.liststring()
            with open(self.opts.output,'w') as fnamelist:
                fnamelist.write("\n".join(output))
            print "Wrote file %s to '%s'" % ("log" if self.opts.log else "list",self.opts.output)
        
