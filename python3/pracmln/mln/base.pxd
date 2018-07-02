from ..logic.common cimport Logic

cdef class MLN:
    cdef public Logic logic
    cdef dict __dict__
