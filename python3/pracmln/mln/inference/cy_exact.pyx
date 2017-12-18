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
from dnutils import logs, ProgressBar

from .infer import Inference
from multiprocessing import Pool
from ..mrfvars import FuzzyVariable
from ..constants import auto, HARD
from ..errors import SatisfiabilityException
from ..grounding.fastconj import FastConjunctionGrounding
from ..util import Interval, colorize
from ...utils.multicore import with_tracing
from ...logic.fol import FirstOrderLogic
from ...logic.common import Logic
from numpy.ma.core import exp


logger = logs.getlogger(__name__)

# this readonly global is for multiprocessing to exploit copy-on-write
# on linux systems
global_enumAsk = None


cdef eval_queries(float* world):
    '''
    Evaluates the queries given a possible world.
    '''
    numerators = [0] * len(global_enumAsk.queries)
    denominator = 0
    expsum = 0
    for gf in global_enumAsk.grounder.itergroundings():
        if global_enumAsk.soft_evidence_formula(gf):
            expsum += gf.noisyor(world) * gf.weight
        else:
            truth = gf(world)
            if gf.weight == HARD:
                if truth in Interval(']0,1['):
                    raise Exception('No real-valued degrees of truth are allowed in hard constraints.')
                if truth == 1:
                    continue
                else:
                    return numerators, 0
            expsum += gf(world) * gf.weight
    expsum = exp(expsum)
    # update numerators
    for i, query in enumerate(global_enumAsk.queries):
        if query(world):
            numerators[i] += expsum
    denominator += expsum
    return numerators, denominator


class EnumerationAsk(Inference):
    """
    Inference based on enumeration of (only) the worlds compatible with the
    evidence; supports soft evidence (assuming independence)
    """

    def __init__(self, mrf, queries, **params):
        Inference.__init__(self, mrf, queries, **params)
        self.grounder = FastConjunctionGrounding(mrf, simplify=False, unsatfailure=False, formulas=mrf.formulas, cache=auto, verbose=False, multicore=False)
        # self.grounder = DefaultGroundingFactory(mrf, simplify=False,
        # unsatfailure=False, formulas=list(mrf.formulas), cache=auto,
        # verbose=False)
        # check consistency of fuzzy and functional variables
        for variable in self.mrf.variables:
            variable.consistent(self.mrf.evidence, strict=isinstance(variable, FuzzyVariable))


    def _run(self):
        """
        verbose: whether to print results (or anything at all, in fact)
        details: (given that verbose is true) whether to output additional
                 status information
        debug:   (given that verbose is true) if true, outputs debug
                 information, in particular the distribution over possible
                 worlds
        debugLevel: level of detail for debug mode
        """
        # check consistency with hard constraints:
        self._watch.tag('check hard constraints', verbose=self.verbose)
        hcgrounder = FastConjunctionGrounding(self.mrf, simplify=False, unsatfailure=True, 
                                              formulas=[f for f in self.mrf.formulas if f.weight == HARD], 
                                              **(self._params + {'multicore': False, 'verbose': False}))
        for gf in hcgrounder.itergroundings():
            if isinstance(gf, Logic.TrueFalse) and gf.truth() == .0:
                raise SatisfiabilityException('MLN is unsatisfiable due to hard constraint violation by evidence: {} ({})'.format(str(gf), str(self.mln.formula(gf.idx))))
        self._watch.finish('check hard constraints')
        # compute number of possible worlds
        worlds = 1
        for variable in self.mrf.variables:
            values = variable.valuecount(self.mrf.evidence)
            worlds *= values
        numerators = [0.0 for i in range(len(self.queries))]
        denominator = 0.
        # start summing
        logger.debug("Summing over %d possible worlds..." % worlds)
        if worlds > 500000 and self.verbose:
            print(colorize('!!! %d WORLDS WILL BE ENUMERATED !!!' % worlds, (None, 'red', True), True))
        k = 0
        self._watch.tag('enumerating worlds', verbose=self.verbose)
        global global_enumAsk
        global_enumAsk = self
        bar = None
        if self.verbose:
            bar = ProgressBar(steps=worlds, color='green')
        if self.multicore:
            pool = Pool()
            logger.debug('Using multiprocessing on {} core(s)...'.format(pool._processes))
            try:
                for num, denum in pool.imap(with_tracing(eval_queries), self.mrf.worlds()):
                    denominator += denum
                    k += 1
                    for i, v in enumerate(num):
                        numerators[i] += v
                    if self.verbose: bar.inc()
            except Exception as e:
                logger.error('Error in child process. Terminating pool...')
                pool.close()
                raise e
            finally:
                pool.terminate()
                pool.join()
        else:  # do it single core
            for world in self.mrf.worlds():
                # compute exp. sum of weights for this world
                num, denom = eval_queries(world)
                denominator += denom
                for i, _ in enumerate(self.queries):
                    numerators[i] += num[i]
                k += 1
                if self.verbose:
                    bar.update(float(k) / worlds)
        logger.debug("%d worlds enumerated" % k)
        self._watch.finish('enumerating worlds')
        if 'grounding' in self.grounder.watch.tags:
            self._watch.tags['grounding'] = self.grounder.watch['grounding']
        if denominator == 0:
            raise SatisfiabilityException(
                'MLN is unsatisfiable. All probability masses returned 0.')
        # normalize answers
        dist = [float(x) / denominator for x in numerators]
        result = {}
        for q, p in zip(self.queries, dist):
            result[str(q)] = p
        return result

    def soft_evidence_formula(self, gf):
        truths = [a.truth(self.mrf.evidence) for a in gf.gndatoms()]
        if None in truths:
            return False
        return isinstance(self.mrf.mln.logic, FirstOrderLogic) and any([t in Interval('(0,1)') for t in truths])
