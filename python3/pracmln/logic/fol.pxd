from .common cimport Logic
from .common cimport Constraint as Super_Constraint
from .common cimport Formula as Super_Formula
from .common cimport ComplexFormula as Super_ComplexFormula
from .common cimport Conjunction as Super_Conjunction
from .common cimport Disjunction as Super_Disjunction
from .common cimport Lit as Super_Lit
from .common cimport LitGroup as Super_LitGroup
from .common cimport GroundLit as Super_GroundLit
from .common cimport GroundAtom as Super_GroundAtom
from .common cimport Equality as Super_Equality
from .common cimport Implication as Super_Implication
from .common cimport Biimplication as Super_Biimplication
from .common cimport Negation as Super_Negation
from .common cimport Exist as Super_Exist
from .common cimport TrueFalse as Super_TrueFalse
from .common cimport NonLogicalConstraint as Super_NonLogicalConstraint
from .common cimport CountConstraint as Super_CountConstraint
from .common cimport GroundCountConstraint as Super_GroundCountConstraint



cdef class Constraint(Super_Constraint):
    pass

cdef class Formula(Super_Formula):
    pass

cdef class ComplexFormula(Super_ComplexFormula):
    pass

cdef class Lit(Super_Lit):
    pass

cdef class LitGroup(Super_LitGroup):
    pass

cdef class GroundAtom(Super_GroundAtom):
    pass

cdef class GroundLit(Super_GroundLit):
    pass

cdef class Disjunction(Super_Disjunction):
    pass

cdef class Conjunction(Super_Conjunction):
    pass

cdef class Implication(Super_Implication):
    pass

cdef class Biimplication(Super_Biimplication):
    pass

cdef class Negation(Super_Negation):
    pass

cdef class Exist(Super_Exist):
    pass

cdef class Equality(Super_Equality):
    pass

cdef class TrueFalse(Super_TrueFalse):
    pass

cdef class ProbabilityConstraint():
    pass

cdef class PriorConstraint(ProbabilityConstraint):
    pass

cdef class PosteriorConstraint(ProbabilityConstraint):
    pass

