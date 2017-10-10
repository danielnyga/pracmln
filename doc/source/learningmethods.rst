
Learning Methods
================

.. autoclass:: pracmln.MLNLearn
    :members: mln, db, output_filename, params, method, pattern, use_prior, prior_mean,
              prior_stdev, incremental, shuffle, use_initial_weights, qpreds, epreds,
              discr_preds, logic, grammar, multicore, profile, verbose, ignore_unknown_preds,
              ignore_zero_weight_formulas, save

The above parameters are common for all learning algorithms. In 
addition, specific parameters can be handed over to specific 
algorithms, which will be introduced in the following.

General Parameters
^^^^^^^^^^^^^^^^^^

*  Gaussian prior on the formula weights: 
    This parameter enables `MAP-learning` (maximum-a-posteriori) with a Gaussian regularization
    term punishing large weights during learing, which can be controlled
    via the mean and the standard deviation of the Gaussian:
    
    *  ``prior_stdev=<sigma>``: the standard deviation :math:`\sigma` of the prior
    *  ``prior_mean=<mu>``: the mean :math:`\mu` of the prior.
    *  ``use_prior=True/False``: whether or not the prior should be used.
    
    Typical values of a suitable prior are for example :math:`\mathcal{N}(0.0, 10.0)`
    

Generative Learning Methods
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Log-likelihood Learning
~~~~~~~~~~~~~~~~~~~~~~~

The standard learning method using maximum likelihood.

Additional parameters:

* ``optimizer``: the optimization routine to be used.

.. warning::
    
    Log-likelihood learning is intractable for most but the smallest
    examples. If you deal with realistic problems you should consider
    using a more efficient learning method.

Pseudo-likelihood Learning
~~~~~~~~~~~~~~~~~~~~~~~~~~

Learner for the pseudo-log-likelihood learning algorithm.

* ``optimizer``: the optimization routine to be used.

Pseudo-likelihood Learning (with Custom Grounding)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If the formulas in your model are prevalently conjunctions of
literals, this method should be preferred over the previous
methods, since it processes such conjunctions in approximately linear
time instead of exponential time.

* ``optimizer``: the optimization routine to be used.

Composite-likelihood Learning
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Composite-likelihood Learning is a generalization of both log-likelihood
and pseudo-log-likelihood learning, in that it partitions the set
of variables in an MRF in subsets of sizes larger than 1, which leads
to better accuracy of the learnt model. However, in the current 
implementation of `pracmln`, only partitions of size 1 are supported,
in which case this method is equivalent to pseudo-log-likelihood
learning, but comes with a slightly more efficient implementation.

* ``optimizer``: the optimization routine to be used.


Discriminative Learning Methods
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For most of the likelihood-based learning methods, `pracmln` provides
discriminative variants, which are preferable if the reasoning 
problem at hand exhibits dedicated input and output variables. Using
discriminative learning, one can learn conditional distributions
:math:`P(X|Y)` instead of the join :math:`P(X,Y)`, which is favorable
with respect to model accuracy and computational performance. For all
discriminative algorithms, either a set of dedicated query or evidence
predicate needs to be specified, i.e. :math:`X` or :math:`Y` in the 
above distribution, depending on whether the predicates occur as
evidence or query variables. In addition to the parameters of their
generative variants, they have as additional parameters:


* ``qpreds``: a list of predicate names that should be treated
              as query variables during discriminative learning.
* ``epreds``: a list of predicate names that should be treated
              as evidence variables during discriminative learning
* ``discr_preds``: One of the values ``pracmln.EVIDENCE_PREDS`` or
                ``pracmln.QUERY_PREDS``, specifying whether ``qpreds``
                or the ``epreds`` parameters should be used.


Discriminative log-likelihood Learning
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Discriminative variant of log-likelihood learning.

* ``optimizer``: the optimization routine to be used.


.. warning::
    
    Log-likelihood learning is intractable for most but the smallest
    examples. If you deal with realistic problems you should consider
    using a more efficient learning method.


Discriminative Pseudo-likelihood Learning
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Discriminative learner for the pseudo-log-likelihood learning algorithm.

* ``optimizer``: the optimization routine to be used.


Discriminative Pseudo-likelihood Learning (with Custom Grounding)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Discriminative learner for the pseudo-log-likelihood learning with custom grounding.

* ``optimizer``: the optimization routine to be used.

Discriminative Composite-likelihood Learning
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Discriminative variant of composite likelihood learning.

Optimization Techniques
^^^^^^^^^^^^^^^^^^^^^^^

In addition to the learning method, different optimization techniques
can be specified in `pracmln`. The type of the optimizer and their
parameters can be specified in the additional parameters text field
in the :doc:`mlnlearningtool` by specifying a parameter ``optimizer=<algo>``.
Currently, the following optimization techniques are supported.

BFGS (Broyden–Fletcher–Goldfarb–Shanno algorithm)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Command: ``optimizer='bfgs'``
* Additional Parameters:
   *  ``maxiter=<int>``: Specifies the maximal number of gradient ascent steps.

.. note::

    This is the standard SciPy implementation

Conjugate Gradient
~~~~~~~~~~~~~~~~~~

* Command: ``optimizer='cg'``
* Additional Parameters:
   *  ``maxiter=<int>``: Specifies the maximal number of gradient ascent steps.

.. note::

    This is the standard SciPy implementation

