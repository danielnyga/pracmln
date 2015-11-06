API-Specification
=================

`pracmln` comes with an easy-to-use API, which lets you use the
learning and reasoning methods provided by `pracmln` convently
in your own applications.


MLNs
^^^^

An MLN is represented by an instance of the class :class:`pracmln.MLN`.
An existing MLN can be loaded using its static :attr:`load` method: ::

    mln = MLN.load(files='path/to/file')

.. automethod:: pracmln.MLN.load

Alternatively, the constructor can be used to load the MLN:::

    mln = MLN(mlnfile='path/to/mlnfile', grammar='PRACGrammar', logic='FirstOrderLogic')
    
.. autoclass:: pracmln.MLN

If no ``mlnfile`` is specified, the constructor creates an empty ``MLN``
object. Using the ``<<`` operator, one can feed content into the MLN: ::

    >>> from pracmln import MLN
    >>> mln = MLN()
    >>> mln << 'foo(x)' # predicate declaration
    >>> mln << 'bar(y)' # another pred declaration
    >>> mln << 'bar(?x) => bar(?y).' # hard logical constraint
    >>> mln << 'logx(.75)/log(.25) foo(?x)' # weighted formula
   
We can dump the MLN into the regular MLN file format by using the :attr:`write`
method: ::

    >>> mln.write()



    // predicate declarations
    bar(y)
    foo(x)

    // formulas
    bar(?x) => bar(?y).
    logx(.75)/log(.25)  foo(?x)

If your terminal supports ASCII escape sequences, the syntax of the result
will be highlighted. By specifying a ``stream``, one can dump the MLN into a file.

.. automethod:: pracmln.MLN.write

We can access the predicates of the MLN using the :attr:`predicates` attribute: ::
   
    >>> for pred in mln.predicates:
    ...     print repr(pred)
    ... 
    <Predicate: bar(y)>
    <Predicate: foo(x)>

Formulas are instances of :class:`pracmln.logic.Formula` and stored in the :attr:`formulas` attribute: ::

    >>> for f in mln.formulas:
    ...     print f
    ...     f.print_structure()
    ... 
    bar(?x) => bar(?y)
    <Implication: bar(?x) => bar(?y)>: [idx=0, weight=inf] bar(?x) => bar(?y) = ?
        <Lit: bar(?x)>: [idx=?, weight=?] bar(?x) = ?
        <Lit: bar(?y)>: [idx=?, weight=?] bar(?y) = ?
    foo(?x)
    <Lit: foo(?x)>: [idx=1, weight=logx(.75)/log(.25)] foo(?x) = ?


The method :attr:`print_structure` prints the logical structure of a 
formula as well as a couple of properties, such as its index in the 
MLN and its weight. As you can see, hard formula constraints are 
internally represented by assiging them a weight of 
``float('inf')``. In presence of evidence, :attr:`print_structure` also 
prints the truth value of each constituent of a formula, which is a 
``float`` value in {0,1} for formulas with FOL semantics, and in [0,1] in 
case of fuzzy logics semantics. If the truth value cannot be 
determined (as in our example here for we don't have evidence yet), 
this is indicated by a question mark ``= ?``.


Databases
^^^^^^^^^

The central datastructures for representing relational data is
the :class:`pracmln.Database` class. It stores atomic facts about
the relational domain of discourse by maintaining a mapping of ground
atoms to their respective truth value.

A serialized ``.db`` database file can be loaded using the :attr:`Database.load`
method: ::

    >>> from pracmln import Database
    >>> dbs = Database.load(mln, 'path/to/dbfile')
    
Since there may be multiple independent databases stored in a single 
`.db` file (separated by ``---``) :attr:`load` always returns a list
of :class:`pracmln.Database` objects.


The ``mln`` parameter of the :attr:`load` method must point to an 
instantated :class:`pracmln.MLN` object containing all the predicate
declarations of atoms occuring in the database. The default
constructor creates an empty database: ::

    >>> db = Database(mln)
    
.. autoclass:: pracmln.Database


Loading a database from a static serialized file is fine, but if you 
consider integrating SRL techniques seamlessly in your application, 
you rather want to create databases representing the evidences for 
your reasoning tasks at runtime. `pracmln` has been designed to 
support convenient dynamic generation of relational data. Once a 
database has been loaded or created, new facts can be added using 
the ``<<`` operator ::

    >>> db << 'foo(X)'

or by directly setting the truth value of an atom: ::

    >>> db['bar(Y)'] = .0
    
Similarly to the :class:`pracmln.MLN`, databases have a :attr:`write`
method that prints them to the console: ::

    >>> db.write()
    [                              ]   0.000 %  bar(Y)
    [■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■] 100.000 %  foo(X)
    
The bars in front of the atom names indicate the truth 
values/probabilities of the respective atom. When writing them to a 
file, they can be switched off.

.. automethod:: pracmln.Database.write

Truth values of atoms that have been asserted once can be retracted
from a database using the ``del`` operator: ::

    >>> del db['bar(Y)']
    >>> db.write()
    [■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■] 100.000 %  foo(X)

A convenient method is :attr:`Database.query`, which lets you make
a PROLOG-like query to the database for an arbitrary formula in FOL.

.. automethod:: pracmln.Database.query

Reasoning
^^^^^^^^^

Once an MLN and a database have been loaded or created, we can perform
inference using the :class:`pracmln.MLNQuery` class, which wraps
around all inference algorithms provided by `pracmln`. It takes
the MLN object subject to reasoning as a parameter as well as any
of the parameters for the inference algorithms described in :doc:`inferencemethods`. ::

    >>> from pracmln import MLNQuery
    >>> result = MLNQuery(mln=mln, db=db).run()
    >>> result.write()
    [■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■] 100.000 % bar(X)
    [■■■■■■■■■■■■■■■■■■■■■■■       ]  75.660 % foo(K)
    

API Reference
^^^^^^^^^^^^^

:class:`pracmln.MLN`
~~~~~~~~~~~~~~~~~~~~

.. automodule:: pracmln
    :members: MLN


:class:`pracmln.Database`
~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: pracmln
    :members: Database



In this section, we will introduce the basic interface for using
the reasoning methods for MLNs provided by `pracmln`.

The easiest way


ROS Service interface
~~~~~~~~~~~~~~~~~~~~~

Introduction
------------
This is a tutorial for the ROS service that can be used
to query an MLN. We will describe the implemantation
of the server together with the ROS messages that are
associated with this project. We will also present an
example client program that can be used as a template.


Server methods
--------------

.. function:: handle_mln_query(req)
   :module: scripts.mln_server

	Handles the query from the client. It expects
	*req* to have two fields, *req.query* and an optional
	*req.config*. *req.query* should be of type *MLNQuery* while
	*req.config* should be of type *MLNConfig*.
	
	It returns a list of *AtomProbPair* objects. Each element of the 
	list is an atom with it's corresponding degree of truth.

.. function:: mln_interface_server
   :module: scripts.mln_server

   Keeps an infinite loop while waiting
   for clients to ask for the service.

.. function:: getInstance
   :module: scripts.mln_server.Storage

   Storage is a singleton class that keeps
   track of an MLNInfer object together with
   the settings for the inference proceedure.

Example client 
--------------

.. function:: mln_interface_client(query, config=None)
   :module: scripts.mln_mln

    This is an example of the client quering the service.
    The important thing to note is that you have the option
    to set the configuration parameters only once and use the
    the same settings in further calls.

Messages
--------
**MLNQuery.msg**
	This ROS message contains the following fields:
	
	**queries** - This message is an ecoding of the queries that will
		sent to the service. 


**MLNResponse.msg**
	This ROS message contains the follwing fields:

	**results** - This is what is returned by the service. results
		is a list of *AtomProbPair* objects. Each atom is associated
		with a probability value.


**MLNConfig.msg**
	This is a message that is used to initialize the
	configuration parameters for quering the service.
	You have an option to pass this argument only once
	and reuse the same configurations over and over.
	It contains the following fields:

	**mlnFiles** - a \*.mln file that describes the MLN

	**db** - the evidence database

	**method** - the inference method to be used

	**engine** - the inference engine to be used

	**output_filename** - the name of the output filename

	**saveResults** - this field should be set to true if you wish to save the results

	**logic** - specifies the logic to be used for inference

	**grammar** - specifies the grammar to be used

**AtomProbPair.msg**
	This message is a pair of an Atom and a Probabality.
	It contains the following fields:

	**atom** - string describing the atom

	**prob** - a probability value for the atom's degree of truth


Services
--------

**MLNInterface.srv**
	This is the main service. It contains two fields:

	**MLNQuery** - This is the query string

	**MLNConfig** - This specifies which engine, inference method
		etc is going to be used for inference. This should be
		set at least once.
 


