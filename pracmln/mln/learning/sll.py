# -*- coding: utf-8 -*-
#
# Markov Logic Networks
#
# (C) 2011-2012 by Dominik Jain (jain@cs.tum.edu) and Martin J. Schuster
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

# sampling-based log-likelihood learning

import sys

from common import *
from ll import *
from pracmln import logic


class MCMCSampler(object):
    def __init__(self, mrf, mcsatParams, discardDuplicateWorlds = False, keepTopWorldCounts = False, computeHessian = False):
        self.mrf = mrf
        self.N = len(self.mrf.mln.formulas) 
        self.wtsLast = None
        self.mcsatParams = mcsatParams
        self.keepTopWorldCounts = keepTopWorldCounts
        if keepTopWorldCounts:
            self.topWorldValue = 0.0
        self.computeHessian = computeHessian
        
        self.discardDuplicateWorlds = discardDuplicateWorlds        

    def sample(self, wtFull):
        if (self.wtsLast is None) or numpy.any(self.wtsLast != wtFull): # weights have changed => calculate new values
            self.wtsLast = wtFull.copy()
            
            # reset data
            N = self.N
            self.sampledWorlds = {}
            self.numSamples = 0
            self.Z = 0            
            self.globalFormulaCounts = numpy.zeros(N, numpy.float64)            
            self.scaledGlobalFormulaCounts = numpy.zeros(N, numpy.float64)
            #self.worldValues = []
            #self.formulaCounts = []
            self.currentWeights = wtFull
            if self.computeHessian:
                self.hessian = None
                self.hessianProd = numpy.zeros((N,N), numpy.float64)
            
            self.mrf.mln.setWeights(wtFull)
            print "calling MCSAT with weights:", wtFull
            
            #evidenceString = evidence2conjunction(self.mrf.getEvidenceDatabase())
            what = [logic.FirstOrderLogic.TrueFalse(True)]      
            mcsat = self.mrf.inferMCSAT(what, sampleCallback=self._sampleCallback, **self.mcsatParams)
            #print mcsat
            print "sampled %d worlds" % self.numSamples
        else:
            print "using cached values, no sampling (weights did not change)"
            
    def _sampleCallback(self, sample, step):
        world = sample.chains[0].state
        
        if self.discardDuplicateWorlds:
            t = tuple(world)
            if t in self.sampledWorlds:
                return
            self.sampledWorlds[t] = True
        
        #print "got sample, computing true groundings for %d ground formulas (%d formulas)" % (len(self.mrf.gndFormulas), self.N)
        formulaCounts = self.mrf.countTrueGroundingsInWorld(world)               
        exp_sum = exp(numpy.sum(formulaCounts * self.currentWeights))
        #self.formulaCounts.append(formulaCounts)
        #self.worldValues.append(exp_sum)
        self.globalFormulaCounts += formulaCounts
        self.scaledGlobalFormulaCounts += formulaCounts * exp_sum
        self.Z += exp_sum
        self.numSamples += 1
        
        if self.keepTopWorldCounts and exp_sum > self.topWorldValue:
            self.topWorldFormulaCounts = formulaCounts
        
        if self.computeHessian:
            #print "computing hessian"
            for i in xrange(self.N):
                self.hessianProd[i][i] += formulaCounts[i]**2
                for j in xrange(i+1, self.N):
                    v = formulaCounts[i] * formulaCounts[j]
                    self.hessianProd[i][j] += v
                    self.hessianProd[j][i] += v
        
        if self.numSamples % 1000 == 0:
            print "  MCSAT sample #%d" % self.numSamples
    
    def getHessian(self):
        if not self.computeHessian: raise Exception("The Hessian matrix was not computed for this learning method")
        if not self.hessian is None: return self.hessian
        self.hessian = numpy.zeros((self.N,self.N), numpy.float64)
        eCounts = self.globalFormulaCounts / self.numSamples
        for i in xrange(self.N):
            for j in xrange(self.N):
                self.hessian[i][j] = eCounts[i] * eCounts[j]
        self.hessian -= self.hessianProd / self.numSamples
        return self.hessian

    def getCovariance(self):
        return -self.getHessian()


class SLL(AbstractLearner):
    '''
        sample-based log-likelihood
    '''
     
    def __init__(self, mrf, **params):
        AbstractLearner.__init__(self, mrf, **params)
        if len(filter(lambda b: isinstance(b, SoftMutexBlock), self.mrf.gndAtomicBlocks)) > 0:
            raise Exception('%s cannot handle soft-functional constraints' % self.__class__.__name__)
        self.mcsatSteps = self.params.get("mcsatSteps", 2000)        
        self.samplerParams = dict(given="", softEvidence={}, maxSteps=self.mcsatSteps, 
                                  doProbabilityFitting=False,
                                  verbose=False, details=False, infoInterval=100, resultsInterval=100)
        self.samplerConstructionParams = dict(discardDuplicateWorlds=False, keepTopWorldCounts=False)
         
    def _sample(self, wt, caller):
        self.normSampler.sample(wt)
         
    def _f(self, wt, **params):
        # although this function corresponds to the gradient, it cannot soundly be applied to
        # the problem, because the set of samples is drawn only from the set of worlds that
        # have probability mass only
        # i.e. it would optimize the world's probability relative to the worlds that have
        # non-zero probability rather than all worlds, which is problematic in the presence of
        # hard constraints that need to be learned as being hard
         
        self._sample(wt, "f")        
        ll = numpy.sum(self.formulaCountsTrainingDB * wt) - numpy.sum(self.normSampler.globalFormulaCounts * wt) / self.normSampler.numSamples
         
        return ll
     
    def _grad(self, wt, **params):
        self._sample(wt, "grad")
        grad = self.formulaCountsTrainingDB - self.normSampler.globalFormulaCounts / self.normSampler.numSamples
        return grad
     
    def _initSampler(self):
        self.normSampler = MCMCSampler(self.mrf,
                                       self.samplerParams,
                                       **self.samplerConstructionParams)
     
    def _prepareOpt(self):
        # compute counts
        print "computing counts for training database..."
        self.formulaCountsTrainingDB = self.mrf.countTrueGroundingsInWorld(self.mrf.evidence)
         
        # initialise sampler
        self._initSampler()        
         
        # collect some uniform sample data for shrinkage correction
        #self.numUniformSamples = 5000
        #self.totalFormulaCountsUni = numpy.zeros(len(self.mrf.formulas))        
        #for i in xrange(self.numUniformSamples):
        #    world = self.mrf.getRandomWorld()
        #    self.totalFormulaCountsUni += self.mrf.countTrueGroundingsInWorld(world)
 
 
class SLL_DN(SLL):
    '''
        sample-based log-likelihood via diagonal Newton
    '''
     
    def __init__(self, mrf, **params):
        SLL.__init__(self, mrf, **params)
        self.samplerConstructionParams["computeHessian"] = True
     
    def _f(self, wt, **params):
        raise Exception("Objective function not implemented; use e.g. diagonal Newton to optimize")
     
    def _hessian(self, wt):
        self._sample(wt, "hessian")
        return self.normSampler.getHessian()
     
    def getAssociatedOptimizerName(self):
        return "diagonalNewton"
         
 
from softeval import truthDegreeGivenSoftEvidence
 
 
# class SLL_ISE(LL_ISE):
#     '''
#         Uses soft features to compute counts for a fictitious soft world (assuming independent soft evidence)
#         Uses MCMC sampling to approximate the normalisation constant
#     '''    
#      
#     def __init__(self, mrf, **params):
#         LL_ISE.__init__(self, mrf, **params)
#      
#     def _f(self, wt, **params):
#         idxTrainDB = self.idxTrainingDB
#         self._calculateWorldValues(wt) # (calculates sum for evidence world only)
#         self.normSampler.sample(wt)
#  
#         partition_function = self.normSampler.Z / self.normSampler.numSamples
#              
#         #print self.worlds
#         print "worlds[idxTrainDB][\"sum\"] / Z", self.expsums[idxTrainDB], partition_function
#         ll = log(self.expsums[idxTrainDB]) - log(partition_function)
#         print "ll =", ll
#         print 
#         return ll
#      
#     def _grad(self, wt, **params):
#         idxTrainDB = self.idxTrainingDB
#  
#         self.normSampler.sample(wt)
#          
#         #calculate gradient
#         grad = numpy.zeros(len(self.mrf.formulas), numpy.float64)
#         for ((idxWorld, idxFormula), count) in self.counts.iteritems():
#             if idxTrainDB == idxWorld:                
#                 grad[idxFormula] += count
#         grad = grad - self.normSampler.globalFormulaCounts / self.normSampler.numSamples
#  
#         # HACK: gradient gets too large, reduce it
#         if numpy.any(numpy.abs(grad) > 1):
#             print "gradient values too large:", numpy.max(numpy.abs(grad))
#             grad = grad / (numpy.max(numpy.abs(grad)) / 1)
#             print "scaling down to:", numpy.max(numpy.abs(grad))
#          
#         return grad
#      
#     def _prepareOpt(self):
#         # create just one possible worlds (for our training database)
#         self.mrf.worlds = []
#         self.mrf.worlds.append({"values": self.mrf.evidence}) # HACK
#         self.idxTrainingDB = 0 
#         # compute counts
#         print "computing counts..."
#         self._computeCounts()
#         print "  %d counts recorded." % len(self.counts)
#      
#         # init sampler
#         self.mcsatSteps = self.params.get("mcsatSteps", 2000)
#         self.normSampler = MCMCSampler(self.mrf,
#                                        dict(given="", softEvidence={}, maxSteps=self.mcsatSteps, 
#                                             doProbabilityFitting=False,
#                                             verbose=True, details =True, infoInterval=100, resultsInterval=100),
#                                        discardDuplicateWorlds=True)
#  
#  
# class SLL_SE(SoftEvidenceLearner):
#     '''
#         NOTE: SLL_SE_DN should usually be preferred to this
#      
#         sampling-based maximum likelihood with soft evidence (SMLSE):
#         uses MC-SAT-PC to sample soft evidence worlds
#         uses MC-SAT to sample worlds in order to approximate Z
#     '''
#      
#     def __init__(self, mrf, **params):
#         SoftEvidenceLearner.__init__(self, mrf, **params)        
#          
#     def _sample(self, wt):
#         self.normSampler.sample(wt)
#         self.seSampler.sample(wt)
#      
#     def _grad(self, wt, **params):
#         self._sample()
#          
#         grad = (self.seSampler.scaledGlobalFormulaCounts / self.seSampler.Z) - (self.normSampler.scaledGlobalFormulaCounts / self.normSampler.Z)
#  
#         #HACK: gradient gets too large, reduce it
#         if numpy.any(numpy.abs(grad) > 1):
#             print "gradient values too large:", numpy.max(numpy.abs(grad))
#             grad = grad / (numpy.max(numpy.abs(grad)) / 1)
#             print "scaling down to:", numpy.max(numpy.abs(grad))        
#          
#         print "SLL_SE: _grad:", grad
#         return grad    
#     
#     def _f(self, wt, **params):        
#         self._sample()
#          
#         numerator = self.seSampler.Z / self.seSampler.numSamples
#                  
#         partition_function = self.normSampler.Z / self.normSampler.numSamples 
#          
#         ll = log(numerator) - log(partition_function)
#         print "ll =", ll
#         print 
#         return ll
#      
#     def _prepareOpt(self):
#         self.mcsatStepsEvidence = self.params.get("mcsatStepsEvidenceWorld", 1000)
#         self.mcsatSteps = self.params.get("mcsatSteps", 2000)        
#         self.normSampler = MCMCSampler(self.mrf,
#                                        dict(given="", softEvidence={}, maxSteps=self.mcsatSteps, 
#                                             doProbabilityFitting=False,
#                                             verbose=True, details =True, infoInterval=100, resultsInterval=100))
#         evidenceString = evidence2conjunction(self.mrf.getEvidenceDatabase())
#         self.seSampler = MCMCSampler(self.mrf,
#                                      dict(given=evidenceString, softEvidence=self.mrf.softEvidence, maxSteps=self.mcsatStepsEvidence, 
#                                           doProbabilityFitting=False,
#                                           verbose=True, details =True, infoInterval=1000, resultsInterval=1000,
#                                           maxSoftEvidenceDeviation=0.05))
#  
# 
# class SLL_SE_DN(SoftEvidenceLearner):
#     '''
#         sample-based log-likelihood with soft evidence via diagonal Newton
#     '''
#     
#     def __init__(self, mrf, **params):
#         print "init soft ev learner"
#         SoftEvidenceLearner.__init__(self, mrf, **params)
# 
#     def _f(self, wt, **paramss):
#         raise Exception("Objective function not implemented; use e.g. diagonal Newton to optimize")
#     
#     def _sample(self, wt):
#         self.normSampler.sample(wt)
#         self.seSampler.sample(wt)
#     
#     def _grad(self, wt, **params):
#         self._sample(wt)
#         grad = (self.seSampler.globalFormulaCounts / self.seSampler.numSamples) - (self.normSampler.globalFormulaCounts / self.normSampler.numSamples)
#         return grad
# 
#     def _hessian(self, wt):
#         self._sample(wt)
#         #return self.seSampler.getCovariance() - self.normSampler.getCovariance()
#         return self.normSampler.getHessian()
#     
#     def getAssociatedOptimizerName(self):
#         return "diagonalNewton"
#     
#     def _prepareOpt(self):
#         self.mcsatStepsEvidence = self.params.get("mcsatStepsEvidenceWorld", 2000)
#         self.mcsatSteps = self.params.get("mcsatSteps", 2000)
#         evidenceString = evidence2conjunction(self.mrf.getEvidenceDatabase())
#         self.normSampler = MCMCSampler(self.mrf,
#                                        dict(given="", softEvidence={}, maxSteps=self.mcsatSteps,
#                                             doProbabilityFitting=False,
#                                             verbose=False, details=False, infoInterval=100, resultsInterval=100),
#                                        computeHessian=True)
#         self.seSampler = MCMCSampler(self.mrf,
#                                      dict(given=evidenceString, softEvidence=self.mrf.softEvidence, maxSteps=self.mcsatStepsEvidence, 
#                                           doProbabilityFitting=False,
#                                           verbose=False, details=False, infoInterval=1000, resultsInterval=1000,
#                                           maxSoftEvidenceDeviation=0.05),
#                                      computeHessian=True)
