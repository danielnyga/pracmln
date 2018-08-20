from mrf cimport MRF
from mlnpreds cimport Predicate

cdef class MRFVariable:
    cdef MRF mrf
    cdef public list gndatoms
    cdef public int idx
    cdef public str name
    cdef public Predicate predicate # baffling multidb bpll learning error if not public...
