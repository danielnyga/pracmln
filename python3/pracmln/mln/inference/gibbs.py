# -*- coding: utf-8 -*-
#
# Markov Logic Networks
#
# (C) 2006-2011 by Dominik Jain (jain@cs.tum.edu)
# 
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import random
from collections import defaultdict

import numpy
from dnutils import ProgressBar

from .mcmc import MCMCInference
from ..constants import ALL
from ..grounding.fastconj import FastConjunctionGrounding
from ...logic.common import Logic


class GibbsSampler(MCMCInference):

    def __init__(self, mrf, queries=ALL, **params):
        MCMCInference.__init__(self, mrf, queries, **params)
        self.var2gf = defaultdict(set)
        grounder = FastConjunctionGrounding(mrf, simplify=True, unsatfailure=True, cache=None)
        for gf in grounder.itergroundings():
            if isinstance(gf, Logic.TrueFalse): continue
            vars_ = set([self.mrf.variable(a).idx for a in gf.gndatoms()])
            for v in vars_: self.var2gf[v].add(gf)
    
    @property
    def chains(self):
        return self._params.get('chains', 1)
    
    @property
    def maxsteps(self):
        return self._params.get('maxsteps', 500)
    

    class Chain(MCMCInference.Chain):
    
        def __init__(self, infer, queries):
            MCMCInference.Chain.__init__(self, infer, queries)
            mrf = infer.mrf
            
        def _valueprobs(self, var, world):
            sums = [0] * var.valuecount()
            for gf in self.infer.var2gf[var.idx]:
                possible_values = []
                for i, value in var.itervalues(self.infer.mrf.evidence):
                    possible_values.append(i)
                    world_ = var.setval(value, list(world))
                    truth = gf(world_)
                    if truth == 0 and gf.ishard:
                        sums[i] = None
                    elif sums[i] is not None and not gf.ishard:
                        sums[i] += gf.weight * truth
                # set all impossible values to None (i.e. prob 0) since they
                # might still be have a value of 0 in sums 
                for i in [j for j in range(len(sums)) if j not in possible_values]: sums[i] = None
            expsums = numpy.array([numpy.exp(s) if s is not None else 0 for s in sums])
            Z = sum(expsums) 
            probs = expsums / Z
            return probs
        
        def step(self):
            mrf = self.infer.mrf
            # reassign values by sampling from the conditional distributions given the Markov blanket
            state = list(self.state)
            for var in mrf.variables:
                # compute distribution to sample from
                values = list(var.values())
                if len(values) == 1: # do not sample if we have evidence 
                    continue  
                probs = self._valueprobs(var, self.state)
                # check for soft evidence and greedily satisfy it if possible                
                idx = None
#                 if isinstance(var, BinaryVariable):
#                     atom = var.gndatoms[0]
#                     p = mrf.evidence[var.gndatoms[0]]
#                     if p is not None:
#                         belief = self.soft_evidence_frequency(atom)
#                         if p > belief and expsums[1] > 0:
#                             idx = 1
#                         elif p < belief and expsums[0] > 0:
#                             idx = 0
                # sample value
                if idx is None:
                    r = random.uniform(0, 1)                    
                    idx = 0
                    s = probs[0]
                    while r > s:
                        idx += 1
                        s += probs[idx]
                var.setval(values[idx], self.state)
            # update results
            self.update(self.state)
    

    def _run(self, **params):
        """
        infer one or more probabilities P(F1 | F2)
        what: a ground formula (string) or a list of ground formulas (list of strings) (F1)
        given: a formula as a string (F2)
        set evidence according to given conjunction (if any)
        """
#         if softEvidence is None:
#             self.softEvidence = self.mln.softEvidence
#         else:
#             self.softEvidence = softEvidence
        # initialize chains
        chains = MCMCInference.ChainGroup(self)
        for i in range(self.chains):
            chain = GibbsSampler.Chain(self, self.queries)
            chains.chain(chain)
#             if self.softEvidence is not None:
#                 chain.setSoftEvidence(self.softEvidence)
        # do Gibbs sampling
#         if verbose and details: print "sampling..."
        converged = 0
        steps = 0
        if self.verbose:
            bar = ProgressBar(color='green', steps=self.maxsteps)
        while converged != self.chains and steps < self.maxsteps:
            converged = 0
            steps += 1
            for chain in chains.chains:
                chain.step()
            if self.verbose:
                bar.inc()
                bar.label('%d / %d' % (steps, self.maxsteps))
#                 if self.useConvergenceTest:
#                     if chain.converged and numSteps >= minSteps:
#                         converged += 1
#             if verbose and details:
#                 if numSteps % infoInterval == 0:
#                     print "step %d (fraction converged: %.2f)" % (numSteps, float(converged) / numChains)
#                 if numSteps % resultsInterval == 0:
#                     chainGroup.getResults()
#                     chainGroup.printResults(shortOutput=True)
        # get the results
        return chains.results()[0]
