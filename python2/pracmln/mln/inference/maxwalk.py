# -*- coding: utf-8-*-
#
# Markov Logic Networks
#
# (C) 2012-2015 by Daniel Nyga
#     2006-2011 by Dominik Jain
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

from dnutils import ProgressBar

from pracmln.mln.inference.mcmc import MCMCInference
from pracmln.mln.grounding.fastconj import FastConjunctionGrounding
from pracmln.logic.common import Logic
from pracmln.mln.constants import HARD, ALL

class SAMaxWalkSAT(MCMCInference):
    '''
    A MaxWalkSAT MPE solver using simulated annealing.
    '''
    
    
    def __init__(self, mrf, queries=ALL, state=None, **params):
        MCMCInference.__init__(self, mrf, queries, **params)
        if state is None:
            self.state = self.random_world(self.mrf.evidence)
        else:
            self.state = state
        self.sum = 0
        self.var2gf = defaultdict(set)
        self.weights = list(self.mrf.mln.weights)
        formulas = []
        for f in self.mrf.formulas:
            if f.weight < 0:
                f_ = self.mrf.mln.logic.negate(f)
                f_.weight = - f.weight
                formulas.append(f_.nnf())
        grounder = FastConjunctionGrounding(mrf, formulas=formulas, simplify=True, unsatfailure=True)
        for gf in grounder.itergroundings():
            if isinstance(gf, Logic.TrueFalse): continue
            vars_ = set(map(lambda a: self.mrf.variable(a).idx, gf.gndatoms()))
            for v in vars_: self.var2gf[v].add(gf)
            self.sum += (self.hardw if gf.weight == HARD else gf.weight) * (1 - gf(self.state))
        
        
    @property
    def thr(self):
        return self._params.get('thr', 0)
    
    
    @property
    def hardw(self):
        return self._params.get('hardw', 10)
        
        
    @property
    def maxsteps(self):
        return self._params.get('maxsteps', 500)
    
    
    def _run(self):
        i = 0 
        i_max = self.maxsteps
        thr = self.thr
        if self.verbose:
            bar = ProgressBar(steps=i_max, color='green')
        while i < i_max and self.sum > self.thr:
            # randomly choose a variable to modify
            var = self.mrf.variables[random.randint(0, len(self.mrf.variables)-1)]
            evdict = var.value2dict(var.evidence_value(self.mrf.evidence))
            valuecount = var.valuecount(evdict) 
            if valuecount == 1: # this is evidence 
                continue
            # compute the sum of relevant gf weights before the modification
            sum_before = 0
            for gf in self.var2gf[var.idx]:
                sum_before += (self.hardw if gf.weight == HARD else gf.weight) * (1 - gf(self.state)) 
            # modify the state
            validx = random.randint(0, valuecount - 1)
            value = [v for _, v in var.itervalues(evdict)][validx]
            oldstate = list(self.state)
            var.setval(value, self.state)
            # compute the sum after the modification
            sum_after = 0
            for gf in self.var2gf[var.idx]:
                sum_after += (self.hardw if gf.weight == HARD else gf.weight) * (1 - gf(self.state))
            # determine whether to keep the new state            
            keep = False
            improvement = sum_after - sum_before
            if improvement < 0 or sum_after <= thr: 
                prob = 1.0
                keep = True
            else: 
                prob = (1.0 - min(1.0, abs(improvement / self.sum))) * (1 - (float(i) / i_max))
                keep = random.uniform(0.0, 1.0) <= prob
#                 keep = False # !!! no annealing
            # apply new objective value
            if keep: self.sum += improvement
            else: self.state = oldstate
            # next iteration
            i += 1
            if self.verbose:
                bar.label('sum = %f' % self.sum)
                bar.inc()
        if self.verbose:
            print "SAMaxWalkSAT: %d iterations, sum=%f, threshold=%f" % (i, self.sum, self.thr)
        self.mrf.mln.weights = self.weights
        return dict([(str(q), self.state[q.gndatom.idx]) for q in self.queries])
    
    