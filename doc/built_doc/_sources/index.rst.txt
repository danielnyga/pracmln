.. mln_interface documentation master file, created by
   sphinx-quickstart on Tue Feb 25 11:53:18 2014.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

About
=====

pracmln is a toolbox for statistical relational learning and 
reasoning and as such also includes tools for standard graphical 
models. pracmln is a statistical relational learning and reasoning 
system that supports efficient learning and inference in relational 
domains. pracmln has started as a fork of the *ProbCog* toolbox and 
has been extended by latest developments in learning and reasoning 
by the Institute for Artificial Intelligence at the University of 
Bremen, Germany.


pracmln was designed with the particular needs of technical systems 
in mind. Our methods are geared towards practical applicability and 
can easily be integrated into other applications. The tools for 
relational data collection and transformation facilitate 
data-driven knowledge engineering, and the availability of 
graphical tools makes both learning or inference sessions a 
user-friendly experience. Scripting support enables automation, and 
for easy integration into robotics applications, we provide a 
client-server library implemented using the widely used `ROS (Robot 
Operating System) <http://www.ros.org/>`_ middleware.

* Markov logic networks (MLNs): learning and inference Fuzzy-MLN 
  reasoning, probabilistic reasoning about concept taxonomies.
  
* Logic: representation, propositionalization, 
  stochastic SAT sampling, weighted SAT solving, etc.


This package consists of an implementation of Markov logic networks 
as a Python module (`pracmln`) that you can use to work with MLNs in 
your own Python scripts. For an introduction into using `pracmln` in
your own scripts, see :doc:`apidoc`.



Release notes
^^^^^^^^^^^^^
  * Release 1.2.4 (17.05.2019)

    * Fixed installation issues with ``pip``
    * Minor fixes.

  * Release 1.2.2 (18.12.2017)

    * Support for Python 2 and Python 3
    * Release a ``pip``-compliant package
    * Minor fixes

  * Release 1.1.2 (14.03.2017)

    * *Fix*: Patches for using toulbar2 on Windows platforms

  * Release 1.1.1 (13.03.2017)

    * *Fix*: Patches for Windows support

  * Release 1.1.0 (13.06.2016)

    * *Fix*: :ref:`sec-cppbindings`
    * *Feature*: literal groups for formula expansion (see :ref:`sec-litgroups`)
    * *Fix*: existentially quantified formulas evaluate to false when they cannot be grounded
    * *Fix*: cleanup of process pools in multicore mode

Citing
^^^^^^

When you publish research work that makes use of `pracmln`, we
gratefully appreciate if a reference to `pracmln` can be found
in your work in the following way:

* Nyga, D., Picklum, M., Beetz, M., et al., *pracmln -- Markov logic networks in Python*,
  `<http://www.pracmln.org>`_, Online; accessed |today|.

The following Bibtex entry can be used for documents based on LaTeX: ::

    @Misc{,
        author =    {Daniel Nyga and Mareike Picklum and Michael Beetz and others},
        title =     {{pracmln} -- Markov logic networks in {Python}},
        year =      {2013--},
        url = "http://www.pracmln.org/",
        note = {[Online; accessed <date>]}
    }


Contents
^^^^^^^^

.. toctree::
   :maxdepth: 2

   features
   installation
   tools
   mlnquerytool
   mlnlearningtool
   learningmethods
   inferencemethods
   mln_syntax
   mlntutorial
   evaluation
   apidoc
   tutorial
   

Credits
^^^^^^^

Lead Developer
~~~~~~~~~~~~~~

Daniel Nyga (`nyga@cs.uni-bremen.de <mailto:nyga@cs.uni-bremen.de>`_)

Contributors
~~~~~~~~~~~~

* Mareike Picklum
* Ferenc Balint-Benczedi
* Thiemo Wiedemeyer
* Valentine Chiwome

Former Contributors (from ProbCog)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Dominik Jain
* Stefan Waldherr
* Klaus von Gleissenthall
* Andreas Barthels
* Ralf Wernicke
* Gregor Wylezich
* Martin Schuster
* Philipp Meyer

Acknowledgments
~~~~~~~~~~~~~~~

This work is supported in part by the EU FP7 projects `RoboHow <http://www.robohow.org>`_ (grant number 288533) and `ACAT <http://www.acat-project.eu>`_ (grant number
600578):

.. image:: _static/img/robohow-logo.png
    :height: 70px
    :target: http://www.robohow.eu
.. image:: _static/img/acat-logo.png
    :height: 70px
    :target: http://www.acat-project.eu
.. image:: _static/img/fp7-logo.png
    :height: 70px
    :target: http://ec.europa.eu/research/fp7/index_en.cfm


Publications
^^^^^^^^^^^^

.. bibliography:: refs.bib
    :list: enumerated
    :enumtype: arabic
    :filter: author % "Nyga" or author % "Jain"
    :all:


Indices and tables
^^^^^^^^^^^^^^^^^^

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

