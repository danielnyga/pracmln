
MLN-Learning-Tool
=================

Start the tool from the command line with ``mlnlearn``.

.. figure:: _static/img/mlnlearningtool.png

   The MLN-Learning-Tool GUI.

The MLN learning tool learns the weights of a MLN file given a 
training database and a template MLN. The tool allows you to invoke 
the actual MLN learning algorithms of the Python-based MLN 
engine. Once you start the actual algorithm, 
the tool window itself will be hidden as long as the job is 
running, while the output of the algorithm is written to the 
console for you to follow. At the beginning, the tools list the 
main input parameters for your convenience, and, at the end, the 
query tool additionally outputs the inference results to the 
console.

The tool features an integrated editor for ``*.db`` and ``*.mln`` files. If 
you modify a file in the internal editor, it will automatically be 
saved as soon as you invoke the learning method. The new content 
can either be saved to the same file (overwriting the old content) 
or a new file, which you can choose to name as desired. 
Furthermore, the tool will save all the settings you made whenever 
the learning method is invoked, so that you can easily resume a 
session.

Parameters
^^^^^^^^^^

For the learning methods, there are a couple of parameters that can 
be handed over to the respective algorithm:

.. figure:: _static/img/learning-parameters.png

   Parameters in the GUI Tool.
   
*  Evidence and query predicates for the discriminative learning algorithms
   (see also: :doc:`learningmethods`)
   
*  A Gaussian prior distribution over the formula weights.
   (see also: :doc:`learningmethods`)

In the text field 'Add. Params', you have the opportunity to pass additional
parameters to the tool and the learning algorithms, respectively.
The parameters need to be specified in the Python dictionary syntax
as they will be transformed into and passed to the algorithms as
python dictionaries.

Currently, the following parameters are supported:

*  ``debug='<level>'`` This will temporarily set the debug level to the 
   one specified. Admissible values are (with decreasing level of verbosity): 
   ``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``, ``CRITICAL``.
   
*  ``optimizer='<name>'`` Specifies which optimization routine to be used. See also
   :doc:`learningmethods` for more information.
   
* ``profile=True/False`` Launches the learner via the python profiler.

