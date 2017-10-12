# Markov Logic Networks - Grounding
#
# (C) 2013 by Daniel Nyga (nyga@cs.tum.edu)
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

from collections import defaultdict

from dnutils import logs

from .fastconj import FastConjunctionGrounding
from ..util import unifyDicts, dict_union
from ..constants import HARD
from ..errors import SatisfiabilityException
from ...utils.undo import Ref, Number, List, ListDict, Boolean
from ...logic.common import Logic
from ...utils.multicore import with_tracing, checkmem

import types
from multiprocessing.pool import Pool

# this readonly global is for multiprocessing to exploit copy-on-write
# on linux systems
global_bpll_grounding = None

logger = logs.getlogger(__name__)

# multiprocessing function
def create_formula_groundings(formula, unsatfailure=True):
    checkmem()
    results = []
    if global_bpll_grounding.mrf.mln.logic.islitconj(formula):
        for res in global_bpll_grounding.itergroundings_fast(formula):
            checkmem()
            results.append(res)
    else:
        for gf in formula.itergroundings(global_bpll_grounding.mrf, simplify=False):
            checkmem()
            stat = []
            for gndatom in gf.gndatoms():
                world = list(global_bpll_grounding.mrf.evidence)
                var = global_bpll_grounding.mrf.variable(gndatom)
                for validx, value in var.itervalues():
                    var.setval(value, world)
                    truth = gf(world)
                    if truth != 0:
                        stat.append((var.idx, validx, truth))
                    elif unsatfailure and gf.weight == HARD and gf(global_bpll_grounding.mrf.evidence) != 1:
                        print()
                        gf.print_structure(global_bpll_grounding.mrf.evidence)
                        raise SatisfiabilityException('MLN is unsatisfiable due to hard constraint violation {} (see above)'.format(global_bpll_grounding.mrf.formulas[gf.idx]))
            results.append((gf.idx, stat))
    return results


class BPLLGroundingFactory(FastConjunctionGrounding):
    """
    Grounding factory for efficient grounding of conjunctions for
    pseudo-likelihood learning.
    """


    def __init__(self, mrf, formulas=None, cache=None, **params):
        FastConjunctionGrounding.__init__(self, mrf, simplify=False, unsatfailure=False, formulas=formulas, cache=cache, **params)
        self._stat = {}
        self._varidx2fidx = defaultdict(set)


    def itergroundings_fast(self, formula):
        """
        Recursively generate the groundings of a conjunction. Prunes the
        generated grounding tree in case that a formula cannot be rendered
        true by subsequent literals.
        """
        # make a copy of the formula to avoid side effects
        formula = formula.ground(self.mrf, {}, partial=True)
        children = [formula] if not hasattr(formula, 'children') else formula.children
        # make equality constraints access their variable domains
        # this is a _really_ dirty hack but it does the job ;-)
        vardoms = formula.vardoms()


        def eqvardoms(self, v=None, c=None):
            if v is None: v = defaultdict(set)
            for a in self.args:
                if self.mln.logic.isvar(a):
                    v[a] = vardoms[a]
            return v

        for child in children:
            if isinstance(child, Logic.Equality):
                setattr(child, 'vardoms', types.MethodType(eqvardoms, child))
        lits = sorted(children, key=self._conjsort)
        for gf in self._itergroundings_fast(formula, lits, 0, assignment={}, variables=[]):
            yield gf


    def _itergroundings_fast(self, formula, constituents, cidx, assignment, variables, falsevar=None, level=0):
        if cidx == len(constituents):
            # no remaining literals to ground. return the ground formula
            # and statistics
            stat = [(varidx, validx, count) for (varidx, validx, count) in variables]
            yield formula.idx, stat
            return
        c = constituents[cidx]
        # go through all remaining groundings of the current constituent
        for varass in c.itervargroundings(self.mrf, partial=assignment):
            gnd = c.ground(self.mrf, dict_union(varass, assignment))
            # check if it violates a hard constraint
            if formula.weight == HARD and gnd(self.mrf.evidence) < 1:
                raise SatisfiabilityException('MLN is unsatisfiable by evidence due to hard constraint violation {} (see above)'.format(global_bpll_grounding.mrf.formulas[formula.idx]))
            if isinstance(gnd, Logic.Equality):
                # if an equality grounding is false in a conjunction, we can
                # stop since the  conjunction cannot be rendered true in any
                # grounding that follows
                if gnd.truth(None) == 0: continue
                for gf in self._itergroundings_fast(formula, constituents, cidx + 1, dict_union(assignment, varass),
                                                    variables, falsevar, level + 1):
                    yield gf
            else:
                var = self.mrf.variable(gnd.gndatom)
                world_ = list(self.mrf.evidence)
                stat = []
                skip = False
                falsevar_ = falsevar
                vars_ = list(variables)
                for validx, value in var.itervalues():
                    var.setval(value, world_)
                    truth = gnd(world_)
                    if truth == 0 and value == var.evidence_value():
                        # if the evidence value renders the current
                        # consituent false and there was already a false
                        # literal in the grounding path, we can prune the
                        # tree since no grounding will be true
                        if falsevar is not None and falsevar != var.idx:
                            skip = True
                            break
                        else:
                            # if there was no literal false so far, we
                            # collect statistics only for the current literal
                            # and only if all future literals will be true
                            # by evidence
                            vars_ = []
                            falsevar_ = var.idx
                    if truth > 0 and falsevar is None:
                        stat.append((var.idx, validx, truth))
                if falsevar is not None and falsevar == var.idx:
                    # in case of non-mutual exclusive values take only the
                    # values that render all literals true
                    # example: soft-functional constraint with
                    # !foo(?x) ^ foo(?y), x={X,Y,Z} where the evidence
                    # foo(Z) is true
                    # here the grounding !foo(X) ^ foo(Y) is false:
                    # !foo(X) is true for foo(Z) and foo(Y) and
                    # (!foo(Z) ^ !foox(X) ^ !foo(Y))
                    #       foo(Y) is true for foo(Y)
                    #   both are only true for foo(Y)
                    stat = set(variables).intersection(stat)
                    skip = not bool(stat)  # skip if no values remain
                if skip: continue
                for gf in self._itergroundings_fast(formula, constituents, cidx + 1, dict_union(assignment, varass), vars_ + stat, falsevar=falsevar_, level=level + 1):
                    yield gf


    def _itergroundings(self, simplify=False, unsatfailure=False):
        global global_bpll_grounding
        global_bpll_grounding = self
        if self.multicore:
            pool = Pool(maxtasksperchild=1)
            try:
                for gndresult in pool.imap(with_tracing(create_formula_groundings), self.formulas):
                    for fidx, stat in gndresult:
                        for (varidx, validx, val) in stat:
                            self._varidx2fidx[varidx].add(fidx)
                            self._addstat(fidx, varidx, validx, val)
                        checkmem()
                    yield None
            except Exception as e:
                logger.error('Error in child process. Terminating pool...')
                pool.close()
                raise e
            finally:
                pool.terminate()
                pool.join()
        else:
            for gndresult in map(create_formula_groundings, self.formulas):
                for fidx, stat in gndresult:
                    for (varidx, validx, val) in stat:
                        self._varidx2fidx[varidx].add(fidx)
                        self._addstat(fidx, varidx, validx, val)
                yield None


    def _addstat(self, fidx, varidx, validx, inc=1):
        if fidx not in self._stat:
            self._stat[fidx] = {}
        d = self._stat[fidx]
        if varidx not in d:
            d[varidx] = [0] * self.mrf.variable(varidx).valuecount()
        d[varidx][validx] += inc


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# here comes some very experimental code. which is currently not in use.


class FormulaGrounding(object):
    """
    Represents a particular (partial) grounding of a formula with respect to
    _one_ predicate and in terms of disjoint sets of variables occurring in
    that formula. A grounding of the formula is represented as a list of
    assignments of the independent variable sets.
    It represents a node in the search tree for weighted SAT solving.
    Additional fields:
    - depth:    the depth of this formula grounding (node) in the search tree
                The root node (the formula with no grounded variable has
                depth 0.
    - children: list of formula groundings that have been generated from this
                fg.
    """


    def __init__(self, formula, mrf, parent=None, assignment=None):
        """
        Instantiates the formula grounding for a given
        - formula:    the formula grounded in this node
        - mrf:        the MRF associated to this problem
        - parent:     the formula grounding this fg has been created from
        - assignment: dictionary mapping variables to their values
        """
        self.mrf = mrf
        self.formula = formula
        self.parent = Ref(parent)
        self.trueGroundings = Number(0.)
        self.processed = Boolean(False)
        if parent is None:
            self.depth = 0
        else:
            self.depth = parent.depth + 1
        self.children = List()
        self.assignment = assignment
        self.domains = ListDict()
        if parent is None:
            for var in self.formula.getVariables(self.mrf.mln):
                self.domains.extend(var, list(self.mrf.domains[
                                                  self.formula.getVarDomain(
                                                      var, self.mrf.mln)]))
        else:
            for (v, d) in parent.domains.items():
                self.domains.extend(v, list(d))
        self.domains.epochEndsHere()


    def epochEndsHere(self):
        for mem in (
        self.parent, self.trueGroundings, self.children, self.domains,
        self.processed):
            mem.epochEndsHere()


    def undoEpoch(self):
        for mem in (
        self.parent, self.trueGroundings, self.children, self.domains,
        self.processed):
            mem.undoEpoch()


    def countGroundings(self):
        """
        Computes the number of ground formulas subsumed by this
        FormulaGrounding based on the domain sizes of the free (unbound)
        variables.
        """
        gf_count = 1
        for var in self.formula.getVariables(self.mrf):
            domain = self.mrf.domains[self.formula.getVarDomain(var, self.mrf)]
            gf_count *= len(domain)
        return gf_count


    def ground(self, assignment=None):
        """
        Takes an assignment of _one_ particular variable and
        returns a new FormulaGrounding with that assignment. If
        the assignment renders the formula false true, then
        the number of groundings rendered true is returned.
        """
        # calculate the number of ground formulas resulting from
        # the remaining set of free variables
        if assignment is None:
            assignment = {}
        gf_count = 1
        for var in set(self.formula.getVariables(self.mrf.mln)).difference(
                list(assignment.keys())):
            domain = self.domains[var]
            if domain is None: return 0.
            gf_count *= len(domain)
        gf = self.formula.ground(self.mrf, assignment,
                                 allowPartialGroundings=True)
        gf.weight = self.formula.weight
        for var_name, val in assignment.items(): break
        self.domains.drop(var_name, val)
        # if the simplified gf reduces to a TrueFalse instance, then
        # we return the no of groundings if it's true, or 0 otherwise.
        truth = gf.isTrue(self.mrf.evidence)
        if truth in (True, False):
            if not truth:
                trueGFCounter = 0.0
            else:
                trueGFCounter = gf_count
            self.trueGroundings += trueGFCounter
            return trueGFCounter
        # if the truth value cannot be determined yet, we return
        # a new formula grounding with the given assignment
        else:
            new_grounding = FormulaGrounding(gf, self.mrf, parent=self,
                                             assignment=assignment)
            self.children.append(new_grounding)
            return new_grounding


    def __str__(self):
        return str(self.assignment) + '->' + str(self.formula) + str(
            self.domains)  # str(self.assignment)


    def __repr__(self):
        return str(self)


class SmartGroundingFactory(object):
    """
    Implements a factory for generating the groundings of one formula. 
    The groundings are created incrementally with one
    particular ground atom being presented at a time.
    fields:
    - formula:    the (ungrounded) formula representing the root of the
                  search tree
    - mrf:        the respective MRF
    - root:       a FormulaGrounding instance representing the root of the
                  tree, i.e. an ungrounded formula
    - costs:      the costs accumulated so far
    - depth2fgs:  mapping from a depth of the search tree to the
                  corresponding list of FormulaGroundings
    - vars_processed:     list of variable names that have already been
                          processed so far
    - values_processed:   mapping from a variable name to the list of values
                          of that vaiable that
                          have already been assigned so far.
    This class maintains a stack of all its fields in order allow undoing
    groundings that have been performed once.
    """


    def __init__(self, formula, mrf):
        """
        formula might be a formula or a FormulaGrounding instance.
        """
        self.mrf = mrf
        self.costs = .0
        if isinstance(formula, Logic.Formula):
            self.formula = formula
            self.root = FormulaGrounding(formula, mrf)
        elif isinstance(formula, FormulaGrounding):
            self.root = formula
            self.formula = formula.formula
        self.values_processed = ListDict()
        self.variable_stack = List(None)
        self.var2fgs = ListDict({None: [self.root]})
        self.gndAtom2fgs = ListDict()
        self.manipulatedFgs = List()


    def epochEndsHere(self):
        for mem in (self.values_processed, self.variable_stack, self.var2fgs,
                    self.gndAtom2fgs, self.manipulatedFgs):
            mem.epochEndsHere()
        for fg in self.manipulatedFgs:
            fg.epochEndsHere()


    def undoEpoch(self):
        for fg in self.manipulatedFgs:
            fg.undoEpoch()
        for mem in (self.values_processed, self.variable_stack, self.var2fgs,
                    self.gndAtom2fgs, self.manipulatedFgs):
            mem.undoEpoch()


    def ground(self, gndAtom):
        """
        Expects a ground atom and creates all groundings 
        that can be derived by it in terms of FormulaGroundings.
        """
        self.manipulatedFgs.clear()
        # get all variable assignments of matching literals in the formula 
        var_assignments = {}
        for lit in self.formula.iterLiterals():
            assignment = self.gndAtom2Assignment(lit, gndAtom)
            if assignment is not None:
                unifyDicts(var_assignments, assignment)
        cost = .0

        # first evaluate formula groundings that contain 
        # this gnd atom as an artifact
        min_depth = None
        min_depth_fgs = []
        for fg in self.gndAtom2fgs.get(gndAtom, []):
            if len(self.variable_stack) <= fg.depth:
                continue
            if fg.processed.value:
                continue
            truth = fg.formula.isTrue(self.mrf.evidence)
            if truth is not None:
                cost -= fg.trueGroundings.value
                if not fg in self.manipulatedFgs:
                    self.manipulatedFgs.append(fg)
                fg.processed.set(True)
                self.var2fgs.drop(self.variable_stack[fg.depth], fg)
                if not fg.parent.obj in self.manipulatedFgs:
                    self.manipulatedFgs.append(fg.parent.obj)
                fg.parent.obj.children.remove(
                    fg)  # this is just for the visualization/ no real functionality
                if fg.depth == min_depth or min_depth is None:
                    min_depth_fgs.append(fg)
                    min_depth = fg.depth
                if fg.depth < min_depth:
                    min_depth = fg.depth
                    min_depth_fgs = []
                    min_depth_fgs.append(fg)
        for fg in min_depth_fgs:
            # add the costs which are aggregated by the root of the subtree 
            if fg.formula.isTrue(fg.mrf.evidence) == False:
                cost += fg.formula.weight * fg.countGroundings()
                fg.trueGroundings.set(cost)
        # straighten up the variable stack and formula groundings
        # since they might have become empty
        for var in list(self.variable_stack):
            if self.var2fgs[var] is None:
                self.variable_stack.remove(var)
        for var, value in var_assignments.items():
            # skip the variables with values that have already been processed
            if not var in self.variable_stack:
                depth = len(self.variable_stack)
            else:
                depth = self.variable_stack.index(var)
            queue = list(self.var2fgs[self.variable_stack[depth - 1]])
            while len(queue) > 0:
                fg = queue.pop()
                # first hinge the new variable grounding to all possible
                # parents, i.e. all FormulaGroundings with depth - 1...
                if fg.depth < depth:
                    vars_and_values = [{var: value}]
                # ...then hinge all previously seen subtrees to the newly
                # created formula groundings...
                elif fg.depth >= depth and fg.depth < len( self.variable_stack) - 1:
                    vars_and_values = [{self.variable_stack[fg.depth + 1]: v}
                                       for v in self.values_processed[
                                           self.variable_stack[fg.depth + 1]]]
                # ...and finally all variable values that are not part of
                # the subtrees i.e. variables that are currently NOT in the
                # variable_stack (since they have been removed due to falsity
                # of a formula grounding).
                else:
                    vars_and_values = []
                    varNotInTree = None
                    for varNotInTree in [v for v in
                                         list(self.values_processed.keys()) if
                                         v not in self.variable_stack]: break
                    if varNotInTree is None: continue
                    values = self.values_processed[varNotInTree]
                    for v in values:
                        vars_and_values.append({varNotInTree: v})
                for var_value in vars_and_values:
                    for var_name, val in var_value.items(): break
                    if not fg.domains.contains(var_name, val): continue
                    gnd_result = fg.ground(var_value)
                    if not fg in self.manipulatedFgs:
                        self.manipulatedFgs.append(fg)
                    # if the truth value of a grounding cannot be determined...
                    if isinstance(gnd_result, FormulaGrounding):
                        # collect all ground atoms that have been created as 
                        # as artifacts for future evaluation
                        artifactGndAtoms = [a for a in
                                            gnd_result.formula.getGroundAtoms()
                                            if not a == gndAtom]
                        for artGndAtom in artifactGndAtoms:
                            self.gndAtom2fgs.put(artGndAtom, gnd_result)
                        if not var_name in self.variable_stack:
                            self.variable_stack.append(var_name)
                        self.var2fgs.put(self.variable_stack[gnd_result.depth],
                                         gnd_result)
                        queue.append(gnd_result)
                    else:
                        # ...otherwise it's true/false; add its costs and
                        # discard it.
                        if self.formula.isHard and gnd_result > 0.:
                            gnd_result = float('inf')
                        cost += gnd_result
            self.values_processed.put(var, value)
        return cost

    def printTree(self):
        queue = [self.root]
        print('---')
        while len(queue) > 0:
            n = queue.pop()
            space = ''
            for _ in range(n.depth): space += '--'
            print(space + str(n))
            queue.extend(n.children.list)
        print('---')


    def gndAtom2Assignment(self, lit, atom):
        """
        Returns None if the literal and the atom do not match.
        """
        if type(lit) is Logic.Equality or \
                        lit.predName != atom.predName:
            return None
        assignment = {}
        for p1, p2 in zip(lit.params, atom.params):
            if self.mrf.mln.logic.isVar(p1):
                assignment[p1] = p2
            elif p1 != p2:
                return None
        return assignment
