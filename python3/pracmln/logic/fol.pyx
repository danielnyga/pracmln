# FIRST-ORDER LOGIC -- PROCESSING
#
# (C) 2013 by Daniel Nyga (nyga@cs.uni-bremen.de)
# (C) 2007-2012 by Dominik Jain
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
from dnutils import ifnone

from .common import Logic
from .common import Constraint as Super_Constraint
from .common import Formula as Super_Formula
from .common import ComplexFormula as Super_ComplexFormula
from .common import Conjunction as Super_Conjunction
from .common import Disjunction as Super_Disjunction
from .common import Lit as Super_Lit
from .common import LitGroup as Super_LitGroup
from .common import GroundLit as Super_GroundLit
from .common import GroundAtom as Super_GroundAtom
from .common import Equality as Super_Equality
from .common import Implication as Super_Implication
from .common import Biimplication as Super_Biimplication
from .common import Negation as Super_Negation
from .common import Exist as Super_Exist
from .common import TrueFalse as Super_TrueFalse
from .common import NonLogicalConstraint as Super_NonLogicalConstraint
from .common import CountConstraint# as Super_CountConstraint
from .common import GroundCountConstraint as Super_GroundCountConstraint
from ..mln.util import fstr


cdef class Constraint(Super_Constraint):
    pass

#class Formula(Super_Formula, Constraint):
cdef class Formula(Super_Formula):
    def noisyor(self, world):
        """
        Computes the noisy-or distribution of this formula.
        """
        return self.cnf().noisyor(world)


    def _getEvidenceTruthDegreeCW(self, gndAtom, worldValues):
        """
            gets (soft or hard) evidence as a degree of belief from 0 to 1, making the closed world assumption,
            soft evidence has precedence over hard evidence
        """
        se = self._getSoftEvidence(gndAtom)
        if se is not None:
            return se if (True == worldValues[gndAtom.idx] or None == worldValues[gndAtom.idx]) else 1.0 - se # TODO allSoft currently unsupported
        return 1.0 if worldValues[gndAtom.idx] else 0.0


    def _noisyOr(self, mln, worldValues, disj):
        if isinstance(disj, GroundLit):
            lits = [disj]
        elif isinstance(disj, TrueFalse):
            return disj.isTrue(worldValues)
        else:
            lits = disj.children
        prod = 1.0
        for lit in lits:
            p = mln._getEvidenceTruthDegreeCW(lit.gndAtom, worldValues)
            if not lit.negated:
                factor = p
            else:
                factor = 1.0 - p
            prod *= 1.0 - factor
        return 1.0 - prod

#class ComplexFormula(Super_ComplexFormula, Formula):
cdef class ComplexFormula(Super_ComplexFormula):
    pass

#class Lit(Super_Lit, Formula):
cdef class Lit(Super_Lit):
    pass

#class Litgroup(Super_LitGroup, Formula):
cdef class LitGroup(Super_LitGroup):
    pass

cdef class GroundAtom(Super_GroundAtom):
    pass

#class GroundLit(Super_GroundLit, Formula):
cdef class GroundLit(Super_GroundLit):
    def noisyor(self, world):
        truth = self(world)
        if self.negated: truth = 1. - truth
        return truth

#class Disjunction(Super_Disjunction, ComplexFormula):
cdef class Disjunction(Super_Disjunction):
    def truth(self, world):
        cdef bint dontKnow = False
        for child in self.children:
            childValue = child.truth(world)
            if childValue == 1:
                return 1
            if childValue is None:
                dontKnow = True
        if dontKnow:
            return None
        else:
            return 0


    def simplify(self, world):
        sf_children = []
        for child in self.children:
            child = child.simplify(world)
            t = child.truth(world)
            if t == 1:
                return self.mln.logic.true_false(1, mln=self.mln, idx=self.idx)
            elif t == 0: continue
            else: sf_children.append(child)
        if len(sf_children) == 1:
            return sf_children[0].copy(idx=self.idx)
        elif len(sf_children) >= 2:
            return self.mln.logic.disjunction(sf_children, mln=self.mln, idx=self.idx)
        else:
            return self.mln.logic.true_false(0, mln=self.mln, idx=self.idx)


    def noisyor(self, world):
        prod = 1.0
        for lit in self.children:
            p = ifnone(lit(world), 1)
            if not lit.negated:
                factor = p
            else:
                factor = 1.0 - p
            prod *= 1.0 - factor
        return 1.0 - prod

#class Conjunction(Super_Conjunction, ComplexFormula):
cdef class Conjunction(Super_Conjunction):
    def truth(self, world):
        cdef bint dontKnow = False
        for child in self.children:
            childValue = child.truth(world)
            if childValue == 0:
                return 0.
            if childValue is None:
                dontKnow = True
        if dontKnow:
            return None
        else:
            return 1.


    def simplify(self, world):
        sf_children = []
        for child in self.children:
            child = child.simplify(world)
            t = child.truth(world)
            if t == 0:
                return self.mln.logic.true_false(0, mln=self.mln, idx=self.idx)
            elif t == 1: pass
            else: sf_children.append(child)
        if len(sf_children) == 1:
            return sf_children[0].copy(idx=self.idx)
        elif len(sf_children) >= 2:
            return self.mln.logic.conjunction(sf_children, mln=self.mln, idx=self.idx)
        else:
            return self.mln.logic.true_false(1, mln=self.mln, idx=self.idx)


    def noisyor(self, world):
        cnf = self.cnf()
        prod = 1.0
        if isinstance(cnf, Conjunction):
            for disj in cnf.children:
                prod *= disj.noisyor(world)
        else:
            prod *= cnf.noisyor(world)
        return prod

#class Implication(Super_Implication, ComplexFormula):
cdef class Implication(Super_Implication):
    def truth(self, world):
        ant = self.children[0].truth(world)
        cons = self.children[1].truth(world)
        if ant == 0 or cons == 1:
            return 1
        if ant is None or cons is None:
            return None
        return 0

#class Biimplication(Super_Biimplication, ComplexFormula):
cdef class Biimplication(Super_Biimplication):
    def truth(self, world):
        c1 = self.children[0].truth(world)
        c2 = self.children[1].truth(world)
        if c1 is None or c2 is None:
            return None
        return 1 if (c1 == c2) else 0

#class Negation(Super_Negation, ComplexFormula):
cdef class Negation(Super_Negation):
    pass

#class Exist(Super_Exist, ComplexFormula):
cdef class Exist(Super_Exist):
    pass

#class Equality(Super_Equality, ComplexFormula):
cdef class Equality(Super_Equality):
    pass

#class TrueFalse(Super_TrueFalse, Formula):
cdef class TrueFalse(Super_TrueFalse):
    @property
    def value(self):
        return self._value


    @value.setter
    def value(self, truth):
        if not truth == 0 and not truth == 1:
            raise Exception('Truth values in first-order logic cannot be %s' % truth)
        self._value = truth


    def __str__(self):
        return str(True if self.value == 1 else False)


    def noisyor(self, world):
        return self(world)

#class ProbabilityConstraint(object):
cdef class ProbabilityConstraint():
    """
    Base class for representing a prior/posterior probability constraint (soft evidence)
    on a logical expression.
    """

    def __init__(self, formula, p):
        self.formula = formula
        self.p = p

    def __repr__(self):
        return str(self)

cdef class PriorConstraint(ProbabilityConstraint):
    """
    Class representing a prior probability.
    """

    def __str__(self):
        return 'P(%s) = %.2f' % (fstr(self.formula), self.p)

cdef class PosteriorConstraint(ProbabilityConstraint):
    """
    Class representing a posterior probability.
    """

    def __str__(self):
        return 'P(%s|E) = %.2f' % (fstr(self.formula), self.p)
















cdef class FirstOrderLogic(Logic):
    """
    Factory class for first-order logic.
    """

    def conjunction(self, *args, **kwargs):
        return Conjunction(*args, **kwargs)

    def disjunction(self, *args, **kwargs):
        return Disjunction(*args, **kwargs)

    def negation(self, *args, **kwargs):
        return Negation(*args, **kwargs)

    def implication(self, *args, **kwargs):
        return Implication(*args, **kwargs)

    def biimplication(self, *args, **kwargs):
        return Biimplication(*args, **kwargs)

    def equality(self, *args, **kwargs):
        return Equality(*args, **kwargs)

    def exist(self, *args, **kwargs):
        return Exist(*args, **kwargs)

    def gnd_atom(self, *args, **kwargs):
        return GroundAtom(*args, **kwargs)

    def lit(self, *args, **kwargs):
        return Lit(*args, **kwargs)

    def litgroup(self, *args, **kwargs):
        return LitGroup(*args, **kwargs)

    def gnd_lit(self, *args, **kwargs):
        return GroundLit(*args, **kwargs)

    def count_constraint(self, *args, **kwargs):
        return CountConstraint(*args, **kwargs)

    def true_false(self, *args, **kwargs):
        return TrueFalse(*args, **kwargs)


# this is a little hack to make nested classes pickleable
# Constraint = FirstOrderLogic.Constraint
# Formula = FirstOrderLogic.Formula
# ComplexFormula = FirstOrderLogic.ComplexFormula
# Conjunction = FirstOrderLogic.Conjunction
# Disjunction = FirstOrderLogic.Disjunction
# Lit = FirstOrderLogic.Lit
# GroundLit = FirstOrderLogic.GroundLit
# GroundAtom = FirstOrderLogic.GroundAtom
# Equality = FirstOrderLogic.Equality
# Implication = FirstOrderLogic.Implication
# Biimplication = FirstOrderLogic.Biimplication
# Negation = FirstOrderLogic.Negation
# Exist = FirstOrderLogic.Exist
# TrueFalse = FirstOrderLogic.TrueFalse

# the following attributes no longer exist (!):
# NonLogicalConstraint = FirstOrderLogic.NonLogicalConstraint
# CountConstraint = FirstOrderLogic.CountConstraint
# GroundCountConstraint = FirstOrderLogic.GroundCountConstraint
