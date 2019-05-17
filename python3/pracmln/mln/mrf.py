# -*- coding: utf-8 -*-
#
# Ground Markov Random Fields
#
# (C) 2012-2013 by Daniel Nyga (nyga@cs.uni-bremen.de)
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

import re
import sys
import time
from math import *

from dnutils import out, logs

from .database import Database
from .errors import (MRFValueException, NoSuchDomainError, NoSuchPredicateError)
from .methods import InferenceMethods
from .constants import HARD
from .mrfvars import (MutexVariable, SoftMutexVariable, FuzzyVariable,
    BinaryVariable)
from .util import fstr, logx, mergedom, CallByRef, Interval
from ..logic import FirstOrderLogic
from ..logic.common import Logic
from ..logic.fuzzy import FuzzyLogic
from .grounding import *

logger = logs.getlogger(__name__)


class MRF(object):
    '''
    Represents a ground Markov random field.

    :member _gndatoms:             dict mapping a string representation of a ground atom to its Logic.GroundAtom object
    :member _gndatoms_indices:     dict mapping ground atom index to Logic.GroundAtom object
    :member _evidence:             vector of evidence truth values of all ground atoms
    :member _variables:            dict mapping variable names to their :class:`mln.mrfvars.MRFVariable` instance.
    
    :param mln:    the MLN tied to this MRF.
    :param db:     the database that the MRF shall be grounded with.
    '''

    def __init__(self, mln, db):
        if not mln._materialized:
            self.mln = mln.materialize(db)
        else:
            self.mln = mln
        self._evidence = []
#         self.evidenceBackup = {}
        self._variables = {}
        self._variables_by_idx = {} # gnd atom idx -> variable
        self._variables_by_gndatomidx = {} # gnd atom idx
        self._gndatoms = {}
        self._gndatoms_by_idx = {} 
        # get combined domain
        self.domains = mergedom(self.mln.domains, db.domains)
#         self.softEvidence = list(mln.posteriorProbReqs) # constraints on posterior 
                                                        # probabilities are nothing but 
                                                        # soft evidence and can be handled in exactly the same way
        # ground members
        self.formulas = list(self.mln.formulas)
        if isinstance(db, str):
            db = Database.load(self.mln, dbfile=db)
        elif isinstance(db, Database): 
            pass
        elif db is None:
            db = Database(self.mln)
        else:
            raise Exception("Not a valid database argument (type %s)" % (str(type(db))))
        self.db = db
        # materialize formula weights
        self._materialize_weights()
        return

    @property
    def probreqs(self):
        return self.mln.probreqs

    @property
    def variables(self):
        return sorted(list(self._variables.values()), key=lambda v: v.idx)
    
    @property
    def gndatoms(self):
        return list(self._gndatoms.values())
    
    @property
    def evidence(self):
        return self._evidence

    @evidence.setter
    def evidence(self, evidence):
        self._evidence = evidence
        self.consistent()
        
    @property
    def predicates(self):
        return self.mln.predicates
    
    @property
    def hardformulas(self):
        '''
        Returns a list of all hard formulas in this MRF.
        '''
        return [f for f in self.formulas if f.weight == HARD]

    def _getPredGroundings(self, predName):
        '''
        Gets the names of all ground atoms of the given predicate.
        '''
        # get the string represenation of the first grounding of the predicate
        if predName not in self.predicates:
            raise Exception('Unknown predicate "%s" (%s)' % (predName, list(map(str, self.predicates))))
        domNames = self.predicates[predName]
        params = []
        for domName in domNames:
            params.append(self.domains[domName][0])
        gndAtom = "%s(%s)" % (predName, ",".join(params))
        # get all subsequent groundings (by index) until the predicate name changes
        groundings = []
        idx = self.gndAtoms[gndAtom].idx
        while True:
            groundings.append(gndAtom)
            idx += 1
            if idx >= len(self.gndAtoms):
                break
            gndAtom = str(self.gndAtomsByIdx[idx])
            if self.mln.logic.parseAtom(gndAtom)[0] != predName:
                break
        return groundings

    def _getPredGroundingsAsIndices(self, predName):
        '''
        Get a list of all the indices of all groundings of the given predicate
        '''
        # get the index of the first grounding of the predicate and the number of groundings
        domNames = self.predicates[predName]
        params = []
        numGroundings = 1
        for domName in domNames:
            params.append(self.domains[domName][0])
            numGroundings *= len(self.domains[domName])
        gndAtom = "%s(%s)" % (predName, ",".join(params))
        if gndAtom not in self.gndAtoms: return []
        idxFirst = self.gndAtoms[gndAtom].idx
        return list(range(idxFirst, idxFirst + numGroundings))

    def domsize(self, domname):
        if not domname in self.domains:
            raise NoSuchDomainError(domname)
        return len(self.domains[domname])

    def _materialize_weights(self, verbose=False):
        '''
        materialize all formula weights.
        '''
        max_weight = 0
        for f in self.formulas:
            if f.weight is not None and f.weight != HARD:
                w = str(f.weight)
                variables = re.findall(r'\$\w+', w)
                for var in variables:
                    try:
                        w, numReplacements = re.subn(r'\%s' % var, self.mln.vars[var], w)
                    except:
                        raise Exception("Error substituting variable references in '%s'\n" % w)
                    if numReplacements == 0:
                        raise Exception("Undefined variable(s) referenced in '%s'" % w)
                w = re.sub(r'domSize\((.*?)\)', r'self.domsize("\1")', w)
                try:
                    f.weight = float(eval(w))
                except:
                    sys.stderr.write("Evaluation error while trying to compute '%s'\n" % w)
                    raise
                max_weight = max(abs(f.weight), max_weight)

    def __getitem__(self, key):
        return self.evidence[self.gndatom(key).idx]

    def __setitem__(self, key, value):
        self.set_evidence({key: value}, erase=False)    

    def prior(self, f, p):
        self._probreqs.append(FirstOrderLogic.PriorConstraint(formula=f, p=p))

    def posterior(self, f, p):
        self._probreqs.append(FirstOrderLogic.PosteriorConstraint(formula=f, p=p))

    def set_evidence(self, atomvalues, erase=False, cw=False):
        '''
        Sets the evidence of variables in this MRF.
        
        If erase is `True`, for every ground atom appearing in atomvalues, the truth values of all ground
        ground atom in the respective MRF variable are erased before the evidences
        are set. All other ground atoms stay untouched.

        :param atomvalues:     a dict mapping ground atom strings/objects/indices to their truth
                               values.
        :param erase:          specifies whether or not variables shall be erased before asserting the evidences.
                               Only affects the variables that are present in `atomvalues`.
        :param cw:             applies the closed-world assumption for all non evidence atoms.
        '''
        # check validity of evidence values
        atomvalues_ = {}
        for key, value in dict(atomvalues).items():
            # convert boolean to numeric values
            if value in (True, False):
                atomvalues[key] = {True: 1, False: 0}[value]
                value = atomvalues[key]
            gndatom = self.gndatom(key)
            if gndatom is None:
                self.print_gndatoms()
                raise MRFValueException('"%s" is not among the ground atoms.' % key)
            atomvalues_[str(gndatom)] = value
            var = self.variable(gndatom)
            if isinstance(self.mln.logic, FuzzyLogic):
                if (isinstance(var, MutexVariable) or isinstance(var, SoftMutexVariable) or isinstance(var, BinaryVariable)) and value is not None and value in Interval(']0,1['):
                    raise MRFValueException('Illegal value for the  (soft-) mutex or binary variable "%s": %s' % (str(var), value))
        atomvalues = atomvalues_
        if erase: # erase all variable assignments appearing in atomvalues
            for key, _ in atomvalues.items():
                var = self.variable(self.gndatom(key))
                # unset all atoms in this variable
                for atom in var.gndatoms:
                    self._evidence[atom.idx] = None
        
        for key, value in atomvalues.items():
            gndatom = self.gndatom(key)
            var = self.variable(gndatom)
            # create a template with admissible truth values for all
            # ground atoms in this variable 
            values = [-1] * len(var.gndatoms)
            if isinstance(var, FuzzyVariable):
                self._evidence[gndatom.idx] = value
                continue
            elif isinstance(var, BinaryVariable):
                self._evidence[gndatom.idx] = value
                continue
            for _, val in var.itervalues(evidence={gndatom.idx: value}):
                for i, (v, v_) in enumerate(zip(values, val)):
                    if v == -1: values[i] = v_
                    elif v is not None and v != v_:
                        values[i] = None
            for atom, val in zip(var.gndatoms, values):
                curval = self._evidence[atom.idx]
                if curval is not None and val is not None and curval != val:
                    raise MRFValueException('Contradictory evidence in variable %s: %s = %s vs. %s' % (var.name, str(gndatom), curval, val))
                elif curval is None and val is not None:
                    self._evidence[atom.idx] = val
        if cw: self.apply_cw()
                
    def erase(self):
        '''
        Erases all evidence in the MRF.
        '''
        self._evidence = [None] * len(self.gndatoms)
        
    def apply_cw(self, *prednames):
        '''
        Applies the closed world assumption to this MRF.
        
        Sets all evidences to 0 if they don't have truth value yet.
        
        :param prednames:     a list of predicate names the cw assumption shall be applied to.
                              If empty, it is applied to all predicates.
        '''
        for i, v in enumerate(self._evidence):
            if prednames and self.gndatom(i).predname not in prednames:
                continue
            if v is None: self._evidence[i] = 0
            
    def consistent(self, strict=False):
        '''
        Performs a consistency check on this MRF wrt. to the variable value assignments.
        
        Raises an MRFValueException if the MRF is inconsistent.
        '''
        for variable in self.variables:
            variable.consistent(self.evidence_dicti(), strict=strict)

    def gndatom(self, identifier, *args):
        '''
        Returns the the ground atom instance that is associated with the given identifier, or adds
        a new ground atom.
        
        :param identifier:    Either the string representation of the ground atom or its index (int)
        :returns:             the :class:`logic.common.Logic.GroundAtom` instance or None, if the ground
                              atom doesn't exist.
        
        :Example:
        >>> mrf = MRF(mln)
        >>> mrf.gndatom('foo', 'x', 'y') # add the ground atom 'foo(x,y)'
        >>> mrf.gndatom('foo(x,y)')      # get the ground atom
        foo(x,y)
        >>> mrf.gndatom(0)               # get the ground atom
        foo(x,y)
        '''
        if not args:
            if isinstance(identifier, str):
                atom = self._gndatoms.get(identifier)
                if atom is None:
                    try:
                        _, predname, args = self.mln.logic.parse_literal(identifier)
                    except NoSuchPredicateError: return None
                    atomstr = str(self.mln.logic.gnd_atom(predname, args, self.mln))
                    return self._gndatoms.get(atomstr)
                else:
                    return atom
            elif type(identifier) is int:
                return self._gndatoms_by_idx.get(identifier)
            elif isinstance(identifier, Logic.GroundAtom):
                return self._gndatoms.get(str(identifier))
#                 else:
#                     return self.new_gndatom(identifier.predname, *identifier.args)
            else: raise Exception('Illegal identifier type: %s' % type(identifier))
        else:
            return self.new_gndatom(identifier, *args)

    def variable(self, identifier):
        '''
        Returns the :class:`mln.mrfvars.MRFVariable` instance of the variable with the name or index `var`,
        or None, if no such variable exists.
        
        :param identifier:    (string/int/:class:`logic.common.Logic.GroundAtom`) the name or index of the variable,
                              or the instance of a ground atom that is part of the desired variable. 
        '''
        if type(identifier) is int:
            return self._variables_by_idx.get(identifier)
        elif isinstance(identifier, Logic.GroundAtom):
            return self._variables_by_gndatomidx[identifier.idx]
        elif isinstance(identifier, str):
            return self._variables.get(identifier)
    
    def new_gndatom(self, predname, *args):
        '''
        Adds a ground atom to the set (actually it's a dict) of ground atoms. 
        
        If the ground atom is already in the MRF it does nothing but returning the existing
        ground atom instance. Also updates/adds the variables of the MRF.
        
        :param predname:    the predicate name of the ground atom
        :param *args:       the list of predicate arguments `logic.common.Logic.GroundAtom` object
        '''
        # create and add the ground atom
        gndatom = self.mln.logic.gnd_atom(predname, args, self.mln)
        if str(gndatom) in self._gndatoms:
            return self._gndatoms[str(gndatom)]
        self._evidence.append(None)
        gndatom.idx = len(self._gndatoms)
        self._gndatoms[str(gndatom)] = gndatom
        self._gndatoms_by_idx[gndatom.idx] = gndatom
        # add the ground atom to the variable it belongs
        # to or create a new one if it doesn't exists.
        predicate = self.mln.predicate(gndatom.predname)
        varname = predicate.varname(gndatom)
        variable = self.variable(varname)
        if variable is None:
            variable = predicate.tovariable(self, varname)
            self._variables[variable.name] = variable
            self._variables_by_idx[variable.idx] = variable
        variable.gndatoms.append(gndatom)
        self._variables_by_gndatomidx[gndatom.idx] = variable
        return gndatom
    
    def print_variables(self):
        for var in self.variables:
            print(str(var))
    
    def print_world_atoms(self, world, stream=sys.stdout):
        '''
        Prints the given world `world` as a readable string of the plain gnd atoms to the given stream.
        '''
        for gndatom in self.gndatoms:
            v = world[gndatom.idx]
            vstr = '%.3f' % v if v is not None else '?    '
            stream.write('%s  %s\n' % (vstr, str(gndatom)))
        
    def print_world_vars(self, world, stream=sys.stdout, tb=2):
        '''
        Prints the given world `world` as a readable string of the MRF variables to the given stream.
        '''
        out('=== WORLD VARIABLES ===', tb=tb)
        for var in self.variables:
            stream.write(repr(var) + '\n')
            for i, v in enumerate(var.evidence_value(world)):
                vstr = '%.3f' % v if v is not None else '?    '
                stream.write('  %s  %s\n' % (vstr, var.gndatoms[i])) 

    def print_domains(self):
        out('=== MRF DOMAINS ==', tb=2)
        for dom, values in self.domains.items():
            print(dom, '=', ','.join(values)) 

    def evidence_dicts(self):
        '''
        Returns, from the current evidence list, a dictionary that maps ground atom names to truth values
        '''
        d = {}
        for idx, tv in enumerate(self._evidence):
            d[str(self._gndatoms_by_idx[idx])] = tv
        return d

    def evidence_dicti(self):
        '''
        Returns, from the current evidence list, a dictionary that maps ground atom indices to truth values
        '''
        d = {}
        for idx, tv in enumerate(self._evidence):
            d[idx] = tv
        return d

    def countworlds(self, withevidence=False):
        '''
        Computes the number of possible worlds this MRF can take.
        
        :param withevidence:    (bool) if True, takes into account the evidence which is currently set in the MRF.
                                if False, computes the total number of possible worlds.
        
        .. note:: this method does not enumerate the possible worlds.
        '''
        worlds = 1
        ev = self.evidence_dicti if withevidence else {}
        for var in self.variables:
            worlds *= var.valuecount(ev)
        return worlds
    
    def iterworlds(self):
        '''
        Iterates over the possible worlds of this MRF taking into account the evidence vector of truth values.
        
        :returns:    a generator of (idx, possible world) tuples.
        '''
        for res in self._iterworlds([v for v in self.variables if v.valuecount(self.evidence) > 1], list(self.evidence), CallByRef(0), self.evidence_dicti()):
            yield res

    def _iterworlds(self, variables, world, worldidx, evidence):
        if not variables:
            yield worldidx.value, world
            worldidx.value += 1
            return
        variable = variables[0]
        if isinstance(variable, FuzzyVariable):
            world_ = list(world)
            value = variable.evidence_value(evidence)
            for res in self._iterworlds(variables[1:], variable.setval(value, world_), worldidx, evidence):
                yield res 
        else:
            for _, value in variable.itervalues(evidence):
                world_ = list(world)
                for res in self._iterworlds(variables[1:], variable.setval(value, world_), worldidx, evidence):
                    yield res 

    def worlds(self):
        '''
        Iterates over all possible worlds (taking evidence into account).
        
        :returns:    a generator of possible worlds.
        '''
        for _, world in self.iterworlds():
            yield world

    def iterallworlds(self):
        '''
        Iterates over all possible worlds (without) taking evidence into account).
        
        :returns:    a generator of possible worlds.
        '''
        world = [None] * len(self.evidence)
        for i, w in self._iterworlds(self.variables, world, CallByRef(0), {}):
            yield i, w

    def itergroundings(self, simplify=False, grounding_factory='DefaultGroundingFactory'):
        '''
        Iterates over all groundings of all formulas of this MRF.
        
        :param simplify:  if True, the ground formulas are simplified wrt to the evidence in the MRF.
        :param grounding_factory: the grounding factory to be used.  
        :returns:         a generator yielding ground formulas
        '''
        grounder = eval('%s(self, simplify=simplify)' % grounding_factory)
        for gndf in grounder.itergroundings():
            yield gndf

    def print_evidence_atoms(self, stream=sys.stdout):
        '''
        Prints the evidence truth values of plain ground atoms to the given `stream`.
        '''
        self.print_world_atoms(self.evidence, stream)

    def print_evidence_vars(self, stream=sys.stdout):
        '''
        Prints the evidence truth values of the variables of this MRF to the given `stream`.
        '''
        self.print_world_vars(self.evidence, stream, tb=3)    

    def getTruthDegreeGivenSoftEvidence(self, gf, world):
        cnf = gf.cnf()
        prod = 1.0
        if isinstance(cnf, FirstOrderLogic.Conjunction):
            for disj in cnf.children:
                prod *= self._noisyOr(world, disj)
        else:
            prod *= self._noisyOr(world, cnf)
        return prod

    def _getEvidenceTruthDegreeCW(self, gndAtom, worldValues):
        '''
            gets (soft or hard) evidence as a degree of belief from 0 to 1, making the closed world assumption,
            soft evidence has precedence over hard evidence
        '''
        se = self._getSoftEvidence(gndAtom)
        if se is not None:
            return se if (True == worldValues[gndAtom.idx] or None == worldValues[gndAtom.idx]) else 1.0 - se # TODO allSoft currently unsupported
        return 1.0 if worldValues[gndAtom.idx] else 0.0

    def print_gndatoms(self, stream=sys.stdout):
        '''
        Prints the alphabetically sorted list of ground atoms in this MRF to the given `stream`.
        '''
        out('=== GROUND ATOMS ===', tb=2)
        l = list(self._gndatoms.keys())
        for ga in sorted(l):
            stream.write(str(ga) + '\n')

    def apply_prob_constraints(self, constraints, method=InferenceMethods.EnumerationAsk, 
                                   thr=1.0e-3, steps=20, fittingMCSATSteps=5000, 
                                   fittingParams=None, given=None, queries=None, 
                                   maxThreshold=None, greedy=False, probabilityFittingResultFileName=None, **args):
        '''
        Applies the given probability constraints (if any), dynamically 
        modifying weights of the underlying MLN by applying iterative proportional fitting

        :param constraints: list of constraints
        :param method:      one of the inference methods defined in InferenceMethods
        inferenceParams:    parameters to pass on to the inference method
        :param given:       if not None, fit parameters of posterior (given the evidence) rather than prior
        :param querie       queries to compute along the way, results for which will be returned
        :param thr:         when maximum absolute difference between desired and actual probability drops below this value, then stop (convergence)
        maxThreshold:
            if not None, then convergence is relaxed, and we stop when the *mean* absolute difference between desired and
            actual probability drops below "threshold" *and* the maximum is below "maxThreshold"
        '''
        if fittingParams is None:
            fittingParams = {}
        inferenceParams = fittingParams
        inferenceParams["doProbabilityFitting"] = False # avoid recursive fitting calls when calling embedded inference method
        if given == None:
            given = ""
        if queries is None:
            queries = []
        if inferenceParams is None:
            inferenceParams = {}
        if not constraints:
            if queries: pass # TODO !!!! because this is called from inferIPFPM, should perform inference anyhow
            return
        t_start = time.time()

        # determine relevant formulas
        for req in constraints:
            # if we don't yet have a ground formula to fit, create one
            if not "gndFormula" in req:
                # if we don't yet have a formula to use, search for one that matches the expression to fit
                if not "idxFormula" in req:
                    idxFormula = None
                    for idxF, formula in enumerate(self.formulas):
                        #print strFormula(formula), req["expr"]
                        if fstr(formula).replace(" ", "") == req["expr"]:
                            idxFormula = idxF
                            break
                    if idxFormula is None:
                        raise Exception("Probability constraint on '%s' cannot be applied because the formula is not part of the MLN!" % req["expr"])
                    req["idxFormula"] = idxFormula
                # instantiate a ground formula
                formula = self.formulas[req["idxFormula"]]
                variables = formula.getVariables(self)
                groundVars = {}
                for varName, domName in variables.items(): # instantiate vars arbitrarily (just use first element of domain)
                    groundVars[varName] = self.domains[domName][0]
                gndFormula = formula.ground(self, groundVars)
                req["gndExpr"] = str(gndFormula)
                req["gndFormula"] = gndFormula

        # iterative fitting algorithm
        step = 1 # fitting round
        fittingStep = 1 # actual IPFP iteration
        #print "probConstraints", probConstraints, "queries", queries
        what = [r["gndFormula"] for r in constraints] + queries
        done = False
        while step <= steps and not done:
            # calculate probabilities of the constrained formulas (ground formula)
            if method is InferenceMethods.Exact:
                if not hasattr(self, "worlds"):
                    self._getWorlds()
                else:
                    self._calculateWorldValues()
                results = self.inferExact(what, given=given, verbose=False, **inferenceParams)
            elif method == InferenceMethods.EnumerationAsk:
                results = self.inferEnumerationAsk(what, given=given, verbose=False, **inferenceParams)
            #elif inferenceMethod == InferenceMethods.ExactLazy:
            #    results = self.inferExactLazy(what, given=given, verbose=False, **inferenceParams)
            elif method == InferenceMethods.MCSAT:
                results = self.inferMCSAT(what, given=given, verbose=False, maxSteps = fittingMCSATSteps, **inferenceParams)
            else:
                raise Exception("Requested inference method (%s) not supported by probability constraint fitting" % InferenceMethods.getName(method))
            if type(results) != list:
                results = [results]
            # compute deviations
            diffs = [abs(r["p"] - results[i]) for (i, r) in enumerate(constraints)]
            maxdiff = max(diffs)
            meandiff = sum(diffs) / len(diffs)
            # are we done?
            done = maxdiff <= thr
            if not done and maxThreshold is not None: # relaxed convergence criterion
                done = (meandiff <= thr) and (maxdiff <= maxThreshold)
            if done: break
            # select constraint to fit
            if greedy:
                idxConstraint = diffs.index(maxdiff)
                strStep = "%d;%d" % (step, fittingStep)
            else:
                idxConstraint = (fittingStep - 1) % len(constraints)
                strStep = "%d;%d/%d" % (step, idxConstraint + 1, len(constraints))
            req = constraints[idxConstraint]
            # get the scaling factor and apply it
            formula = self.formulas[req["idxFormula"]]
            p = results[idxConstraint]
            #print "p", p, "results", results, "idxConstraint", idxConstraint
            pnew = req["p"]
            precision = 1e-3
            if p == 0.0: p = precision
            if p == 1.0: p = 1 - precision
            f = pnew * (1 - p) / p / (1 - pnew)
            old_weight = formula.weight
            formula.weight += float(logx(f)) #make sure to set the weight to a native float and not an mpmath value
            diff = diffs[idxConstraint]
            # print status
            logger.debug("  [%s] p=%f vs. %f (diff = %f), weight %s: %f -> %f, dev max %f mean %f, elapsed: %.3fs" % (strStep, p, pnew, diff, str(formula), old_weight, formula.weight, maxdiff, meandiff, time.time() - t_start))
            if fittingStep % len(constraints) == 0:
                step += 1
            fittingStep += 1

        #write resulting mln:
        if probabilityFittingResultFileName != None:
            mlnFile = file(probabilityFittingResultFileName, "w")
            self.mln.write(mlnFile)
            mlnFile.close()
            print("written MLN with probability constraints to:", probabilityFittingResultFileName)

        return (results[len(constraints):], {"steps": min(step, steps), "fittingSteps": fittingStep, "maxdiff": maxdiff, "meandiff": meandiff, "time": time.time() - t_start})

    def _weights(self):
        ''' returns the weight vector as a list '''
        return [f.weight for f in self.formulas]

    def dotfile(self, filename):
        '''
        write a .dot file for use with GraphViz (in order to visualize the current ground Markov network)
        '''
        if not hasattr(self, "gndFormulas") or len(self.gndFormulas) == 0:
            raise Exception("Error: cannot create graph because the MLN was not combined with a concrete domain")
        with open(filename, "wb") as f:
            f.write("graph G {\n")
            graph = {}
            for gf in self.itergroundings:
                atomindices = gf.gndatom_indices()
                for i in range(len(atomindices)):
                    for j in range(i + 1, len(atomindices)):
                        edge = [atomindices[i], atomindices[j]]
                        edge.sort()
                        edge = tuple(edge)
                        if not edge in graph:
                            f.write("  ga%d -- ga%d\n" % edge)
                            graph[edge] = True
            for atom in list(self.gndatoms.values()):
                f.write('  ga%d [label="%s"]\n' % (atom.idx, str(atom)))
            f.write("}\n")

    def graphml(self, filename):
        import graphml  # @UnresolvedImport
        G = graphml.Graph()
        nodes = []
        for i in range(len(self.gndAtomsByIdx)):
            ga = self.gndAtomsByIdx[i]
            nodes.append(graphml.Node(G, label=str(ga), shape="ellipse", color=graphml.randomVariableColor))
        links = {}
        for gf in self.gndFormulas:
            print(gf)
            idxGAs = sorted(gf.idxGroundAtoms())
            for idx, i in enumerate(idxGAs):
                for j in idxGAs[idx+1:]:
                    t = (i,j)
                    if not t in links:
                        print("  %s -- %s" % (nodes[i], nodes[j]))
                        graphml.UndirectedEdge(G, nodes[i], nodes[j])
                        links[t] = True
        f = open(filename, "w")
        G.write(f)
        f.close()
