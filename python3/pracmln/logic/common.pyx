# LOGIC -- COMMON BASE CLASSES
#
# (C) 2012-2013 by Daniel Nyga (nyga@cs.uni-bremen.de)
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

import sys

from dnutils import logs, ifnone

from .grammar import StandardGrammar, PRACGrammar
from ..mln.util import fstr, dict_union, colorize
from ..mln.errors import NoSuchDomainError, NoSuchPredicateError
from ..mln.constants import HARD, predicate_color, inherit, auto
from collections import defaultdict
import itertools
from functools import reduce
from misc import *

logger = logs.getlogger(__name__)

cdef class Logic():
    """
    Abstract factory class for instantiating logical constructs like conjunctions,
    disjunctions etc. Every specifc logic should implement the methods and return
    an instance of the respective element. They also might override the respective
    implementations and behavior of the logic.
    """

    def __init__(self, grammar, mln):
        """
        Creates a new instance of a Logic factory class.

        :param grammar:     an instance of grammar.Grammar
        :param mln:         the MLN instance that the logic shall be tied to.
        """
        if grammar not in ('StandardGrammar', 'PRACGrammar'):
            raise Exception('Invalid grammar: %s' % grammar)
        self.grammar = eval(grammar)(self)
        self.mln = mln

    def __getstate__(self):
        d = self.__dict__.copy()
        d['grammar'] = type(self.grammar).__name__
        return d

    def __setstate__(self, d):
        self.__dict__ = d
        self.grammar = eval(d['grammar'])(self)

    def isvar(self, identifier):
        """
        Returns True if identifier is a logical variable according
        to the used grammar, and False otherwise.
        """
        return self.grammar.isvar(identifier)

    def isconstant(self, identifier):
        """
        Returns True if identifier is a logical constant according
        to the used grammar, and False otherwise.
        """
        return self.grammar.isConstant(identifier)

    def istemplvar(self, s):
        """
        Returns True if `s` is template variable or False otherwise.
        """
        return self.grammar.istemplvar(s)

    def parse_formula(self, formula):
        """
        Returns the Formula object parsed by the grammar.
        """
        return self.grammar.parse_formula(formula)

    def parse_predicate(self, string):
        return self.grammar.parse_predicate(string)

    def parse_atom(self, string):
        return self.grammar.parse_atom(string)

    def parse_domain(self, decl):
        return self.grammar.parse_domain(decl)

    def parse_literal(self, lit):
        return self.grammar.parse_literal(lit)

    # Q(gsoc): possible modifications required upon removing inner classes ...
    def islit(self, f):
        """
        Determines whether or not a formula is a literal.
        """
        return isinstance(f, Logic.GroundLit) or isinstance(f, Logic.Lit) or isinstance(f, Logic.GroundAtom)

    # Q(gsoc): possible modifications required upon removing inner classes ...
    def iseq(self, f):
        """
        Determines wheter or not a formula is an equality consttaint.
        """
        return isinstance(f, Logic.Equality)

    # Q(gsoc): possible modifications required upon removing inner classes ...
    def islitconj(self, f):
        """
        Returns true if the given formula is a conjunction of literals.
        """
        if self.islit(f): return True
        if not isinstance(f, Logic.Conjunction):
            if not isinstance(f, Logic.Lit) and \
                 not isinstance(f, Logic.GroundLit) and \
                 not isinstance(f, Logic.Equality) and \
                 not isinstance(f, Logic.TrueFalse):
                return False
            return True
        for child in f.children:
            if not isinstance(child, Logic.Lit) and \
                not isinstance(child, Logic.GroundLit) and \
                not isinstance(child, Logic.Equality) and \
                not isinstance(child, Logic.TrueFalse):
                return False
        return True

    # Q(gsoc): possible modifications required upon removing inner classes ...
    def isclause(self, f):
        """
        Returns true if the given formula is a clause (a disjunction of literals)
        """
        if self.islit(f): return True
        if not isinstance(f, Logic.Disjunction):
            if not isinstance(f, Logic.Lit) and \
                 not isinstance(f, Logic.GroundLit) and \
                 not isinstance(f, Logic.Equality) and \
                 not isinstance(f, Logic.TrueFalse):
                return False
            return True
        for child in f.children:
            if not isinstance(child, Logic.Lit) and \
                not isinstance(child, Logic.GroundLit) and \
                not isinstance(child, Logic.Equality) and \
                not isinstance(child, Logic.TrueFalse):
                return False
        return True

    # Q(gsoc): possible modifications required upon removing inner classes ...
    def negate(self, formula):
        """
        Returns a negation of the given formula.

        The original formula will be copied first. The resulting negation is tied
        to the same mln and will have the same formula index. Also performs
        a rudimentary simplification in case of `formula` is a (ground) literal
        or equality.
        """
        if isinstance(formula, Logic.Lit) or isinstance(formula, Logic.GroundLit):
            ret = formula.copy()
            ret.negated = not ret.negated
        elif isinstance(formula, Logic.Equality):
            ret = formula.copy()
            ret.negated = not ret.negated
        else:
            ret = self.negation([formula.copy(mln=formula.mln, idx=None)], mln=formula.mln, idx=formula.idx)
        return ret

    def conjugate(self, children, mln=None, idx=inherit):
        """
        Returns a conjunction of the given children.

        Performs rudimentary simplification in the sense that if children
        has only one element, it returns this element (e.g. one literal)
        """
        if not children:
            return self.true_false(0, mln=ifnone(mln, self.mln), idx=idx)
        elif len(children) == 1:
            return children[0].copy(mln=ifnone(mln, self.mln), idx=idx)
        else:
            return self.conjunction(children, mln=ifnone(mln,self.mln), idx=idx)

    def disjugate(self, children, mln=None, idx=inherit):
        """
        Returns a conjunction of the given children.

        Performs rudimentary simplification in the sense that if children
        has only one element, it returns this element (e.g. one literal)
        """
        if not children:
            return self.true_false(0, mln=ifnone(mln, self.mln), idx=idx)
        elif len(children) == 1:
            return children[0].copy(mln=ifnone(mln, self.mln), idx=idx)
        else:
            return self.disjunction(children, mln=ifnone(mln,self.mln), idx=idx)

    @staticmethod
    def iter_eq_varassignments(eq, f, mln):
        """
        Iterates over all variable assignments of an (in)equality constraint.

        Needs a formula since variables in equality constraints are not typed per se.
        """
        doms = f.vardoms()
        eqVars_ = eq.vardoms()
        if not set(eqVars_).issubset(doms):
            raise Exception('Variable in (in)equality constraint not bound to a domain: %s' % eq)
        eqVars = {}
        for v in eqVars_:
            eqVars[v] = doms[v]
        for assignment in Logic._iter_eq_varassignments(mln, eqVars, {}):
            yield assignment

    @staticmethod
    def _iter_eq_varassignments(mrf, variables, assignment):
        if len(variables) == 0:
            yield assignment
            return
        variables = dict(variables)
        variable, domName = variables.popitem()
        domain = mrf.domains[domName]
        for value in domain:
            for assignment in Logic._iter_eq_varassignments(mrf, variables, dict_union(assignment, {variable: value})):
                yield assignment

    @staticmethod
    def clauseset(cnf):
        """
        Takes a formula in CNF and returns a set of clauses, i.e. a list of sets
        containing literals. All literals are converted into strings.
        """
        clauses = []
        if isinstance(cnf, Logic.Disjunction):
            clauses.append(set(map(str, cnf.children)))
        elif isinstance(cnf, Logic.Conjunction):
            for disj in cnf.children:
                clause = set()
                clauses.append(clause)
                if isinstance(disj, Logic.Disjunction):
                    for c in disj.children:
                        clause.add(str(c))
                else:
                    clause.add(str(disj))
        else:
            clauses.append(set([str(cnf)]))
        return clauses

    @staticmethod
    def cnf(gfs, formulas, logic, allpos=False):
        """
        convert the given ground formulas to CNF
        if allPositive=True, then formulas with negative weights are negated to make all weights positive
        @return a new pair (gndformulas, formulas)

        .. warning::

        If allpos is True, this might have side effects on the formula weights of the MLN.

        """
        # get list of formula indices which we must negate
        formulas_ = []
        negated = []
        if allpos:
            for f in formulas:
                if f.weight < 0:
                    negated.append(f.idx)
                    f = logic.negate(f)
                    f.weight = -f.weight
                formulas_.append(f)
        # get CNF version of each ground formula
        gfs_ = []
        for gf in gfs:
            # non-logical constraint
            if not gf.islogical(): # don't apply any transformations to non-logical constraints
                if gf.idx in negated:
                    gf.negate()
                gfs_.append(gf)
                continue
            # logical constraint
            if gf.idx in negated:
                cnf = logic.negate(gf).cnf()
            else:
                cnf = gf.cnf()
            if isinstance(cnf, Logic.TrueFalse): # formulas that are always true or false can be ignored
                continue
            cnf.idx = gf.idx
            gfs_.append(cnf)
        # return modified formulas
        return gfs_, formulas_

    def conjunction(self, *args, **kwargs):
        """
        Returns a new instance of a Conjunction object.
        """
        raise Exception('%s does not implement conjunction()' % str(type(self)))

    def disjunction(self, *args, **kwargs):
        """
        Returns a new instance of a Disjunction object.
        """
        raise Exception('%s does not implement disjunction()' % str(type(self)))

    def negation(self, *args, **kwargs):
        """
        Returns a new instance of a Negation object.
        """
        raise Exception('%s does not implement negation()' % str(type(self)))

    def implication(self, *args, **kwargs):
        """
        Returns a new instance of a Implication object.
        """
        raise Exception('%s does not implement implication()' % str(type(self)))

    def biimplication(self, *args, **kwargs):
        """
        Returns a new instance of a Biimplication object.
        """
        raise Exception('%s does not implement biimplication()' % str(type(self)))

    def equality(self, *args, **kwargs):
        """
        Returns a new instance of a Equality object.
        """
        raise Exception('%s does not implement equality()' % str(type(self)))

    def exist(self, *args, **kwargs):
        """
        Returns a new instance of a Exist object.
        """
        raise Exception('%s does not implement exist()' % str(type(self)))

    def gnd_atom(self, *args, **kwargs):
        """
        Returns a new instance of a GndAtom object.
        """
        raise Exception('%s does not implement gnd_atom()' % str(type(self)))

    def lit(self, *args, **kwargs):
        """
        Returns a new instance of a Lit object.
        """
        raise Exception('%s does not implement lit()' % str(type(self)))

    def litgroup(self, *args, **kwargs):
        """
        Returns a new instance of a Lit object.
        """
        raise Exception('%s does not implement litgroup()' % str(type(self)))

    def gnd_lit(self, *args, **kwargs):
        """
        Returns a new instance of a GndLit object.
        """
        raise Exception('%s does not implement gnd_lit()' % str(type(self)))

    def count_constraint(self, *args, **kwargs):
        """
        Returns a new instance of a CountConstraint object.
        """
        raise Exception('%s does not implement count_constraint()' % str(type(self)))

    def true_false(self, *args, **kwargs):
        """
        Returns a new instance of a TrueFalse constant object.
        """
        raise Exception('%s does not implement true_false()' % str(type(self)))

    def create(self, clazz, *args, **kwargs):
        """
        Takes the type of a logical element (class type) and creates
        a new instance of it.
        """
        return clazz(*args, **kwargs)




# this is a little hack to make nested classes pickleable
Constraint = Logic.Constraint
Formula = Logic.Formula
ComplexFormula = Logic.ComplexFormula
Conjunction = Logic.Conjunction
Disjunction = Logic.Disjunction
Lit = Logic.Lit
LitGroup = Logic.LitGroup
GroundLit = Logic.GroundLit
GroundAtom = Logic.GroundAtom
Equality = Logic.Equality
Implication = Logic.Implication
Biimplication = Logic.Biimplication
Negation = Logic.Negation
Exist = Logic.Exist
TrueFalse = Logic.TrueFalse
NonLogicalConstraint = Logic.NonLogicalConstraint
CountConstraint = Logic.CountConstraint
GroundCountConstraint = Logic.GroundCountConstraint
