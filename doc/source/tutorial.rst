.. mln_interface documentation master file, created by
   sphinx-quickstart on Tue Feb 25 11:53:18 2014.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

ROS Service interface
=====================

Introduction
^^^^^^^^^^^^

This is a tutorial for the ROS service that can be used
to query an MLN. We will describe the implemantation
of the server together with the ROS messages that are
associated with this project. We will also present an
example client program that can be used as a template.


Server methods
^^^^^^^^^^^^^^

.. function:: handle_mln_query(req)
   :module: scripts.mln_server
   :noindex:

	Handles the query from the client. It expects
	*req* to have two fields, *req.query* and an optional
	*req.config*. *req.query* should be of type *MLNQuery* while
	*req.config* should be of type *MLNConfig*.
	
	It returns a list of *AtomProbPair* objects. Each element of the 
	list is an atom with it's corresponding degree of truth.

.. function:: mln_interface_server
   :module: scripts.mln_server
   :noindex:

   Keeps an infinite loop while waiting
   for clients to ask for the service.

.. function:: getInstance
   :module: scripts.mln_server.Storage
   :noindex:

   Storage is a singleton class that keeps
   track of an MLNInfer object together with
   the settings for the inference proceedure.

Example client 
^^^^^^^^^^^^^^

.. function:: mln_interface_client(query, config=None)
   :module: scripts.mln_mln
   :noindex:

    This is an example of the client quering the service.
    The important thing to note is that you have the option
    to set the configuration parameters only once and use the
    the same settings in further calls.

Messages
^^^^^^^^

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
^^^^^^^^

**MLNInterface.srv**
	This is the main service. It contains two fields:

	**MLNQuery** - This is the query string

	**MLNConfig** - This specifies which engine, inference method
		etc is going to be used for inference. This should be
		set at least once.
 

