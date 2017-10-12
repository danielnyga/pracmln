# -*- coding: utf-8 -*-
#
# Markov Logic Networks
#
# (C) 2006-2011 by Dominik Jain (jain@cs.tum.edu)
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

from pracmln.mln.learning.common import SoftEvidenceLearner, DiscriminativeLearner
from pracmln.mln.learning.common import AbstractLearner
import numpy
from numpy.ma.core import exp
from pracmln.mln.util import fsum
from pracmln.mln.mrfvars import SoftMutexVariable


# TODO Note: when counting diffs (PLL), the assumption is made that no formula contains two atoms that are in the same block

class PLL(AbstractLearner):
    
    def __init__(self, mln, mrf, pmbMethod="old", diffMethod="blocking", **params):
        '''
        pmbMethod: 'excl' or 'old'
            concerns the calculation of the probability of a ground atom assignment given the ground atom's Markov blanket
            If set to 'old', consider only the two assignments of the ground atom x (i.e. add the weights of any ground
            formulas within which x appears for both cases and then use the appriopriate fraction).
            If set to 'excl', consider mutual exclusiveness and exhaustiveness by looking at all the assignments of the
            block that x is in (and all the formulas that are affected by any of the atoms in the block). We obtain an exp. sum of
            weights for each block assignment and consider the fraction of those block assignments where x has a given value.
        
        diffMethod: "blocking" or "simple"
            This applies to parameter learning with pseudo-likelihood, where, for each ground atom x, the difference in the number
            of true groundings of a formula is computed for the case where x's truth value is flipped and where x's truth value
            remains the same (as indicated by the training db).
            If set to 'blocking', then we not only consider the effects of flipping x itself but also flips of any
            ground atoms with which x appears together in a block, because flipping them may (or may not) affect the truth
            value of x and thus the truth of ground formulas within which x appears.        
        '''
        AbstractLearner.__init__(self, mln, mrf, **params)
        self.pmbMethod = pmbMethod
        self.diffMethod = diffMethod
        if len(filter(lambda b: isinstance(b, SoftMutexVariable), self.mrf.variables)) > 0:
            raise Exception('%s cannot handle soft-functional constraints' % self.__class__.__name__)
    
    def getAtomProbMB(self, atom):
        '''
        determines the probability of the given ground atom (string) given its Markov blanket
        (the MLN must have been provided with evidence using combineDB)
        '''
        idxGndAtom = self.mrf.gndAtoms[atom].idx
        weights = self._weights()
        return self._getAtomProbMB(idxGndAtom, weights)

    def _getAtomProbMB(self, idxGndAtom, wt, relevantGroundFormulas=None):
        '''            
        gets the probability of the ground atom with index idxGndAtom when given its Markov blanket (evidence set)
        using the specified weight vector
        '''
        #old_tv = self._getEvidence(idxGndAtom)
        # check if the ground atom is in a block
        block = None
        if idxGndAtom in self.mrf.gndBlockLookup and self.pmbMethod != 'old':
            blockname = self.mrf.gndBlockLookup[idxGndAtom]
            block = self.mrf.gndBlocks[blockname]   # list of gnd atom indices that are in the block
            sums = [0 for i in range(len(block))]   # init sum of weights for each possible assignment of block
                                                    # sums[i] = sum of weights for assignment where the block[i] is set to true
            idxBlockMainGA = block.index(idxGndAtom)
            # find out which one of the ground atoms in the block is true
            idxGATrueone = -1
            for i in block:
                if self.mrf._getEvidence(i):
                    if idxGATrueone != -1: raise Exception("More than one true ground atom in block %s!" % blockname)
                    idxGATrueone = i                    
            if idxGATrueone == -1: raise Exception("No true gnd atom in block!" % blockname)
            mainAtomIsTrueone = idxGATrueone == idxGndAtom
        else: # not in block
            wts_inverted = 0
            wts_regular = 0
            wr, wi = [], []
        # determine the set of ground formulas to consider
        checkRelevance = False
        if relevantGroundFormulas == None:
            try:
                relevantGroundFormulas = self.atomRelevantGFs[idxGndAtom]
            except:
                relevantGroundFormulas = self.mrf.gndFormulas
                checkRelevance = True
        # check the ground formulas
        #print self.gndAtomsByIdx[idxGndAtom]
        if self.pmbMethod == 'old' or block == None: # old method (only consider formulas that contain the ground atom)
            for gf in relevantGroundFormulas:
                if checkRelevance:
                    if not gf.containsGndAtom(idxGndAtom):
                        continue
                # gnd atom maintains regular truth value
                prob1 = self._getTruthDegreeGivenEvidence(gf)
                #print "gf: ", str(gf), " index: ", gf.idxFormula, ", wt size:", len(wt), " formula size:", len(self.formulas)
                if prob1 > 0:
                    wts_regular += wt[gf.idxFormula] * prob1
                    wr.append(wt[gf.idxFormula] * prob1)
                # flipped truth value
                #self._setTemporaryEvidence(idxGndAtom, not old_tv)
                self._setInvertedEvidence(idxGndAtom)
                #if self._isTrueGndFormulaGivenEvidence(gf):
                #    wts_inverted += wt[gf.idxFormula]
                #    wi.append(wt[gf.idxFormula])
                prob2 = self._getTruthDegreeGivenEvidence(gf)
                if prob2 > 0:
                    wts_inverted += wt[gf.idxFormula] * prob2
                    wi.append(wt[gf.idxFormula] * prob2)
                #self._removeTemporaryEvidence()
                #print "  F%d %f %s %f -> %f" % (gf.idxFormula, wt[gf.idxFormula], str(gf), prob1, prob2)
                self._setInvertedEvidence(idxGndAtom)
            #print "  %s %s" % (wts_regular, wts_inverted)
            return exp(wts_regular) / (exp(wts_regular) + exp(wts_inverted))
        elif self.pmbMethod == 'excl' or self.pmbMethod == 'excl2': # new method (consider all the formulas that contain one of the ground atoms in the same block as the ground atom)
            for gf in relevantGroundFormulas: # !!! here the relevant ground formulas may not be sufficient!!!! they are different than in the other case
                # check if one of the ground atoms in the block appears in the ground formula
                if checkRelevance:
                    gfRelevant = False
                    for i in block:
                        if gf.containsGndAtom(i):
                            gfRelevant = True
                            break
                    if not gfRelevant: continue
                # make each one of the ground atoms in the block true once
                idxSum = 0
                for i in block:
                    # set the i-th variable in the block to true
                    if i != idxGATrueone:
                        self.mrf._setTemporaryEvidence(i, True)
                        self.mrf._setTemporaryEvidence(idxGATrueone, False)
                    # is the formula true?
                    if self.mrf._isTrueGndFormulaGivenEvidence(gf):
                        sums[idxSum] += wt[gf.idxFormula]
                    # restore truth values
                    self.mrf._removeTemporaryEvidence()
                    idxSum += 1
            expsums = map(exp, sums)
            if self.pmbMethod == 'excl':
                if mainAtomIsTrueone:
                    return expsums[idxBlockMainGA] / sum(expsums)
                else:
                    s = sum(expsums)
                    return (s - expsums[idxBlockMainGA]) / s
            elif self.pmbMethod == 'excl2':
                if mainAtomIsTrueone:
                    return expsums[idxBlockMainGA] / sum(expsums)
                else:
                    idxBlockTrueone = block.index(idxGATrueone)
                    return expsums[idxBlockTrueone] / (expsums[idxBlockTrueone] + expsums[idxBlockMainGA])
        else:
            raise Exception("Unknown pmbMethod '%s'" % self.pmbMethod)
    
    def _setInvertedEvidence(self, idxGndAtom):
        old_tv = self.mrf._getEvidence(idxGndAtom)
        self.mrf._setEvidence(idxGndAtom, 1 - old_tv)

    # prints the probability of each ground atom truth assignment given its Markov blanket
    def printAtomProbsMB(self):
        gndAtoms = self.mrf.gndAtoms.keys()
        gndAtoms.sort()
        values = []
        for gndAtom in gndAtoms:
            v = self.getAtomProbMB(gndAtom)
            print "%s=%s  %f" % (gndAtom, str(self.mrf._getEvidence(self.mrf.gndAtoms[gndAtom].idx)), v)
            values.append(v)
        pll = fsum(map(log, values))
        print "PLL = %f" % pll

    def _calculateAtomProbsMB(self, wt):
        if ('wtsLastAtomProbMBComputation' not in dir(self)) or self.wtsLastAtomProbMBComputation != list(wt):
            print "recomputing atom probabilities...",
            self.atomProbsMB = [self._getAtomProbMB(i, wt) for i in range(len(self.mrf.gndAtomsByIdx))]
            self.atomProbsMB = map(lambda x: x if x > 0 else 1e-10, self.atomProbsMB)
            self.wtsLastAtomProbMBComputation = list(wt)
            print "done."

    def _f(self, wt, **params):
        self._calculateAtomProbsMB(wt)
        #print self.atomProbsMB
        probs = map(lambda x: x if x > 0 else 1e-10, self.atomProbsMB) # prevent 0 probs
        pll = fsum(map(log, probs))
        print "pseudo-log-likelihood:", pll
        return pll

    def _addToDiff(self, idxFormula, idxGndAtom, diff):
        key = (idxFormula, idxGndAtom)
        cur = self.diffs.get(key, 0)
        self.diffs[key] = cur + diff        

    def _computeDiffs(self):
        self.diffs = {}
        for gndFormula in self.mrf.gndFormulas:
            for idxGndAtom in gndFormula.idxGroundAtoms():
                cnt1, cnt2 = 0, 0
                # check if formula is true if gnd atom maintains its truth value
                cnt1 = self.mrf._isTrueGndFormulaGivenEvidence(gndFormula)
                # check if formula is true if gnd atom's truth value is inversed
                old_tv = self.mrf._getEvidence(idxGndAtom)
                self.mrf._setTemporaryEvidence(idxGndAtom, 1 - old_tv)
                cnt2 = self.mrf._isTrueGndFormulaGivenEvidence(gndFormula)
                self.mrf._removeTemporaryEvidence()
                # save difference
                diff = cnt2 - cnt1
                if diff != 0:
                    self._addToDiff(gndFormula.idxFormula, idxGndAtom, diff) 
                    # if the gnd atom is in a block with other variables, then these other variables can also
                    # cause a change in the number of true groundings of this formula:
                    # let's say there are k gnd atoms in the block and one of the k items appears in gndFormula, say item x.
                    # if gnd atom x is true, then a change to any of the other k-1 items will flip x.
                    # if gnd atom x is false, then there is a chance of 1/(k-1) that x is flipped
                    if self.diffMethod == 'blocking':
                        if idxGndAtom in self.mrf.gndBlockLookup:
                            blockname = self.mrf.gndBlockLookup[idxGndAtom]
                            block = self.mrf.gndBlocks[blockname] # list of gnd atom indices that are in the block
                            for i in block:
                                if i not in gndFormula.idxGroundAtoms(): # for each ground atom in the block besides the one we are just processing (which occurs in the ground formula)
                                    if old_tv:
                                        self._addToDiff(gndFormula.idxFormula, i, diff)
                                    else:
                                        self._addToDiff(gndFormula.idxFormula, i, diff / (len(block) - 1))
                                        

    def _grad(self, wt, **params):        
        grad = numpy.zeros(len(self.mln.formulas), numpy.float64)
        fullWt = wt
        self._calculateAtomProbsMB(fullWt)
        for (idxFormula, idxGndAtom), diff in self.diffs.iteritems():
            v = diff * (self.atomProbsMB[idxGndAtom] - 1)
            grad[idxFormula] += v            
        return grad

    def _getAtomRelevantGroundFormulas(self):
        if self.pmbMethod == 'old':
            self.atomRelevantGFs = self.mrf.gndAtomOccurrencesInGFs
        else:
            raise Exception("Not implemented")

    def _prepareOpt(self):
        print "computing differences..."
        self._computeDiffs()
        print "  %d differences recorded" % len(self.diffs)
        print "determining relevant formulas for each ground atom..."
        self._getAtomRelevantGroundFormulas()
        
        
        
class PLL_ISE(SoftEvidenceLearner, PLL):
    
    def __init__(self, mln, **params):
        SoftEvidenceLearner.__init__(self, mln, **params)
        PLL.__init__(self, mln, **params)        
    
    def _computeDiffs(self):
        self.diffs = {}
        for gndFormula in self.mrf.gndFormulas:
            cnt1 = self._getTruthDegreeGivenEvidence(gndFormula)
            for idxGndAtom in gndFormula.idxGroundAtoms():
                # check if formula is true if gnd atom's truth value is inversed
                cnt2 = 0
                # check if it really is a soft evidence:
                s = strFormula(self.mrf.gndAtomsByIdx[idxGndAtom])
                isSoftEvidence = False                 
                for se in self.mrf.softEvidence:
                    if se["expr"] == s:
                        isSoftEvidence = True
                        old_tv = se["p"]
                        break
                    
                if isSoftEvidence:
                    self.mrf._setSoftEvidence(self.mln.gndAtomsByIdx[idxGndAtom], 1 - old_tv)
                    cnt2 = self._getTruthDegreeGivenEvidence(gndFormula)
                    self.mrf._setSoftEvidence(self.mln.gndAtomsByIdx[idxGndAtom], old_tv)
                else:
                    old_tv = self.mrf._getEvidence(idxGndAtom)
                    self.mrf._setTemporaryEvidence(idxGndAtom, not old_tv)
                    if self.mrf._isTrueGndFormulaGivenEvidence(gndFormula): cnt2 = 1
                    self.mrf._removeTemporaryEvidence()
                    
                # save difference
                diff = cnt2 - cnt1
                if diff != 0:
                    self._addToDiff(gndFormula.idxFormula, idxGndAtom, diff)
                    
    def _setInvertedEvidence(self, idxGndAtom):
        s = strFormula(self.mrf.gndAtomsByIdx[idxGndAtom])
        isSoftEvidence = False
        for se in self.mrf.softEvidence:
            if se["expr"] == s:
                isSoftEvidence = True
                old_tv = se["p"]
                break
        if isSoftEvidence:
            self.mrf._setSoftEvidence(self.mrf.gndAtomsByIdx[idxGndAtom], 1 - old_tv)
        else:
            old_tv = self.mrf._getEvidence(idxGndAtom)
            self.mrf._setEvidence(idxGndAtom, not old_tv)
            
    def _prepareOpt(self):
        if self.pmbMethod != 'old': raise Exception("Only PMB (probability given Markov blanket) method 'old' supported by PLL_ISE")
        
        # set all soft evidence values to true
        #for se in self.softEvidence:
        #    self._setEvidence(self.mln.gndAtoms[se["expr"]].idx, True)
        
        PLL._prepareOpt(self)
        
    def _f(self, wt, **params):
        
        pll = PLL._f(self, wt)
            
        if self.gaussianPriorSigma != None:
            #add gaussian means:
            for weight in wt:
                pll += gaussianZeroMean(weight, self.gaussianPriorSigma)
        
        print "pseudo-log-likelihood:", pll
        return pll
        
    def _grad(self, wt, **params):        
        grad = PLL._grad(self, wt)
                
        if self.gaussianPriorSigma != None:
            #add gaussian means:
            for i, weight in enumerate(wt):
                grad[i] += gradGaussianZeroMean(weight, self.gaussianPriorSigma)
                
        return grad




class DPLL_ISE(PLL_ISE):
    ''' discriminative PLL_ISE with independent soft evidence for atLocation '''
    
    def __init__(self, mln, **params):
        DPLL.__init__(mln, **params)
        PLL_ISE.__init__(mln, **params)        
        # manually inherit methods from DPLL
        self._f = DPLL._f
        self._grad = DPLL._grad
        self._isQueryPredicate = DPLL._isQueryPredicate
        