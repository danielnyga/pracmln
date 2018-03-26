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
from dnutils import logs
from dnutils.console import barstr

from collections import defaultdict

import numpy
from dnutils import logs, out
from dnutils.console import barstr
from numpy.ma.core import sqrt, log

from ..constants import HARD
from ..errors import SatisfiabilityException
from ..grounding.bpll import BPLLGroundingFactory
from ..grounding.default import DefaultGroundingFactory
from .common import DiscriminativeLearner, AbstractLearner
from ..util import fsum, temporary_evidence

logger = logs.getlogger(__name__)


class BPLL(AbstractLearner):
    '''
    Pseudo-log-likelihood learning with blocking, i.e. a generalization
    of PLL which takes into consideration the fact that the truth value of a
    blocked atom cannot be inverted without changing a further atom's truth
    value from the same block.
    This learner is fairly efficient, as it computes f and grad based only
    on a sufficient statistic.
    '''
    
    def __init__(self, mrf, **params):
        AbstractLearner.__init__(self, mrf, **params)
        self._pls = None
        self._stat = None
        self._varidx2fidx = None
        self._lastw = None
        
    def _prepare(self):
        logger.debug("computing statistics...") 
        self._compute_statistics()
#         print self._stat
    
    def _pl(self, varidx, w):
        '''
        Computes the pseudo-likelihoods for the given variable under weights w. 
        '''
        var = self.mrf.variable(varidx)
        values = var.valuecount()
        gfs = self._varidx2fidx.get(varidx)
        if gfs is None: # no list was saved, so the truth of all formulas is unaffected by the variable's value
            # uniform distribution applies
            p = 1.0 / values
            return [p] * values
        sums = [0] * values#numpy.zeros(values)
        for fidx in gfs:
            for validx, n in enumerate(self._stat[fidx][varidx]):
                if w[fidx] == HARD: 
                    # set the prob mass of every value violating a hard constraint to None
                    # to indicate a globally inadmissible value. We will set those ones to 0 afterwards.
                    if n == 0: sums[validx] = None
                elif sums[validx] is not None:
                    # don't set it if this value has already been assigned marked as inadmissible.
                    sums[validx] += n * w[fidx]
        expsums = [numpy.exp(s) if s is not None else 0 for s in sums]#numpy.exp(numpy.array(sums))
        z = sum(expsums)
        if z == 0: raise SatisfiabilityException('MLN is unsatisfiable: all probability masses of variable %s are zero.' % str(var))
        return [w_ / z for w_ in expsums]
#         sum_max = numpy.max(sums)
#         sums -= sum_max
#         expsums = numpy.sum(numpy.exp(sums))
#         s = numpy.log(expsums)    
#         return numpy.exp(sums - s)

    def write_pls(self):
        for var in self.mrf.variables:
            print(repr(var))
            for i, value in var.itervalues():
                print('    ', barstr(width=50, color='magenta', percent=self._pls[var.idx][i]) + ('*' if var.evidence_value_index() == i else ' '), i, value)

    def _compute_pls(self, w):
        if self._pls is None or self._lastw is None or self._lastw != list(w):
            self._pls = [self._pl(var.idx, w) for var in self.mrf.variables]
            self._lastw = list(w)
#             self.write_pls()
    
    def _f(self, w):
        self._compute_pls(w)
        probs = []
        for var in self.mrf.variables:
            p = self._pls[var.idx][var.evidence_value_index()]
            if p == 0: p = 1e-10 # prevent 0 probabilities
            probs.append(p)
        return fsum(list(map(log, probs)))

    def _grad(self, w):
        self._compute_pls(w)
        grad = numpy.zeros(len(self.mrf.formulas), numpy.float64)        
        for fidx, varval in self._stat.items():
            for varidx, counts in varval.items():
                evidx = self.mrf.variable(varidx).evidence_value_index()
                g = counts[evidx]
                for i, val in enumerate(counts):
                    g -= val * self._pls[varidx][i]
                grad[fidx] += g
        self.grad_opt_norm = sqrt(float(fsum([x * x for x in grad])))
        return numpy.array(grad)

    def _addstat(self, fidx, varidx, validx, inc=1):
        if fidx not in self._stat:
            self._stat[fidx] = {}
        d = self._stat[fidx]
        if varidx not in d:
            d[varidx] = [0] * self.mrf.variable(varidx).valuecount()
        d[varidx][validx] += inc
        
    def _compute_statistics(self):
        '''
        computes the statistics upon which the optimization is based
        '''
        self._stat = {}
        self._varidx2fidx = defaultdict(set)
        grounder = DefaultGroundingFactory(self.mrf, simplify=False, unsatfailure=True, verbose=self.verbose, cache=0)
        for f in grounder.itergroundings():
            for gndatom in f.gndatoms():
                var = self.mrf.variable(gndatom)
                with temporary_evidence(self.mrf):
                    for validx, value in var.itervalues():
                        var.setval(value, self.mrf.evidence)
                        truth = f(self.mrf.evidence) 
                        if truth != 0:
                            self._varidx2fidx[var.idx].add(f.idx)
                            self._addstat(f.idx, var.idx, validx, truth)
                
                
class DPLL(BPLL, DiscriminativeLearner):
    '''
    Discriminative pseudo-log-likelihood learning.
    '''

    def _f(self, w, **params):
        self._compute_pls(w)
        probs = []
        for var in self.mrf.variables:
            if var.predicate.name in self.epreds: continue
            p = self._pls[var.idx][var.evidence_value_index()]
            if p == 0: p = 1e-10 # prevent 0 probabilities
            probs.append(p)
        return fsum(list(map(log, probs)))

    def _grad(self, w, **params):        
        self._compute_pls(w)
        grad = numpy.zeros(len(self.mrf.formulas), numpy.float64)        
        for fidx, varval in self._stat.items():
            for varidx, counts in varval.items():
                if self.mrf.variable(varidx).predicate.name in self.epreds: continue
                evidx = self.mrf.variable(varidx).evidence_value_index()
                g = counts[evidx]
                for i, val in enumerate(counts):
                    g -= val * self._pls[varidx][i]
                grad[fidx] += g
        self.grad_opt_norm = sqrt(float(fsum([x * x for x in grad])))
        return numpy.array(grad)


class BPLL_CG(BPLL):
    
    def _prepare(self):
        grounder = BPLLGroundingFactory(self.mrf, multicore=self.multicore, verbose=self.verbose)
        for _ in grounder.itergroundings(): pass
        self._stat = grounder._stat
        self._varidx2fidx = grounder._varidx2fidx
        

class DBPLL_CG(DPLL):
    
    def _prepare(self):
        grounder = BPLLGroundingFactory(self.mrf, multicore=self.multicore, verbose=self.verbose)
        for _ in grounder.itergroundings(): pass
        self._stat = grounder._stat
        self._varidx2fidx = grounder._varidx2fidx
