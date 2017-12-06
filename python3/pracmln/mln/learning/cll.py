# COMPOSITE LIKELIHOOD LEARNING
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
from dnutils import logs

from .common import AbstractLearner, DiscriminativeLearner
import random
from collections import defaultdict
from ..util import fsum, dict_union, temporary_evidence
from numpy.ma.core import log, sqrt
import numpy
from ...logic.common import Logic
from ..constants import HARD
from ..errors import SatisfiabilityException


logger = logs.getlogger(__name__)


class CLL(AbstractLearner):
    """
    Implementation of composite-log-likelihood learning.
    """
    
    def __init__(self, mrf, **params):
        AbstractLearner.__init__(self, mrf, **params)
        self.partitions = []
        self.repart = 0


    @property
    def partsize(self):
        return self._params.get('partsize', 1)


    @property
    def maxiter(self):
        return self._params.get('maxiter', 10)
    
                
    @property
    def variables(self):
        return self.mrf.variables
    
    
    def _prepare(self):
        # create random partition of the ground atoms
        self.partitions = []
        self.atomidx2partition = {}
        self.partition2formulas = defaultdict(set)
        self.evidx = {}
        self.valuecounts = {}
        self.partitionProbValues = {}
        self.current_wts = None
        self.iter = 0
        self.probs = {}
        self._stat = {}
        size = self.partsize
        variables = list(self.variables)
        if size > 1:
            random.shuffle(variables)
        while len(variables) > 0:
            vars_ = variables[:size if len(variables) > size else len(variables)]
            partidx = len(self.partitions)
            partition = CLL.Partition(self.mrf, vars_, partidx)
            # create the mapping from atoms to their partitions
            for atom in partition.gndatoms:
                self.atomidx2partition[atom.idx] = partition
            logger.debug('created partition: %s' % str(partition))
            self.valuecounts[partidx] = partition.valuecount()
            self.partitions.append(partition)
            self.evidx[partidx] = partition.evidenceidx()
            variables = variables[len(partition.variables):]
        logger.debug('CLL created %d partitions' % len(self.partitions))
        self._compute_statistics()

        
    def repeat(self):
        return True
        
        
    def _addstat(self, fidx, pidx, validx, inc=1):
        if fidx not in self._stat:
            self._stat[fidx] = {}
        d = self._stat[fidx]
        if pidx not in d:
            d[pidx] = [0] * self.valuecounts[pidx]
        try:
            d[pidx][validx] += inc
        except Exception as e:
            raise e


    def _compute_statistics(self):
        self._stat = {}
        self.partition2formulas = defaultdict(set)
        for formula in self.mrf.formulas:
            literals = []
            for lit in formula.literals():
                literals.append(lit)
            # in case of a conjunction, rearrange the literals such that 
            # equality constraints are evaluated first
            isconj = self.mrf.mln.logic.islitconj(formula)
            if isconj:
                literals = sorted(literals, key=lambda l: -1 if isinstance(l, Logic.Equality) else 1)
            self._compute_stat_rec(literals, [], {}, formula, isconj=isconj)
    
    
    def _compute_stat_rec(self, literals, gndliterals, var_assign, formula, f_gndlit_parts=None, processed=None, isconj=False):
        """
        TODO: make sure that there are no equality constraints in the conjunction!
        """

        if len(literals) == 0:
            # at this point, we have a fully grounded conjunction in gndliterals
            # create a mapping from a partition to the ground literals in this formula
            # (criterion no. 1, applies to all kinds of formulas)
            part2gndlits = defaultdict(list)
            part_with_f_lit = None
            for gndlit in gndliterals:
                if isinstance(gndlit, Logic.Equality) or hasattr(self, 'qpreds') and gndlit.gndatom.predname not in self.qpreds: continue
                part = self.atomidx2partition[gndlit.gndatom.idx]
                part2gndlits[part].append(gndlit)
                if gndlit(self.mrf.evidence) == 0:
                    part_with_f_lit = part

            # if there is a false ground literal we only need to take into account
            # the partition comprising this literal (criterion no. 2)
            # there is maximally one such partition with false literals in the conjunction
            # because of criterion no. 5
            if isconj and part_with_f_lit is not None:
                gndlits = part2gndlits[part_with_f_lit]
                part2gndlits = {part_with_f_lit: gndlits}
            if not isconj: # if we don't have a conjunction, ground the formula with the given variable assignment
                # print 'formula', formula
                gndformula = formula.ground(self.mrf, var_assign)
                # print 'gndformula', gndformula
                # stop()
            for partition, gndlits in part2gndlits.items():
                # for each partition, select the ground atom truth assignments
                # in such a way that the conjunction is rendered true. There
                # is precisely one such assignment for each partition. (criterion 3/4)
                evidence = {}
                if isconj:
                    for gndlit in gndlits:
                        evidence[gndlit.gndatom.idx] = 0 if gndlit.negated else 1
                for world in partition.itervalues(evidence):
                    # update the sufficient statistics for the given formula, partition and world value
                    worldidx = partition.valueidx(world)
                    if isconj:
                        truth = 1
                    else:
                        # temporarily set the evidence in the MRF, compute the truth value of the 
                        # formula and remove the temp evidence
                        with temporary_evidence(self.mrf):
                            for atomidx, value in partition.value2dict(world).items():
                                self.mrf.set_evidence({atomidx: value}, erase=True)
                            truth = gndformula(self.mrf.evidence)
                            if truth is None:
                                print(gndformula)
                                print(gndformula.print_structure(self.mrf.evidence))

                    if truth != 0:
                        self.partition2formulas[partition.idx].add(formula.idx)
                        self._addstat(formula.idx, partition.idx, worldidx, truth)
            return
            
        lit = literals[0]
        # ground the literal with the existing assignments
        gndlit = lit.ground(self.mrf, var_assign, partial=True)
        for assign in Logic.iter_eq_varassignments(gndlit, formula, self.mrf) if isinstance(gndlit, Logic.Equality) else gndlit.itervargroundings(self.mrf):
            # copy the arguments to avoid side effects
            # if f_gndlit_parts is None: f_gndlit_parts = set()
            # else: f_gndlit_parts = set(f_gndlit_parts)
            if processed is None: processed = []
            else: processed = list(processed)
            # ground with the remaining free variables
            gndlit_ = gndlit.ground(self.mrf, assign)
            truth = gndlit_(self.mrf.evidence)
            # treatment of equality constraints
            if isinstance(gndlit_, Logic.Equality):
                if isconj:
                    if truth == 1:
                        self._compute_stat_rec(literals[1:], gndliterals, dict_union(var_assign, assign), formula, f_gndlit_parts, processed, isconj)
                    else: continue
                else:
                    self._compute_stat_rec(literals[1:], gndliterals + [gndlit_], dict_union(var_assign, assign), formula, f_gndlit_parts, processed, isconj) 
                continue
            atom = gndlit_.gndatom

            if atom.idx in processed: continue
            
            # if we encounter a gnd literal that is false by the evidence
            # and there is already a false one in this grounding from a different
            # partition, we can stop the grounding process here. The gnd conjunction
            # will never ever be rendered true by any of this partitions values (criterion no. 5)
            isevidence = hasattr(self, 'qpreds') and gndlit_.gndatom.predname not in self.qpreds
            #assert isEvidence == False
            if isconj and truth == 0:
                if f_gndlit_parts is not None and atom not in f_gndlit_parts:
                    continue
                elif isevidence: continue
                else:
                    self._compute_stat_rec(literals[1:], gndliterals + [gndlit_], dict_union(var_assign, assign), formula, self.atomidx2partition[atom.idx], processed, isconj) 
                    continue
            elif isconj and isevidence:
                self._compute_stat_rec(literals[1:], gndliterals, dict_union(var_assign, assign), formula, f_gndlit_parts, processed, isconj) 
                continue
                 
            self._compute_stat_rec(literals[1:], gndliterals + [gndlit_], dict_union(var_assign, assign), formula, f_gndlit_parts, processed, isconj) 
    

    def _compute_probs(self, w):
        probs = {}#numpy.zeros(len(self.partitions))
        for pidx in range(len(self.partitions)):
            expsums = [0] * self.valuecounts[pidx]
            for fidx in self.partition2formulas[pidx]:
                for i, v in enumerate(self._stat[fidx][pidx]):
                    if w[fidx] == HARD:
                        if v == 0: expsums[i] = None
                    elif expsums[i] is not None:
#                         out('adding', v, '*', w[fidx], 'to', i)
                        expsums[i] += v * w[fidx]
#                         stop(expsums)
#             sum_max = numpy.max(sums)
#             sums -= sum_max
#             expsums = numpy.sum(numpy.exp(sums))
#             s = numpy.log(expsums)
#             probs[pidx] = numpy.exp(sums - s)
#             out(w)
            expsum = numpy.array([numpy.exp(s) if s is not None else 0 for s in expsums])# leave out the inadmissible values
            z = fsum(expsum)
            if z == 0: raise SatisfiabilityException('MLN is unsatisfiable: all probability masses of partition %s are zero.' % str(self.partitions[pidx]))
            probs[pidx] = expsum / z
            self.probs[pidx] = expsum
        self.probs = probs
        return probs
        

    def _f(self, w):
        if self.current_wts is None or list(w) != self.current_wts:
            self.current_wts = list(w)
            self.probs = self._compute_probs(w)
        likelihood = numpy.zeros(len(self.partitions))
        for pidx in range(len(self.partitions)):
            p = self.probs[pidx][self.evidx[pidx]]
            if p == 0: p = 1e-10
            likelihood[pidx] += p
        self.iter += 1
        return fsum(list(map(log, likelihood)))
            
            
    def _grad(self, w, **params):    
        if self.current_wts is None or not list(w) != self.current_wts:
            self.current_wts = w
            self.probs = self._compute_probs(w)
        grad = numpy.zeros(len(w))
        for fidx, partitions in self._stat.items():
            for part, values in partitions.items():
                v = values[self.evidx[part]]
                for i, val in enumerate(values):
                    v -= self.probs[part][i] * val
                grad[fidx] += v
        self.grad_opt_norm = sqrt(float(fsum([x * x for x in grad])))
        return numpy.array(grad)
    
    
    class Partition(object):
        """
        Represents a partition of the variables in the MRF. Provides a couple
        of convencience methods.
        """
        
        def __init__(self, mrf, variables, idx):
            self.variables = variables
            self.mrf = mrf
            self.idx = idx
            
            
        @property
        def gndatoms(self):
            atoms = []
            for v in self.variables:
                atoms.extend(v.gndatoms)
            return atoms
            
            
        def __contains__(self, atom):
            """
            Returns True iff the given ground atom or ground atom index is part of
            this partition.
            """
            if isinstance(atom, Logic.GroundAtom):
                return atom in self.gndatoms
            elif type(atom) is int:
                return self.mrf.gndatom(atom) in self 
            else:
                raise Exception('Invalid type of atom: %s' % type(atom))
            
            
        def value2dict(self, value):
            """
            Takes a possible world tuple of the form ((0,),(0,),(1,0,0),(1,)) and transforms
            it into a dict mapping the respective atom indices to their truth values
            """
            evidence = {}
            for var, val in zip(self.variables, value):
                evidence.update(var.value2dict(val))
            return evidence
            
        
        def evidenceidx(self, evidence=None):
            """
            Returns the index of the possible world value of this partition that is represented
            by evidence. If evidence is None, the evidence set in the MRF is used.
            """
            if evidence is None:
                evidence = self.mrf.evidence
            evidencevalue = []
            for var in self.variables:
                evidencevalue.append(var.evidence_value(evidence))
            return self.valueidx(tuple(evidencevalue))
        
        
        def valueidx(self, value):
            """
            Computes the index of the given possible world that would be assigned
            to it by recursively generating all worlds by itervalues().
            value needs to be represented by a (nested) tuple of truth values.
            Exp: ((0,),(0,),(1,0,0),(0,)) --> 0
                 ((0,),(0,),(1,0,0),(1,)) --> 1
                 ((0,),(0,),(0,1,0),(0,)) --> 2
                 ((0,),(0,),(0,1,0),(1,)) --> 3
                 ...
            """
            idx = 0
            for i, (var, val) in enumerate(zip(self.variables, value)):
                exponential = 2 ** (len(self.variables) - i - 1)
                validx = var.valueidx(val)
                idx += validx * exponential
            return idx
                    
                
        def itervalues(self, evidence=None):
            """
            Yields possible world values of this partition in the form
            ((0,),(0,),(1,0,0),(0,)), for instance. Nested tuples represent mutex variables.
            All tuples are consistent with the evidence at hand. Evidence is
            a dict mapping a ground atom index to its (binary) truth value.
            """
            if evidence is None:
                evidence = []
            for world in self._itervalues(self.variables, [], evidence):
                yield world
        
        
        def _itervalues(self, variables, assignment, evidence):
            """
            Recursively generates all tuples of possible worlds that are consistent
            with the evidence at hand.
            """
            if not variables:
                yield tuple(assignment)
                return
            var = variables[0]
            for _, val in var.itervalues(evidence):
                for world in self._itervalues(variables[1:], assignment + [val], evidence):
                    yield world
                        
            
        def valuecount(self):
            """
            Returns the number of possible (partial) worlds of this partition
            """
            count = 1
            for v in self.variables:
                count *= v.valuecount()
            return count
        
        
        def __str__(self):
            s = []
            for v in self.variables:
                s.append(str(v))
            return '%d: [%s]' % (self.idx, ','.join(s))
    
    
class DCLL(CLL, DiscriminativeLearner):
    """
    Discriminative Composite-Likelihood Learner.
    """
    
    def __init__(self, mrf=None, **params):
        CLL.__init__(self, mrf, **params)
        
    
    @property
    def variables(self):
        return [var for var in self.mrf.variables if var.predicate.name in self.qpreds]
    
    
Partition = CLL.Partition
