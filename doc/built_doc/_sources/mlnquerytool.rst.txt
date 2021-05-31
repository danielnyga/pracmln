
MLN Query-Tool
==============

Start the tool from the command line with ``mlnquery``.

.. figure:: _static/img/mlnquerytool.png

   The MLN Query-Tool GUI.


The MLN query tool is an interface to make inferences in a Markov 
logic network. The tool allows you to invoke the actual MLN 
inference algorithms of the MLN engine. Once you start the 
actual algorithm, the tool window itself will be hidden as long as 
the job is running, while the output of the algorithm is written to 
the console for you to follow. At the beginning, the tools list the 
main input parameters for your convenience, and, at the end, the 
query tool additionally outputs the inference results to the 
console.

The tool features integrated editors for ``.db`` and ``.mln`` files. If you 
modify a file in the internal editor, it will automatically be 
saved as soon as you invoke the learning or inference method. The 
new content can either be saved to the same file (overwriting the 
old content) or a new file, which you can choose to name as 
desired. Furthermore, the tool will save all the settings you made 
whenever the inference method is invoked, so that you can easily 
resume a session. When performing inference, one typically 
associates a particular query with each evidence database, so the 
query tool specifically remembers the query you made for each 
evidence database and restores it whenever you change back to the 
evidence database.

Given these inputs one can choose one of the :doc:`inferencemethods`
and infer the values of the variables stated a 
comma-separated list of queries, where a query can be any one of 
the following:

* a ground atom, e.g. ``foobar(X,Y)``
* the name of a predicate, e.g. ``foobar``
* a ground formula, e.g. ``foobar(X,Y) ^ foobar(Y,X)`` (internal engine only) 

The additional parameters include:

* **Closed-world assumption**

  There are two parameters one can specify to control predicates whose variable values are to be set to false if the evidence given does not state something different:
  
  * **CW Preds**: A comma-separated list of predicate names, whose atom values are automatically set to false if evidence does not state something different.
  
  .. note::
  
    Fore functionally determined perdicates, this settings will raise an exception, because there must always be exactly one true ground atom.

  
  * **CW assumption**: Will apply the closed-world assumption to all predicates that do not appear in the list of queries.
  
  .. note::
  
    This setting will have no effect on functional predicates and will  print a warning for soft-functional predicates.

  
* the option to show additional debug outputs during the execution when using the internal system (additional parameter: ``debug='INFO'``). This field can also be used to pass additional, method-specific parameters to the algorithm, which are documented in :doc:`inferencemethods`.

  
*  ``debug='<level>'`` This will temporarily set the debug level to the one specified. Admissible values are (with decreasing level of verbosity): ``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``, ``CRITICAL``.
