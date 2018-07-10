from ..mrf cimport MRF
from ..base cimport MLN

cdef class Inference:
    cdef public MRF mrf #public MRF mrf
    cdef MLN mln
    cdef dict __dict__
