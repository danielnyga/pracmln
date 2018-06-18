cdef class Constraint():
    pass
cdef class Formula(Constraint):
    pass
cdef class ComplexFormula(Formula):
    pass
cdef class Conjunction(ComplexFormula):
    pass
cdef class Disjunction(ComplexFormula):
    pass
cdef class Lit(Formula):
    pass
cdef class LitGroup(Formula):
    pass
cdef class GroundLit(Formula):
    pass
cdef class GroundAtom:
    pass
cdef class Equality(ComplexFormula):
    pass
cdef class Implication(ComplexFormula):
    pass
cdef class Biimplication(ComplexFormula):
    pass
cdef class Negation(ComplexFormula):
    pass
cdef class Exist(ComplexFormula):
    pass
cdef class TrueFalse(Formula):
    pass
cdef class NonLogicalConstraint(Constraint):
    pass
cdef class CountConstraint(NonLogicalConstraint):
    pass
cdef class GroundCountConstraint(NonLogicalConstraint):
    pass
