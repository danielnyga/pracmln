# -*- coding: utf-8 -*-
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
from dnutils import ProgressBar

from .common import *
from ..grounding.default import DefaultGroundingFactory
from ..constants import HARD
from ..errors import SatisfiabilityException


class LL(AbstractLearner):
    """
    Exact Log-Likelihood learner.
    """
    
    def __init__(self, mrf, **params):
        AbstractLearner.__init__(self, mrf, **params)
        self._stat = None
        self._ls = None
        self._eworld_idx = None
        self._lastw = None

    
    def _prepare(self):
        self._compute_statistics()
        

    def _l(self, w):
        """
        computes the likelihoods of all possible worlds under weights w
        """
        if self._lastw is None or list(w) != self._lastw:
            self._lastw = list(w)
            expsums = []
            for fvalues in self._stat:
                s = 0
                hc_violation = False
                for fidx, val in fvalues.items():
                    if self.mrf.mln.formulas[fidx].weight == HARD:
                        if val == 0:
                            hc_violation = True
                            break
                    else:
                        s += val * w[fidx]
                if hc_violation: 
                    expsums.append(0)
                else:
                    expsums.append(exp(s))
            z = sum(expsums)
            if z == 0: raise SatisfiabilityException('MLN is unsatisfiable: probability masses of all possible worlds are zero.')
            self._ls = [v / z for v in expsums] 
        return self._ls 
            

    def _f(self, w):
        ls = self._l(w)
        return numpy.log(ls[self._eworld_idx])
                
    
    def _grad(self, w):
        ls = self._l(w)
        grad = numpy.zeros(len(self.mrf.formulas), numpy.float64)
        for widx, values in enumerate(self._stat):
            for fidx, count in values.items():
                if widx == self._eworld_idx:
                    grad[fidx] += count
                grad[fidx] -= count * ls[widx]
        return grad 


    def _compute_statistics(self):
        self._stat = []
        grounder = DefaultGroundingFactory(self.mrf)
        eworld = list(self.mrf.evidence)
        if self.verbose:
            bar = ProgressBar(steps=self.mrf.countworlds(), color='green')
        for widx, world in self.mrf.iterallworlds():
            if self.verbose:
                bar.label(str(widx))
                bar.inc()
            values = {}
            self._stat.append(values)
            if self._eworld_idx is None and world == eworld:
                self._eworld_idx = widx  
            for gf in grounder.itergroundings():
                truth = gf(world)
                if truth != 0: values[gf.idx] = values.get(gf.idx, 0) + truth
