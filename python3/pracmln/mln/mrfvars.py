# 
#
# (C) 2011-2014 by Daniel Nyga (nyga@cs.uni-bremen.de)
# 
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
from dnutils import ifnone

from .errors import MRFValueException
from .util import Interval

class MRFVariable(object):
    """
    Represents a (mutually exclusive) block of ground atoms.
    
    This is the base class for different types of variables an MRF
    may consist of, e.g. mutually exclusive ground atoms. The purpose
    of these variables is to provide some convenience methods for 
    easy iteration over their values ("possible worlds") and to ease
    introduction of new types of variables in an MRF.
    
    The values of a variable should have a fixed order, so every value
    must have a fixed index.
    """
    
    def __init__(self, mrf, name, predicate, *gndatoms):
        """
        :param mrf:         the instance of the MRF that this variable is added to
        :param name:        the readable name of the variable
        :param predicate:   the :class:`mln.base.Predicate` instance of this variable
        :param gndatoms:    the ground atoms constituting this variable
        """
        self.mrf = mrf
        self.gndatoms = list(gndatoms)
        self.idx = len(mrf.variables)
        self.name = name
        self.predicate = predicate
    
    
    def atomvalues(self, value):
        """
        Returns a generator of (atom, value) pairs for the given variable value
        
        :param value:     a tuple of truth values
        """
        for atom, val in zip(self.gndatoms, value):
            yield atom, val
    
    
    def iteratoms(self):
        """
        Yields all ground atoms in this variable, sorted by atom index ascending
        """
        for atom in sorted(self.gndatoms, key=lambda a: a.idx):
            yield atom
    
    
    def strval(self, value):
        """
        Returns a readable string representation for the value tuple given by `value`.
        """
        return '<%s>' % ', '.join(['%s' % str(a_v[0]) if a_v[1] == 1 else ('!%s' % str(a_v[0]) if a_v[1] == 0 else '?%s?' % str(a_v[0])) for a_v in zip(self.gndatoms, value)])
    
    
    def valuecount(self, evidence=None):
        """
        Returns the number of values this variable can take.
        """
        raise Exception('%s does not implement valuecount()' % self.__class__.__name__)
    
    
    def _itervalues(self, evidence=None):
        """
        Generates all values of this variable as tuples of truth values.
        
        :param evidence: an optional dictionary mapping ground atoms to truth values.
        
        .. seealso:: values are given in the same format as in :method:`MRFVariable.itervalues()`
        """
        raise Exception('%s does not implement _itervalues()' % self.__class__.__name__)
    
    
    def valueidx(self, value):
        """
        Computes the index of the given value.
        
        .. seealso:: values are given in the same format as in :method:`MRFVariable.itervalues()`
        """
        raise Exception('%s does not implement valueidx()' % self.__class__.__name__)
    
    
    def evidence_value_index(self, evidence=None):
        """
        Returns the index of this atomic block value for the possible world given in `evidence`.
        
        .. seealso:: `MRFVariable.evidence_value()`
        """
        value = self.evidence_value(evidence)
        if any([v is None for v in value]):
            return None
        return self.valueidx(tuple(value))
    
    
    def evidence_value(self, evidence=None):
        """
        Returns the value of this variable as a tuple of truth values
        in the possible world given by `evidence`.
        
        Exp: (0, 1, 0) for a mutex variable containing 3 gnd atoms
        
        :param evidence:   the truth values wrt. the ground atom indices. Can be a 
                           complete assignment of truth values (i.e. a list) or a dict
                           mapping ground atom indices to their truth values. If evidence is `None`,
                           the evidence vector of the MRF is taken.
        """
        if evidence is None: evidence = self.mrf.evidence
        value = []
        for gndatom in self.gndatoms:
            value.append(evidence[gndatom.idx])
#         if all(map(lambda v: v is None, value)):
#             return None
#         if not all(map(lambda v: v is not None, value)) and not all(map(lambda v: v is None, value)):
#             raise Exception('Inconsistent truth assignment in evidence')
        return tuple(value)
    
    
    def value2dict(self, value):
        """
        Takes a tuple of truth values and transforms it into a dict 
        mapping the respective ground atom indices to their truth values.
        
        :param value: the value tuple to be converted.
        """
        evidence = {}
        for atom, val in zip(self.gndatoms, value):
            evidence[atom.idx] = val
        return evidence
    
    
    def setval(self, value, world):
        """
        Sets the value of this variable in the world `world` to the given value.
        
        :param value:    tuple representing the value of the variable.
        :param world:    vector representing the world to be modified:
        :returns:        the modified world.  
        """
        for i, v in self.value2dict(value).items():
            world[i] = v
        return world
    
    
    def itervalues(self, evidence=None):
        """
        Iterates over (idx, value) pairs for this variable.
        
        Values are given as tuples of truth values of the respective ground atoms. 
        For a binary variable (a 'normal' ground atom), for example, the two values 
        are represented by (0,) and (1,). If `evidence is` given, only values 
        matching the evidence values are generated.
        
        :param evidence:     an optional dictionary mapping ground atom indices to truth values.
        
                             .. warning:: ground atom indices are with respect to the mrf instance,
                                          not to the index of the gnd atom in the variable
                                           
        .. warning:: The values are not necessarily orderd with respect to their
                     actual index obtained by `MRFVariable.valueidx()`.
        
        """
        if type(evidence) is list:
            evidence = dict([(i, v) for i, v in enumerate(evidence)])
        for tup in self._itervalues(evidence):
            yield self.valueidx(tup), tup
    
    
    def values(self, evidence=None):
        """
        Returns a generator of possible values of this variable under consideration of
        the evidence given, if any.
        
        Same as ``itervalues()`` but without value indices.
        """
        for _, val in self.itervalues(evidence):
            yield val
    
    
    def iterworlds(self, evidence=None):
        """
        Iterates over possible worlds of evidence which can be generated with this variable.
        
        This does not have side effects on the `evidence`. If no `evidence` is specified,
        the evidence vector of the MRF is taken.
        
        :param evidence:     a possible world of truth values of all ground atoms in the MRF.
        :returns:            
        """
        if type(evidence) is not dict:
            raise Exception('evidence must be of type dict, is %s' % type(evidence))
        if evidence is None:
            evidence = self.mrf.evidence_dicti()
        for i, val  in self.itervalues(evidence):
            world = dict(evidence)
            value = self.value2dict(val)
            world.update(value)
            yield i, world
        
        
    def consistent(self, world, strict=False):
        """
        Checks for this variable if its assignment in the assignment `evidence` is consistent.
        
        :param evidence: the assignment to be checked.
        :param strict:   if True, no unknown assignments are allowed, i.e. there must not be any
                         ground atoms in the variable that do not have a truth value assigned.
        """
        total = 0
        evstr = ','.join([ifnone(world[atom.idx], '?', str) for atom in self.gndatoms])
        for gnatom in self.gndatoms:
            val = world[gnatom.idx]
            if strict and val is None:
                raise MRFValueException('Not all values have truth assignments: %s: %s' % (repr(self), evstr))
            total += ifnone(val, 0)
        if not (total == 1 if strict else total in Interval('[0,1]')):
            raise MRFValueException('Invalid value of variable %s: %s' % (repr(self), evstr))
        return True
        
    
    def __str__(self):
        return self.name
    
    def __repr__(self):
        return '<%s "%s": [%s]>' % (self.__class__.__name__, self.name, ','.join(map(str, self.gndatoms)))
    
    def __contains__(self, element):
        return element in self.gndatoms
    

class FuzzyVariable(MRFVariable):
    """
    Represents a fuzzy ground atom that can take values of truth in [0,1].
    
    It does not support iteration over values or value indexing.
    """
    
    def consistent(self, world, strict=False):
        value = self.evidence_value(world)[0]
        if value is not None:
            if value >= 0 and value <= 1:
                return True
            else: raise MRFValueException('Invalid value of variable %s: %s' % (repr(self), value))
        else:
            if strict: raise MRFValueException('Invalid value of variable %s: %s' % (repr(self), value))
            else: return True
    
    
    def valuecount(self, evidence=None):
        if evidence is None or evidence[self.gndatoms[0].idx] is None:
            raise MRFValueException('Cannot count number of values of an unassigned FuzzyVariable: %s' % str(self))
        else:
            return 1


    def itervalues(self, evidence=None):
        if evidence is None or evidence[self.gndatoms[0].idx] is None:
            raise MRFValueException('Cannot iterate over values of fuzzy variables: %s' % str(self))
        else:
            yield None, (evidence[self.gndatoms[0].idx],)
    

class BinaryVariable(MRFVariable):
    """
    Represents a binary ("normal") ground atom with the two truth values 1 (true) and 0 (false).
    The first value is always the false one.
    """
    

    def valuecount(self, evidence=None):
        if evidence is None:
            return 2
        else:
            return len(list(self.itervalues(evidence)))


    def _itervalues(self, evidence=None):
        if evidence is None:
            evidence = {}
        if len(self.gndatoms) != 1: raise Exception('Illegal number of ground atoms in the variable %s' % repr(self))
        gndatom = self.gndatoms[0]
        if evidence.get(gndatom.idx) is not None and evidence.get(gndatom.idx) in (0,1):
            yield (evidence[gndatom.idx],)
            return
        for t in (0, 1):
            yield (t,)


    def valueidx(self, value):
        if value == (0,): return 0
        elif value == (1,): return 1
        else:
            raise MRFValueException('Invalid world value for binary variable %s: %s' % (str(self), str(value)))
        

    def consistent(self, world, strict=False):
        val = world[self.gndatoms[0].idx]
        if strict and val is None:
            raise MRFValueException('Invalid value of variable %s: %s' % (repr(self), val))
        

class MutexVariable(MRFVariable):
    """
    Represents a mutually exclusive block of ground atoms, i.e. a block
    in which exactly one ground atom must be true.
    """
    
    def valuecount(self, evidence=None):
        if evidence is None:
            return len(self.gndatoms)
        else:
            return len(list(self.itervalues(evidence)))
    
    
    def _itervalues(self, evidence=None):
        if evidence is None:
            evidence = {}
        atomindices = [a.idx for a in self.gndatoms]
        valpattern = []
        for mutexatom in atomindices:
            valpattern.append(evidence.get(mutexatom, None))
        # at this point, we have generated a value pattern with all values 
        # that are fixed by the evidence argument and None for all others
        trues = sum([x for x in valpattern if x == 1])
        if trues > 1: # sanity check
            raise MRFValueException("More than one ground atom in mutex variable is true: %s" % str(self))
        if trues == 1: # if the true value of the mutex var is in the evidence, we have only one possibility
            yield tuple([1 if x == 1 else 0 for x in valpattern])
            return
        if all([x == 0 for x in valpattern]):
            raise MRFValueException('Illegal value for a MutexVariable %s: %s' % (self, valpattern))
        for i, val in enumerate(valpattern): # generate a value tuple with a truth value for each atom which is not set to false by evidence
            if val == 0: continue
            elif val is None:
                values = [0] * len(valpattern)
                values[i] = 1
                yield tuple(values)
                
    
    def valueidx(self, value):
        if sum(value) != 1:
            raise MRFValueException('Invalid world value for mutex variable %s: %s' % (str(self), str(value)))
        else:
            return value.index(1)
        

class SoftMutexVariable(MRFVariable):
    """
    Represents a soft mutex block of ground atoms, i.e. a mutex block in which maximally
    one ground atom may be true.
    """
    
    def valuecount(self, evidence=None):
        if evidence is None:
            return len(self.gndatoms) + 1
        else:
            return len(list(self.itervalues(evidence)))


    def _itervalues(self, evidence=None):
        if evidence is None:
            evidence = {}
        atomindices = [a.idx for a in self.gndatoms]
        valpattern = []
        for mutexatom in atomindices:
            valpattern.append(evidence.get(mutexatom, None))
        # at this point, we have generated a value pattern with all values 
        # that are fixed by the evidence argument and None for all others
        trues = sum([x for x in valpattern if x == 1])
        if trues > 1: # sanity check
            raise Exception("More than one ground atom in mutex variable is true: %s" % str(self))
        if trues == 1: # if the true value of the mutex var is in the evidence, we have only one possibility
            yield tuple([1 if x == 1 else 0 for x in valpattern])
            return
        for i, val in enumerate(valpattern): # generate a value tuple with a true value for each atom which is not set to false by evidence
            if val == 0: continue
            elif val is None:
                values = [0] * len(valpattern)
                values[i] = 1
                yield tuple(values)
        yield tuple([0] * len(atomindices))
        
    
    def valueidx(self, value):
        if sum(value) > 1:
            raise Exception('Invalid world value for soft mutex block %s: %s' % (str(self), str(value)))
        elif sum(value) == 1:
            return value.index(1) + 1
        else: return 0
