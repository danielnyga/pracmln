
Inference Methods
=================

Full posterior distributions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The following algorithms compute the full posterior distribution
over a set of variables :math:`Q` given the evidence :math:`E, P(Q|E)`.

Enumeration-Ask
~~~~~~~~~~~~~~~

Performs exact inference by enumerating all possible worlds :math:`x\in\mathcal{X}` that
are consistent with the evidence :math:`E`, i.e.

.. math::
    
     P(Q|E) = \frac{\sum_{x \models E\land Q}^{} \phi(x)}{\sum_{x'\models E}{\phi(x')}}


.. warning::

    This is intractable for all but the smallest reasoning problems.
    

MC-SAT
~~~~~~

Performs approximate inference using the `MC-SAT` algorithm.


Gibbs Sampling
~~~~~~~~~~~~~~

Performs Gibbs sampling on the ground MRF.



Most Probable Explanation (MPE)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In some cases, one is not interested in the full posterior distribution
:math:`P(Q|E)` over query variables :math:`Q` given evidence :math:`E`,
but only in the most probable variable assignment of :math:`Q, \text{arg max}_QP(Q|E)`
`pracmln` provides two algorithms to perform this kind of `MPE` inference
(which is sometimes also referred to as `maximum a-posteriori (MAP)`
inference.

MaxWalk-SAT
~~~~~~~~~~~

A randomized weighted satisfiability solver that performs simulated
annealing.

Parameters:

* ``maxsteps``: the maximum number simulated annealing steps
* ``thr``: the threshold for the sum of unsatisfied weighted formulas that needs be undercut for the algorithm to terminate
* ``hardw``: a constant weight that will temporarily be attached to hard logical formulas. 

WCSP
~~~~

Performs exact MPE inference by converting the ground MRF into an
equivalent weighted constraint satisfaction problem (WCSP) and
solving it using the `toulbar2` :cite:`allouche2010toulbar2` solver. For more details, see :cite:`jain09modref`.


.. bibliography:: refs.bib
   :cited:






