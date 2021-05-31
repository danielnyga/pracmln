
Getting Started
===============

Compatibility
^^^^^^^^^^^^^

This software suite works out-of-the-box on Linux and Windows 64-bit machines. 

Source Code
^^^^^^^^^^^

The source code is publicly available under BSD License: ::

  git clone https://github.com/danielnyga/pracmln.git


Prerequisites
^^^^^^^^^^^^^

Linux
~~~~~

* Python 2.7/3 (tested with 3.5) with Tkinter installed.

    .. note::

      On Linux, the following packages should be installed (tested for Ubuntu).::

        sudo apt-get install python-tk

* `pracmln` is shipped with the open source WCSP solver `toulbar2` for Linux and Windows 64-bit versions.
  For other architectures, it can be obtained from::

    https://mulcyber.toulouse.inra.fr/projects/toulbar2

  Its executable ``toulbar2`` should then be included in the ``$PATH`` variable.


Windows
~~~~~~~

* Python 2.7 with Tkinter installed.

    .. note::

      On Windows, Tkinter is usually shipped with Python.

  You will also need the following python packages: `pyparsing`, `tabulate`, `psutil` and `networkx`. You can install them via ::

    $ pip install pyparsing tabulate psutil==0.4.1 networkx

  You will also need the python packages `scipy` and `numpy+mkl`. Installing with pip will probably not work, but you can obtain prebuilt versions (e.g. scipy‑0.XX.Y‑cp27‑cp27m‑win32.whl and numpy‑1.11.3+mkl‑cp27‑cp27m‑win32.wh) online from::

    http://www.lfd.uci.edu/~gohlke/pythonlibs/#scipy

  and::

    http://www.lfd.uci.edu/~gohlke/pythonlibs/#numpy

  You can install the files with pip::

    $ pip install <filename>.whl

* `pracmln` is shipped with the open source WCSP solver `toulbar2` for Linux and Windows (Intel) 64-bit versions.

   Install the ``toulbar2.exe`` in ``./3rdparty/toulbar2-0.9.7.0/x86_64/Windows`` and make sure the path to the installed executable (most likely ``C:\Program Files (x86)\toulbar2.0.9.7.0-Release``)
   is added to your ``PATH`` variable. For other architectures, `toulbar2` can be obtained from::

    https://mulcyber.toulouse.inra.fr/projects/toulbar2


Installation
^^^^^^^^^^^^

As of Version 0.2.0, `pracmln` is shipped as a ``pip``-compliant package. For installing it, just checkout the code from::

  $> git clone https://github.com/danielnyga/pracmln.git

and install it with::

  $> python setup.py install


.. _sec-cppbindings:

C++ bindings
^^^^^^^^^^^^

* Requirements:

 * Linux OS (tested on Ubuntu 14.04, 16.04 with Python 2.7 and Python 3.5)

 * libboost-python

 * libpython-dev

* Installation:

 * After the installation of `pracmln`, run::

    libpracmln-build

   It will compile the C++ sources in the current working directory, creating a folder ``libpracmln``.

* Usage:

 * Include the header ``pracmln/mln.h`` and link against ``libpracmln``

 * A simple example program ::

    #include <pracmln/mln.h>

    int main(int argc, char **argv)
    {
      // create a mln object
      MLN mln;

      // initialize the object (loading python packages, etc.)
      if(!mln.initialize()){
        // error
      }

      std::vector<std::string> query;
      query.push_back("some query");

      // change settings, give input files, etc.
      mln.setQuery(query);
      mln.setMLN("path to mln file");
      mln.setDB("path to db file");

      std::vector<std::string> results;
      std::vector<double> probabilities;

      // execute inference
      if(mln.infer(results, probabilities)){
        // error
      }

      // do something with the results

      return 0;
    }

Examples
^^^^^^^^

There are example models in the ``./examples/`` directory.

Simply run the ``mlnquery`` applications in one of the subdirectories
to try out some inference tasks.

In the ``./examples/meals/`` directory, you can also try out learning.
To train a MLN model run ``mlnlearn``. 
