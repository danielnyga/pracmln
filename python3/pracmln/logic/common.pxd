from ..mln.base cimport MLN



cdef class Constraint():
    cdef dict __dict__

cdef class Formula(Constraint):
    cdef MLN _mln
    pass

cdef class ComplexFormula(Formula):
    pass

cdef class Conjunction(ComplexFormula):
    cpdef int maxtruth(self, world)
    cpdef int mintruth(self, world)

cdef class Disjunction(ComplexFormula):
    cpdef int maxtruth(self, world)
    cpdef int mintruth(self, world)

cdef class Lit(Formula):
    cdef int _negated
    cdef str _predname

cdef class LitGroup(Formula):
    cdef int _negated
    cdef str _predname

cdef class GroundLit(Formula):
    cdef GroundAtom _gndatom
    cdef int _negated
    cpdef truth(self, list world)
    cpdef mintruth(self, list world)
    cpdef maxtruth(self, list world)
        
cdef class GroundAtom():
    cdef str _predname
    cdef MLN mln
    #cdef int _idx
    cdef dict __dict__
    cpdef truth(self, list world)
    cpdef mintruth(self, list world)
    cpdef maxtruth(self, list world)

cdef class Equality(ComplexFormula):
    cdef int _negated
    cdef str _argsA
    cdef str _argsB
    cpdef truth(self, world=*)
    cpdef int maxtruth(self, world)
    cpdef int mintruth(self, world)

cdef class Implication(ComplexFormula):
    pass

cdef class Biimplication(ComplexFormula):
    pass

cdef class Negation(ComplexFormula):
    pass

cdef class Exist(ComplexFormula):
    pass

cdef class TrueFalse(Formula):
    cdef float _value
    cpdef float truth(self, world=*)
    cpdef mintruth(self, world=*)
    cpdef maxtruth(self, world=*)

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

