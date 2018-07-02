from base cimport MLN
from cpython cimport array


cdef class MRF:
    cdef public MLN mln
    #cdef array.array _evidence
    cdef dict __dict__
