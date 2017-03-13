
Getting Started
===============

Compatibility
-------------

This software suite works out-of-the-box on Linux and Windows 64-bit machines. 

Source Code
-----------

The source code is publicly available under BSD License: ::

  git clone https://github.com/danielnyga/pracmln.git


Prerequisites
-------------


Linux
^^^^^

* Python 2.7 with Tkinter installed.

    .. note::

      On Linux, the following packages should be installed (tested for Ubuntu).::

        sudo apt-get install python-tk python-scipy

  You will also need the following python packages: `pyparsing`, `tabulate`, `psutil` and `networkx`. You can install them via ::

    $ sudo pip install pyparsing tabulate psutil==0.4.1 networkx

* `pracmln` is shipped with the open source WCSP solver `toulbar2` for Linux and Windows 64-bit versions.
  For other architectures, it can be obtained from::

    https://mulcyber.toulouse.inra.fr/projects/toulbar2

  Its executable ``toulbar2`` should then be included in the ``$PATH`` variable.


Windows
^^^^^^^

* Python 2.7 with Tkinter installed.

    .. note::

      On Windows, Tkinter is usually shipped with Python.

  You will also need the following python packages: `pyparsing`, `tabulate`, `psutil` and `networkx`. You can install them via ::

    $ pip install numpy pyparsing tabulate psutil==0.4.1 networkx

  You will also need the python package `scipy`. If installing it with pip does not work, obtain a prebuilt version (e.g. scipy‑0.XX.Y‑cp27‑cp27m‑win32.whl) online from::

    http://www.lfd.uci.edu/~gohlke/pythonlibs/#scipy


* `pracmln` is shipped with the open source WCSP solver `toulbar2` for Linux and Windows (Intel) 64-bit versions.
  For other architectures, it can be obtained from::

    https://mulcyber.toulouse.inra.fr/projects/toulbar2

  Its executable ``toulbar2`` should then be included in the ``$PATH`` variable.


Installation
------------

#. Generating Apps

   Run the ``setup.py`` script: ::
    
    python setup.py

   This will generate a number of shell scripts (or batch files for Windows) in the ``./apps`` directory. 

#. Setting up your Environment

   ``setup.py`` will report how to set up your environment.
   
   To temporarily configure your environment, you can simply use the ``env`` script/batch
   file it creates to get everything set up.
   If you use `pracmln` a lot, consider adding the ``./apps`` directory to your ``PATH`` variable
   or copy the files created therein to an appropriate directory.
   If you intend to make use of scripting, also set ``PYTHONPATH`` as described
   by ``setup`` (the env.bat for Windows will do this automatically).

.. _sec-cppbindings:

C++ bindings
------------

* Requirements:

 * Linux OS (tested on Ubuntu 14.04)

 * libboost-python

 * libpython-dev

* Installation:

 * Run the ``setup`` script with ``--cppbindings``: ::

    python setup.py --cppbindings

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
--------

There are example models in the ``./examples/`` directory.

Simply run the ``mlnquery`` applications in one of the subdirectories
to try out some inference tasks.

In the ``./examples/meals/`` directory, you can also try out learning.
To train a MLN model run ``mlnlearn``. 
