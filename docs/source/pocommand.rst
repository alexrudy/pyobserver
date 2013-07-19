The ``PO`` command
==================

The ``PO`` command is used to manipulate many FITS files from the command line. It contains several subcommand programs which work with FITS files or starlists.


FITS File Commands
------------------

Several ``PO`` commands deal with large groups of FITS files. These are all documented below. The commands use a similar option-syntax to control `input options`_, `output options`_ and `keyword search`_, which are documented after the individual commands.

.. program:: PO list

``PO list``
~~~~~~~~~~~

Output the filenames of FITS files. On its own, this is not particularly powerful, but with the `keyword search`_ capability, it can be used to quickly filter a list of FITS files.

.. program:: PO log

``PO log``
~~~~~~~~~~

Output the filenames and header values for FITS files. Header values can be specified with or without search values. The delimiter between keywords and search values is the `=` character. See `keyword search`_ for more information on keyword searching. This command supports the :option:`PO -i`, :option:`PO -o` and :option:`<KEYWORD=value>` options.

.. program:: PO inspect

``PO inspect``
~~~~~~~~~~~~~~

This method works like ``PO list``, except that individual FITS files are opened one at a time in DS9, and the user is asked to confirm whether the shown file should be included in the output list or not.

``PO group``
~~~~~~~~~~~~

Groups the FITS files based on Keyword values being homogenous. Groups are then listed for the user to examine.

.. program:: PO

.. _input options:

FITS Command Input
~~~~~~~~~~~~~~~~~~

.. option:: -i <filename> [<filename> ...]

    This option takes any number of filenames which are then loaded into the command for processing. Shell globs can be used to pass many filenames. As well, when files are lists, the contents of those lists are loaded as fits files.


.. _output options:

FITS Command Output
~~~~~~~~~~~~~~~~~~~

.. option:: -o <filename>

    The filename used for output.

.. option:: -l

    This flag toggles whether the output is a log file, or just a bunch of filenames. When :option:`PO -l` is used, it creates a log file, which is human-readable, has several columns (specified in the `keyword search`_). List files are suitable for use with IRAF or other tools that expect a list of FITS files.


.. _keyword search:

FITS Keyword Search
~~~~~~~~~~~~~~~~~~~

Most ``PO`` commands can search through your FITS files using header keywords. When supplying the keywords to the ``PO`` command, you can use a ``KEYWORD=value`` syntax. The `value` will be interpreted as a python literal, or as a string (so you don't need to put quotes around strings that don't have spaces). This means that entering ``OBJECT=galaxy`` will search for files with the header keyword ``OBJECT`` set to the value ``"galaxy"``. This works for other python literals (``int``, ``float`` etc.) which might appear in header keywords.

The ``--re`` option for all search commands changes the value to a regular expression. Therefore ``--re OBJECT=gal(axy)?`` will find header keywords which match either ``gal`` or ``galaxy`` or contain either of those strings. (This is a dumb example. There are lots of good tutorials on regular expressions online. The `python re documentation`_ is a decent place to start.).

.. option:: --re

    Tells the tool to use regular expressions when searching through FITS headers.

.. option:: <KEYWORD=value>

    Tells the program to search for keywords. All searches are performed with the "AND" operator. Keyword arguments should be of the form KEYWORD="search value" where "search value" can be one of the following types:

    - A string or other basic python literal. In this case, the keyword value is matched against the entire literal.
    - A regular expression object from :func:`re.compile`, where :meth:`match` is used to match the compiled regular expression to the keyword value.
    - A boolean value. ``True`` means that you only want headers which have the specified keyword. ``False`` means you only want headers which **don't** have the specified keyword. For ``False``, the keyword value will be normalized to the empty stirng (for logging/listing purposes).

.. _python re documentation: <http://docs.python.org/2/library/re.html>

Starlist Commands
-----------------

.. program:: PO slds9

``PO slds9``
~~~~~~~~~~~~

Conversion between starlists and ds9.

