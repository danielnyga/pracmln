# MARKOV LOGIC NETWORKS
#
# (C) 2011-2014 by Daniel Nyga (nyga@cs.tum.edu)
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

import types
from multiprocessing.pool import Pool

from .default import DefaultGroundingFactory
from ..mlnpreds import FunctionalPredicate, SoftFunctionalPredicate, FuzzyPredicate
from ..util import dict_union, rndbatches, cumsum
from ..errors import SatisfiabilityException
from ..constants import HARD
from ...logic.common import Logic
from ...logic.fuzzy import FuzzyLogic
from ...utils.multicore import with_tracing
from collections import defaultdict


logger = logs.getlogger(__name__)

# this readonly global is for multiprocessing to exploit copy-on-write
# on linux systems
global_fastConjGrounding = None


# multiprocessing function
def create_formula_groundings(formulas):
    gfs = []
    for formula in sorted(formulas, key=global_fastConjGrounding._fsort):
        if global_fastConjGrounding.mrf.mln.logic.islitconj(formula) or global_fastConjGrounding.mrf.mln.logic.isclause(formula):
            for gf in global_fastConjGrounding.itergroundings_fast(formula):
                gfs.append(gf)
        else:
            for gf in formula.itergroundings(global_fastConjGrounding.mrf, simplify=True):
                gfs.append(gf)
    return gfs


class FastConjunctionGrounding(DefaultGroundingFactory):
    """
    Fairly fast grounding of conjunctions pruning the grounding tree if a
    formula is rendered false by the evidence. Performs some heuristic
    sorting such that equality constraints are evaluated first.
    """


    def __init__(self, mrf, simplify=False, unsatfailure=False, formulas=None,
                 cache=None, **params):
        DefaultGroundingFactory.__init__(self, mrf, simplify=simplify, unsatfailure=unsatfailure, formulas=formulas, cache=cache, **params)


    def _conjsort(self, e):
        if isinstance(e, Logic.Equality):
            return 0.5
        elif isinstance(e, Logic.TrueFalse):
            return 1
        elif isinstance(e, Logic.GroundLit):
            if self.mrf.evidence[e.gndatom.idx] is not None:
                return 2
            elif type(self.mrf.mln.predicate(e.gndatom.predname)) in (FunctionalPredicate, SoftFunctionalPredicate):
                return 3
            else:
                return 4
        elif isinstance(e, Logic.Lit) and type(
                self.mrf.mln.predicate(e.predname)) in (FunctionalPredicate, SoftFunctionalPredicate, FuzzyPredicate):
            return 5
        elif isinstance(e, Logic.Lit):
            return 6
        else:
            return 7


    @staticmethod
    def _fsort(f):
        if f.weight == HARD:
            return 0
        else:
            return 1


    def itergroundings_fast(self, formula):
        """
        Recursively generate the groundings of a conjunction that do _not_
        have a definite truth value yet given the evidence.
        """
        # make a copy of the formula to avoid side effects
        formula = formula.ground(self.mrf, {}, partial=True, simplify=True)
        children = [formula] if not hasattr(formula, 'children') else formula.children
        # make equality constraints access their variable domains
        # this is a _really_ dirty hack but it does the job ;-)
        variables = formula.vardoms()

        def eqvardoms(self, v=None, c=None):
            if v is None:
                v = defaultdict(set)
            for a in self.args:
                if self.mln.logic.isvar(a):
                    v[a] = variables[a]
            return v


        for child in children:
            if isinstance(child, Logic.Equality):
                # replace the vardoms method in this equality instance by
                # our customized one
                setattr(child, 'vardoms', types.MethodType(eqvardoms, child))
        lits = sorted(children, key=self._conjsort)
        truthpivot, pivotfct = (1, FuzzyLogic.min_undef) if isinstance(formula, Logic.Conjunction) else ((0, FuzzyLogic.max_undef) if isinstance(formula, Logic.Disjunction) else (None, None))
        for gf in self._itergroundings_fast(formula, lits, 0, pivotfct, truthpivot, {}):
            yield gf


    def _itergroundings_fast(self, formula, constituents, cidx, pivotfct, truthpivot, assignment, level=0):
        if truthpivot == 0 and (isinstance(formula, Logic.Conjunction) or self.mrf.mln.logic.islit(formula)):
            if formula.weight == HARD:
                raise SatisfiabilityException('MLN is unsatisfiable given evidence due to hard constraint violation: {}'.format(str(formula)))
            return
        if truthpivot == 1 and (isinstance(formula, Logic.Disjunction) or self.mrf.mln.logic.islit(formula)):
            return
        if cidx == len(constituents):
            # we have reached the end of the formula constituents
            gf = formula.ground(self.mrf, assignment, simplify=True)
            if isinstance(gf, Logic.TrueFalse):
                return
            yield gf
            return
        c = constituents[cidx]
        for varass in c.itervargroundings(self.mrf, partial=assignment):
            newass = dict_union(assignment, varass)
            ga = c.ground(self.mrf, newass)
            truth = ga.truth(self.mrf.evidence)
            if truth is None:
                truthpivot_ = truthpivot
            elif truthpivot is None:
                truthpivot_ = truth
            else:
                truthpivot_ = pivotfct(truthpivot, truth)
            for gf in self._itergroundings_fast(formula, constituents, cidx + 1, pivotfct, truthpivot_, newass, level + 1):
                yield gf

    def _itergroundings(self, simplify=True, unsatfailure=True):
        # generate all groundings
        if not self.formulas:
            return
        global global_fastConjGrounding
        global_fastConjGrounding = self
        batches = list(rndbatches(self.formulas, 20))
        batchsizes = [len(b) for b in batches]
        if self.verbose:
            bar = ProgressBar(steps=sum(batchsizes), color='green')
            i = 0
        if self.multicore:
            pool = Pool()
            try:
                for gfs in pool.imap(with_tracing(create_formula_groundings), batches):
                    if self.verbose:
                        bar.inc(batchsizes[i])
                        bar.label(str(cumsum(batchsizes, i + 1)))
                        i += 1
                    for gf in gfs: yield gf
            except Exception as e:
                logger.error('Error in child process. Terminating pool...')
                pool.close()
                raise e
            finally:
                pool.terminate()
                pool.join()
        else:
            for gfs in map(create_formula_groundings, batches):
                if self.verbose:
                    bar.inc(batchsizes[i])
                    bar.label(str(cumsum(batchsizes, i + 1)))
                    i += 1
                for gf in gfs: yield gf
