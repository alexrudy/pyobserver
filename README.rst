Introduction to PyObserver
==========================

Observational tools for handling FITS files.

Primarily, this tool provides a command ``PO`` which can be used to examine FITS file headers and manipulate starlists.

Installation
------------

To install this module, use the python installation command ``pip``::

    $ pip install .


Installing the module with ``pip install -e .`` installs it so that you can make changes to the source files and have those changes automatically take effect. ``pip`` will ensure that your computer has all of the required dependencies.

Usage
-----

To get help information, use ``PO -h``. ``PO`` has several commands for working with FITS files, and one command for working with Starlists/ds9 regions.

FITS Commands
~~~~~~~~~~~~~

- ``PO list``: Create a list of files. Optionally, search through their headers, and only list ones matching specific criteria.
- ``PO log``: Create a log of files with specific header keywords included. Optionally, search.
- ``PO group``: Group a collection of files based on keyword values. This quickly tells you how many files have identical values for a set of keywords.
- ``PO info``: Show the HDU information for a bunch of FITS files. This shows extension HDUs, HDU types and sizes.
- ``PO inspect``: Similar to ``PO list``, but pulls each image up in ds9, and asks the user whether they want to keep that image or not.

Searching FITS Files
~~~~~~~~~~~~~~~~~~~~

Most ``PO`` commands can search through your FITS files using header keywords. When supplying the keywords to the ``PO`` command, you can use a ``KEYWORD=value`` syntax. The `value` will be interpreted as a python literal, or as a string (so you don't need to put quotes around strings that don't have spaces). This means that entering ``OBJECT=galaxy`` will search for files with the header keyword ``OBJECT`` set to the value ``"galaxy"``. This works for other python literals (``int``, ``float`` etc.) which might appear in header keywords.

The ``--re`` option for all search commands changes the value to a regular expression. Therefore ``--re OBJECT=gal(axy)?`` will find header keywords which match either ``gal`` or ``galaxy`` or contain either of those strings. (This is a dumb example. There are lots of good tutorials on regular expressions online. The `python re documentation`_ is a decent place to start.).


Starlist Commands
~~~~~~~~~~~~~~~~~

- ``PO slds9``: Convert between starlists and ds9 region files.

.. _python re documentation: <http://docs.python.org/2/library/re.html>
