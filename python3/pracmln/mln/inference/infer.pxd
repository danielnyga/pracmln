from ..mrf cimport MRF
from ..base cimport MLN

cdef class Inference:
    cdef MRF mrf
    cdef MLN mln
    cdef dict __dict__
