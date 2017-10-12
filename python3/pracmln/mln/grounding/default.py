# Markov Logic Networks - Default Grounding
#
# (C) 2013 by Daniel Nyga (nyga@cs.uni-bremen.de)
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
from dnutils import logs, ProgressBar, ifnone

from ..util import fstr, dict_union, StopWatch
from ..constants import auto, HARD
from ..errors import SatisfiabilityException


logger = logs.getlogger(__name__)


CACHE_SIZE = 100000


class DefaultGroundingFactory:
    """
    Implementation of the default grounding algorithm, which
    creates ALL ground atoms and ALL ground formulas.

    :param simplify:        if `True`, the formula will be simplified according to the
                            evidence given.
    :param unsatfailure:    raises a :class:`mln.errors.SatisfiabilityException` if a 
                            hard logical constraint is violated by the evidence.
    """
    
    def __init__(self, mrf, simplify=False, unsatfailure=False, formulas=None, cache=auto, **params):
        self.mrf = mrf
        self.formulas = ifnone(formulas, list(self.mrf.formulas))
        self.total_gf = 0
        for f in self.formulas:
            self.total_gf += f.countgroundings(self.mrf)
        self.grounder = None
        self._cachesize = CACHE_SIZE if cache is auto else cache
        self._cache = None
        self.__cacheinit = False
        self.__cachecomplete = False
        self._params = params
        self.watch = StopWatch()
        self.simplify = simplify
        self.unsatfailure = unsatfailure
        
        
    @property
    def verbose(self):
        return self._params.get('verbose', False)
    
    
    @property
    def multicore(self):
        return self._params.get('multicore', False)
    
    
    @property
    def iscached(self):
        return self._cache is not None and self.__cacheinit

    
    @property
    def usecache(self):
        return self._cachesize is not None and self._cachesize > 0
    
    
    def _cacheinit(self):
        if False:#self.total_gf > self._cachesize:
            logger.warning('Number of formula groundings (%d) exceeds cache size (%d). Caching is disabled.' % (self.total_gf, self._cachesize))
        else:
            self._cache = []
        self.__cacheinit = True
    
    
    def itergroundings(self):
        """
        Iterates over all formula groundings.
        """
        self.watch.tag('grounding', verbose=self.verbose)
        if self.grounder is None:
            self.grounder = iter(self._itergroundings(simplify=self.simplify, unsatfailure=self.unsatfailure))
        if self.usecache and not self.iscached:
            self._cacheinit()
        counter = -1
        while True:
            counter += 1
            if self.iscached and len(self._cache) > counter:
                yield self._cache[counter]
            elif not self.__cachecomplete:
                try:
                    gf = next(self.grounder)
                except StopIteration:
                    self.__cachecomplete = True
                    return
                else:
                    if self._cache is not None:
                        self._cache.append(gf)
                    yield gf
            else: return
        self.watch.finish('grounding')
        if self.verbose: print()
            
            
    def _itergroundings(self, simplify=False, unsatfailure=False):
        if self.verbose: 
            bar = ProgressBar(color='green')
        for i, formula in enumerate(self.formulas):
            if self.verbose: bar.update((i+1) / float(len(self.formulas)))
            for gndformula in formula.itergroundings(self.mrf, simplify=simplify):
                if unsatfailure and gndformula.weight == HARD and gndformula(self.mrf.evidence) == 0:
                    print()
                    gndformula.print_structure(self.mrf.evidence)
                    raise SatisfiabilityException('MLN is unsatisfiable due to hard constraint violation %s (see above)' % self.mrf.formulas[gndformula.idx])
                yield gndformula
                
                
class EqualityConstraintGrounder(object):
    """
    Grounding factory for equality constraints only.
    """
    
    def __init__(self, mrf, domains, mode, eq_constraints):
        """
        Initialize the equality constraint grounder with the given MLN
        and formula. A formula is required that contains all variables
        in the equalities in order to infer the respective domain names.
        
        :param mode: either ``alltrue`` or ``allfalse``
        """
        self.constraints = eq_constraints
        self.mrf = mrf
        self.truth = {'alltrue': 1, 'allfalse': 0}[mode]
        self.mode = mode
        eqvars = [c for eq in eq_constraints for c in eq.args if self.mrf.mln.logic.isvar(c)]
        self.vardomains = dict([(v, d) for v, d in domains.items() if v in eqvars]) 
    
    def iter_valid_variable_assignments(self):
        """
        Yields all variable assignments for which all equality constraints
        evaluate to true.
        """
        return self._iter_valid_variable_assignments(list(self.vardomains.keys()), {}, self.constraints)

    
    def _iter_valid_variable_assignments(self, variables, assignments, eq_groundings):
        if not variables: 
            yield assignments
            return
        eq_groundings = [eq for eq in eq_groundings if not all([not self.mrf.mln.logic.isvar(a) for a in eq.args])]
        variable = variables[0]
        for value in self.mrf.domains[self.vardomains[variable]]:
            new_eq_groundings = []
            goon = True
            for eq in eq_groundings:
                geq = eq.ground(None, {variable: value}, partial=True)
                t = geq(None)
                if t is not None and t != self.truth:
                    goon = False
                    break
                new_eq_groundings.append(geq)
            if not goon: continue
            for assignment in self._iter_valid_variable_assignments(variables[1:], dict_union(assignments, {variable: value}), new_eq_groundings):
                yield assignment
    
    @staticmethod
    def vardoms_from_formula(mln, formula, *varnames):
        if isinstance(formula, str):
            formula = mln.logic.parse_formula(formula)
        vardomains = {}
        f_vardomains = formula.vardoms(mln)
        for var in varnames:
            if var not in f_vardomains:
                raise Exception('Variable %s not bound to a domain by formula %s' % (var, fstr(formula)))
            vardomains[var] = f_vardomains[var]
        return vardomains
                
        
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    