from base cimport MLN
from cpython cimport array


cdef class MRF:
    cdef public MLN mln
    cdef list _evidence#cdef array.array _evidence
    cdef dict _variables
    cdef dict _gndatoms
    cdef dict _gndatoms_indices
    cdef dict __dict__
