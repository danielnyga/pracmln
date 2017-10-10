
Tutorial: Learning and Inference in Markov Logic Networks
=========================================================

This tutorial will explain how to learn the parameters of a Markov 
logic network from a training database and how to use to resulting 
model to answer queries. We will make use of the well-known 
``smoking scenario`` as used by Richardson and Domingos.

We work in the ``examples/smokers`` directory.

The Smoking Scenario
^^^^^^^^^^^^^^^^^^^^

The Smoking scenario models the dependencies between smoking and 
having cancer. Moreover, we consider the social network induced by 
a ''friends'' relation. We thus define the following predicates::

    Smokes(person)
    Cancer(person)
    Friends(person,person)

and define a rule stating that cancer follows from smoking,::

    Smokes(p) => Cancer(p)

and further model the symmetry of the friendship relation and its influence on smoking habits::
  
    Friends(p1,p2) <=> Friends (p2,p2)
    Friends(p1,p2) => (Smokes(p1) <=> Smokes(p2))

The last rule states that if two persons are friends, they either 
both smoke or both do not smoke.

Learning
^^^^^^^^

We use the :doc:`mlnlearningtool` to learn the weights of the Markov logic network.::

    cd /path/to/probcog/examples/smokers
    mlnlearn

We pick the "PRACMLN" engine and the MLN defined above (i.e. 
``smoking.mln``). The MLN is displayed in the editor. To use 
the internal engine one has to add a ``0.0``-weight to all formulas 
what are not terminated by a period as a ``0.0``-weight is not 
implicitly assumed for formulas without weights when using the 
internal engine. 

Next, we choose the desired training database (e.g. 
``smoking-train.db``) and learning method (e.g. 
''pseudo-log-likelihood with blocking''). 


Having made our selections, we start the learning process by 
clicking the ''Learn'' button at the bottom of the dialog, which 
gives us weights, e.g.::

    1.126769  Smokes(x) => Cancer(x)
    1.577776  Friends(x, y) => (Smokes(x) <=> Smokes(y))

The resulting MLN is saved to the filename we entered under ''Output filename''.

Inference
^^^^^^^^^

We now invoke the :doc:`mlnquerytool` from the console.::

    mlnquery

To test the model described and trained above, we consider the following evidence database:::

    Cancer(Ann)
    !Cancer(Bob)
    !Friends(Ann,Bob)

Using this evidence, we want to infer the smoking habits of Ann and 
Bob: Our queries include ``Smokes``, ``Smokes(Ann) v 
Smokes(Bob)``, ``Smokes(Ann)`` and ``Smokes(Bob)``. 
For this small evidence database, we can still use exact inference. 
We got the following results:::

    0.436830  Smokes(Ann)
    0.152667  Smokes(Ann) ^ Smokes(Bob)
    0.528921  Smokes(Ann) v Smokes(Bob)
    0.244758  Smokes(Bob)

As expected, it is more likely for Ann to smoke than for Bob. 

Exact inference can also give us the full distribution over possible 
worlds which we obtain by using ``debug=True`` as an 
additional parameter. The first 3 of 256 possible worlds:::

    1   0.81%   Friends(Ann,Ann)  Friends(Ann,Bob)  Friends(Bob,Ann)  Friends(Bob,Bob)  
                Smokes(Ann)  Smokes(Bob)  Cancer(Ann)   Cancer(Bob)  
                5.242963e+03 <- 8.56 <- 1.1 1.1 1.6 1.6 1.6 1.6
    2   0.26%   Friends(Ann,Ann)  Friends(Ann,Bob)  Friends(Bob,Ann)  Friends(Bob,Bob)  
                Smokes(Ann)  Smokes(Bob)  Cancer(Ann)   !Cancer(Bob)  
                1.699132e+03 <- 7.44 <- 1.1 1.6 1.6 1.6 1.6
    3   0.26%   Friends(Ann,Ann)  Friends(Ann,Bob)  Friends(Bob,Ann)  Friends(Bob,Bob)
                Smokes(Ann)  Smokes(Bob) !Cancer(Ann)   Cancer(Bob)
                1.699132e+03 <- 7.44 <- 1.1 1.6 1.6 1.6 1.6

The end of each line (i.e. each third line in the results table 
above) contains the exponentiated sum of weights, the sum of 
weights and the individual weights that were summed (rounded values).

We can also use MC-SAT for this model and evidence databse. We set 
the maximum number of steps to 5000, and we set SampleSAT's p 
parameter to ``0.6`` and control the intermediate output using the 
additional parameters ``p=0.6, infoInterval=500, 
resultsInterval=1000``. We obtain:::

    0.449800  Smokes(Ann)
    0.146000  Smokes(Ann) ^ Smokes(Bob)
    0.548800  Smokes(Ann) v Smokes(Bob)
    0.245000  Smokes(Bob)

We observe that MC-Sat gives us reasonable approximations results 
(compared to the exact solution calculated above) for this evidence 
database.