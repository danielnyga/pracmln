from ..mrf cimport MRF

cdef class DefaultGroundingFactory():
    cdef public MRF mrf
    cdef public list _cache
    cdef int _cachesize
    cdef int total_gf
    cdef bint __cacheinit
    cdef bint __cachecomplete
    cdef dict _params
    cdef dict __dict__
    #cdef itergroundings(self)
