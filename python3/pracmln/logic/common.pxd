from ..mln.base cimport MLN



cdef class Constraint():
    cdef dict __dict__

cdef class Formula(Constraint):
    cdef MLN _mln
    pass

cdef class ComplexFormula(Formula):
    pass

cdef class Conjunction(ComplexFormula):
    pass

cdef class Disjunction(ComplexFormula):
    pass

cdef class Lit(Formula):
    cdef int _negated
    cdef str _predname

cdef class LitGroup(Formula):
    cdef int _negated
    cdef str _predname

cdef class GroundLit(Formula):
    cdef GroundAtom _gndatom
    cdef int _negated

cdef class GroundAtom:
    cdef str _predname
    cdef MLN mln
    cdef dict __dict__

cdef class Equality(ComplexFormula):
    cdef int _negated

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

cdef class Logic:
    pass
    #cdef class Constraint():
    #    pass

