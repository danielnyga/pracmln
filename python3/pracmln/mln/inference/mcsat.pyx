# -*- coding: utf-8 -*-
#
# Markov Logic Networks
#
# (C) 2012-2015 by Daniel Nyga
#     2006-2011 by Dominik Jain
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

import math
import random
from collections import defaultdict

from dnutils import logs, ProgressBar, out

from .mcmc import MCMCInference
from ..constants import ALL, HARD
from ..grounding.fastconj import FastConjunctionGrounding
from ..util import item
from ...logic.common import Logic


logger = logs.getlogger(__name__)


class MCSAT(MCMCInference):
    """ 
    MC-SAT/MC-SAT-PC
    """
    
    def __init__(self, mrf, queries=ALL, **params):
        MCMCInference.__init__(self, mrf, queries, **params)
        self._weight_backup = list(self.mrf.mln.weights)
 
    
    def _initkb(self, verbose=False):
        """
        Initialize the knowledge base to the required format and collect structural information for optimization purposes
        """
        # convert the MLN ground formulas to CNF
        logger.debug("converting formulas to cnf...")
        #self.mln._toCNF(allPositive=True)
        self.formulas = []
        for f in self.mrf.formulas:
            if f.weight < 0:
                f.weight = -f.weight
                f = self.mln.logic.negate(f)
            self.formulas.append(f)
#         softweights = [1 - 1 / numpy.exp(w) for w in self.mln.weights if w != HARD]
#         stop(sorted(softweights, reverse=True))
#         w_mean = numpy.mean(softweights)
#         w_stdev = numpy.std(softweights)
#         for f in self.mrf.formulas:
#             if f.ishard: continue
#             f.weight  = min(w_stdev, f.weight)
        grounder = FastConjunctionGrounding(self.mrf, formulas=self.formulas, simplify=True, verbose=self.verbose)
        self.gndformulas = []
        for gf in grounder.itergroundings():
            if isinstance(gf, Logic.TrueFalse): continue
            self.gndformulas.append(gf.cnf())
        self._watch.tags.update(grounder.watch.tags)
#         self.gndformulas, self.formulas = Logic.cnf(grounder.itergroundings(), self.mln.formulas, self.mln.logic, allpos=True)
        # get clause data
        logger.debug("gathering clause data...")
        self.gf2clauseidx = {} # ground formula index -> tuple (idxFirstClause, idxLastClause+1) for use with range
        self.clauses = [] # list of clauses, where each entry is a list of ground literals
        #self.GAoccurrences = {} # ground atom index -> list of clause indices (into self.clauses)
        i_clause = 0
        # process all ground formulas
        for i_gf, gf in enumerate(self.gndformulas):
            # get the list of clauses
            if isinstance(gf, Logic.Conjunction):
                clauses = [clause for clause in gf.children if not isinstance(clause, Logic.TrueFalse)]
            elif not isinstance(gf, Logic.TrueFalse):
                clauses = [gf]
            else: continue
            self.gf2clauseidx[i_gf] = (i_clause, i_clause + len(clauses))
            # process each clause
            for c in clauses:
                if hasattr(c, "children"):
                    lits = c.children
                else: # unit clause
                    lits = [c]
                # add clause to list
                self.clauses.append(lits)
                # next clause index
                i_clause += 1
        # add clauses for soft evidence atoms
        for se in []:#self.softEvidence:
            se["numTrue"] = 0.0
            formula = self.mln.logic.parseFormula(se["expr"])
            se["formula"] = formula.ground(self.mrf, {})
            cnf = formula.toCNF().ground(self.mrf, {}) 
            idxFirst = i_clause
            for clause in self._formulaClauses(cnf):                
                self.clauses.append(clause)
                #print clause
                i_clause += 1
            se["idxClausePositive"] = (idxFirst, i_clause)
            cnf = self.mln.logic.negation([formula]).toCNF().ground(self.mrf, {})
            idxFirst = i_clause
            for clause in self._formulaClauses(cnf):                
                self.clauses.append(clause)
                #print clause
                i_clause += 1
            se["idxClauseNegative"] = (idxFirst, i_clause)
            
            
    def _formula_clauses(self, f):
        # get the list of clauses
        if isinstance(f, Logic.Conjunction):
            lc = f.children
        else:
            lc = [f]
        # process each clause
        for c in lc:
            if hasattr(c, "children"):
                yield c.children
            else: # unit clause
                yield [c]
                
    
    @property
    def chains(self):
        return self._params.get('chains', 1)
    
    @property
    def maxsteps(self):
        return self._params.get('maxsteps', 500)
    
    @property
    def softevidence(self):
        return self._params.get('softevidence', False)
    
    @property
    def use_se(self):
        return self._params.get('use_se')
    
    @property
    def p(self):
        return self._params.get('p', .5)
    
    @property
    def resulthistory(self):
        return self._params.get('resulthistory', False)
    
    @property
    def historyfile(self):
        return self._params.get('historyfile', None)
    
    @property
    def rndseed(self):
        return self._params.get('rndseed', None)
    
    @property
    def initalgo(self):
        return self._params.get('initalgo', 'SampleSAT')
    
    
    def _run(self):
        """
        p: probability of a greedy (WalkSAT) move
        initAlgo: algorithm to use in order to find an initial state that satisfies all hard constraints ("SampleSAT" or "SAMaxWalkSat")
        verbose: whether to display results upon completion
        details: whether to display information while the algorithm is running            
        infoInterval: [if details==True] interval (no. of steps) in which to display the current step number and some additional info
        resultsInterval: [if details==True] interval (no. of steps) in which to display intermediate results; [if keepResultsHistory==True] interval in which to store intermediate results in the history
        debug: whether to display debug information (e.g. internal data structures) while the algorithm is running
            debugLevel: controls degree to which debug information is presented
        keepResultsHistory: whether to store the history of results (at each resultsInterval)
        referenceResults: reference results to compare obtained results to
        saveHistoryFile: if not None, save history to given filename
        sampleCallback: function that is called for every sample with the sample and step number as parameters
        softEvidence: if None, use soft evidence from MLN, otherwise use given dictionary of soft evidence
        handleSoftEvidence: if False, ignore all soft evidence in the MCMC sampling (but still compute softe evidence statistics if soft evidence is there)
        """
        logger.debug("starting MC-SAT with maxsteps=%d, softevidence=%s" % (self.maxsteps, self.softevidence))
        # initialize the KB and gather required info
        self._initkb()
        # print CNF KB
        logger.debug("CNF KB:")
        for gf in self.gndformulas:
            logger.debug("%7.3f  %s" % (gf.weight, str(gf)))
        print()
        # set the random seed if it was given
        if self.rndseed is not None:
            random.seed(self.rndseed)
        # create chains
        chaingroup = MCMCInference.ChainGroup(self)
        self.chaingroup = chaingroup
        for i in range(self.chains):
            chain = MCMCInference.Chain(self, self.queries)
            chaingroup.chain(chain)
            # satisfy hard constraints using initialization algorithm
            M = []
            NLC = []
            for i, gf in enumerate(self.gndformulas):
                if gf.weight == HARD:
                    if gf.islogical():
                        clause_range = self.gf2clauseidx[i]
                        M.extend(list(range(*clause_range)))
                    else:
                        NLC.append(gf)
            if M or NLC:
                logger.debug('Running SampleSAT')
                chain.state = SampleSAT(self.mrf, chain.state, M, NLC, self, p=self.p).run() # Note: can't use p=1.0 because there is a chance of getting into an oscillating state
        if logger.level == logs.DEBUG:
            self.mrf.print_world_vars(chain.state)
        self.step = 1        
        logger.debug('running MC-SAT with %d chains' % len(chaingroup.chains))
        self._watch.tag('running MC-SAT', self.verbose)
        if self.verbose:
            bar = ProgressBar(steps=self.maxsteps, color='green')
        while self.step <= self.maxsteps:
            # take one step in each chain
            for chain in chaingroup.chains:
                # choose a subset of the satisfied formulas and sample a state that satisfies them
                state = self._satisfy_subset(chain)
                # update chain counts
                chain.update(state)
            if self.verbose:
                bar.inc()
                bar.label('%d / %d' % (self.step, self.maxsteps))
            # intermediate results
            self.step += 1
        # get results
        self.step -= 1
        results = chaingroup.results()
        return results[0]
    
    
    def _satisfy_subset(self, chain):
        """
        Choose a set of logical formulas M to be satisfied (more specifically, M is a set of clause indices)
        and also choose a set of non-logical constraints NLC to satisfy
        """
        M = []
        NLC = []
        for gfidx, gf in enumerate(self.gndformulas):
            if gf(chain.state) == 1 or gf.ishard:
                expweight = math.exp(gf.weight)
                u = random.uniform(0, expweight)
                if u > 1:
                    if gf.islogical():
                        clause_range = self.gf2clauseidx[gfidx]
                        M.extend(list(range(*clause_range)))
                    else:
                        NLC.append(gf)
        # add soft evidence constraints
        if False:# self.softevidence:
            for se in self.softevidence:
                p = se["numTrue"] / self.step
                
                #l = self.phistory.get(strFormula(se["formula"]), [])
                #l.append(p)
                #self.phistory[strFormula(se["formula"])] = l
                
                if se["formula"](chain.state):
                    #print "true case"
                    add = False
                    if p < se['p']:
                        add = True
                    if add:
                        M.extend(list(range(*se["idxClausePositive"])))
                    #print "positive case: add=%s, %s, %f should become %f" % (add, map(str, [map(str, self.clauses[i]) for i in range(*se["idxClausePositive"])]), p, se["p"])
                else:
                    #print "false case"
                    add = False
                    if p > se["p"]:
                        add = True
                    if add:
                        M.extend(list(range(*se["idxClauseNegative"])))
                    #print "negative case: add=%s, %s, %f should become %f" % (add, map(str, [map(str, self.clauses[i]) for i in range(*se["idxClauseNegative"])]), p, se["p"])
        # (uniformly) sample a state that satisfies them
        return SampleSAT(self.mrf, chain.state, M, NLC, self, p=self.p).run()
    
    
    def _prob_constraints_deviation(self):
        if len(self.softevidence) == 0:
            return {}
        se_mean, se_max, se_max_item = 0.0, -1, None
        for se in self.softevidence:
            dev = abs((se["numTrue"] / self.step) - se["p"])
            se_mean += dev
            if dev > se_max:
                se_max = max(se_max, dev)
                se_max_item = se
        se_mean /= len(self.softevidence)
        return {"pc_dev_mean": se_mean, "pc_dev_max": se_max, "pc_dev_max_item": se_max_item["expr"]}
    
    
    def _extend_results_history(self, results):
        cur_results = {"step": self.step, "results": list(results), "time": self._getElapsedTime()[0]}
        cur_results.update(self._getProbConstraintsDeviation())
        if self.referenceResults is not None:
            cur_results.update(self._compareResults(results, self.referenceResults))
        self.history.append(cur_results)
    
        
    def getResultsHistory(self):
        return self.resultsHistory


class SampleSAT:
    """
    Sample-SAT algorithm.
    """
    
    def __init__(self, mrf, state, clause_indices, nlcs, infer, p=1):
        """
        clause_indices: list of indices of clauses to satisfy
        p: probability of performing a greedy WalkSAT move
        state: the state (array of booleans) to work with (is reinitialized randomly by this constructor)
        NLConstraints: list of grounded non-logical constraints
        """
        self.debug = logger.level == logs.DEBUG
        self.infer = infer
        self.mrf = mrf
        self.mln = mrf.mln        
        self.p = p
        # initialize the state randomly (considering the evidence) and obtain block info
        self.blockInfo = {}
        self.state = self.infer.random_world()
#         out(self.state, '(initial state)')
        self.init = list(state)
        # these are the variables we need to consider for SampleSAT
#         self.variables = [v for v in self.mrf.variables if v.valuecount(self.mrf.evidence) > 1]
        # list of unsatisfied constraints
        self.unsatisfied = set()
        # keep a map of bottlenecks: index of the ground atom -> list of constraints where the corresponding lit is a bottleneck
        self.bottlenecks = defaultdict(list) # bottlenecks are clauses with exactly one true literal
        # ground atom occurrences in constraints: ground atom index -> list of constraints
        self.var2clauses = defaultdict(set)
        self.clauses = {}
        # instantiate clauses        
        for cidx in clause_indices:  
            clause = SampleSAT._Clause(self.infer.clauses[cidx], self.state, cidx, self.mrf)
            self.clauses[cidx] = clause
            if clause.unsatisfied: 
                self.unsatisfied.add(cidx)
            for v in clause.variables():
                self.var2clauses[v].add(clause)
#             stop('clause', 'v'.join(map(str, self.infer.clauses[cidx])), 'is', 'unsatisfied' if clause.unsatisfied else 'satisfied')
        # instantiate non-logical constraints
        for nlc in nlcs:
            if isinstance(nlc, Logic.GroundCountConstraint): # count constraint
                SampleSAT._CountConstraint(self, nlc)
            else:
                raise Exception("SampleSAT cannot handle constraints of type '%s'" % str(type(nlc)))
        
        
    def _print_unsatisfied_constraints(self):
        out("   %d unsatisfied:  %s" % (len(self.unsatisfied), list(map(str, [self.clauses[i] for i in self.unsatisfied]))), tb=2)
    
    
    def run(self):
        # sampling by enumerating all worlds
        worlds = []
        for world in self.mrf.worlds():
            skip = False
            for clause in list(self.clauses.values()):
                if not clause.satisfied_in_world(world):
                    skip = True
                    break
            if skip: continue
            worlds.append(world)
        state = worlds[random.randint(0, len(worlds)-1)]
        return state
        steps = 0
        while self.unsatisfied:
            steps += 1
            # make a WalkSat move or a simulated annealing move
            if random.uniform(0, 1) <= self.p:
                self._walksat_move()
            else:
                self._sa_move()
        return self.state
    
    
    def _walksat_move(self):
        """
        Randomly pick one of the unsatisfied constraints and satisfy it
        (or at least make one step towards satisfying it
        """
        clauseidx = list(self.unsatisfied)[random.randint(0, len(self.unsatisfied) - 1)]
        # get the literal that makes the fewest other formulas false
        clause = self.clauses[clauseidx]
        varval_opt = []
        opt = None
        for var in clause.variables():
            bottleneck_clauses = [cl for cl in self.var2clauses[var] if cl.bottleneck is not None]
            for _, value in var.itervalues(self.mrf.evidence_dicti()):
                if not clause.turns_true_with(var, value): continue
                unsat = 0
                for c in bottleneck_clauses:
                    # count the  constraints rendered unsatisfied for this value from the bottleneck atoms
                    turnsfalse = 1 if c.turns_false_with(var, value) else 0 
                    unsat +=  turnsfalse
                append = False
                if opt is None or unsat < opt:
                    opt = unsat
                    varval_opt = []
                    append = True
                elif opt == unsat:
                    append = True 
                if append:
                    varval_opt.append((var, value))
        if varval_opt:
            varval = varval_opt[random.randint(0, len(varval_opt) - 1)] 
            self._setvar(*varval)
                
                
    def _setvar(self, var, val):
        """
        Set the truth value of a variable and update the information in the constraints.
        """
        var.setval(val, self.state)
        for c in self.var2clauses[var]:
            satisfied, _ = c.update(var, val)
            if satisfied:
                if c.cidx in self.unsatisfied: self.unsatisfied.remove(c.cidx)
            else:
                self.unsatisfied.add(c.cidx)
               
               
    def _sa_move(self):
        # randomly pick a variable and flip its value
        variables = list(set(self.var2clauses))
        random.shuffle(variables)
        var = variables[0]
        ev = var.evidence_value()
        values = var.valuecount(self.mrf.evidence)
        for _, v in var.itervalues(self.mrf.evidence): break
        if values == 1:
            raise Exception('Only one remaining value for variable %s: %s. Please check your evidences.' % (var, v))
        values = [v for _, v in var.itervalues(self.mrf.evidence) if v != ev]
        val = values[random.randint(0, len(values)-1)]
        unsat = 0
        bottleneck_clauses = [c for c in self.var2clauses[var] if c.bottleneck is not None]
        for c in bottleneck_clauses:
            # count the  constraints rendered unsatisfied for this value from the bottleneck clauses
            uns = 1 if c.turns_false_with(var, val) else 0
#             cur = 1 if c.unsatisfied else 0
            unsat += uns# - cur
        if unsat <= 0: # the flip causes an improvement. take it with p=1.0
            p = 1.
        else:
            # !!! the temperature has a great effect on the uniformity of the sampled states! it's a "magic" number 
            # that needs to be chosen with care. if it's too low, then probabilities will be way off; if it's too high, it will take longer to find solutions
            # temp = 14.0 # the higher the temperature, the greater the probability of deciding for a flip
            # we take as a heuristic the normalized difference between bottleneck clauses and clauses that actually
            # will turn false, such that if no clause will turn false, p is 1
            p = math.exp(- 1 + float(len(bottleneck_clauses) - unsat) / len(bottleneck_clauses))
        # decide and set
        if random.uniform(0, 1) <= p:
            self._setvar(var, val)
        
    
    class _Clause(object):
        
        def __init__(self, lits, world, idx, mrf):
            self.cidx = idx
            self.world = world
            self.bottleneck = None
            self.mrf = mrf
            # check all the literals
            self.lits = lits
            self.truelits = set()
            self.atomidx2lits = defaultdict(set)
            for lit in lits:
                if isinstance(lit, Logic.TrueFalse): continue
                atomidx = lit.gndatom.idx
                self.atomidx2lits[atomidx].add(0 if lit.negated else 1)
                if lit(world) == 1:
                    self.truelits.add(atomidx)
            if len(self.truelits) == 1 and self._isbottleneck(item(self.truelits)):
                self.bottleneck = item(self.truelits)
        
        
        def _isbottleneck(self, atomidx):
            atomidx2lits = self.atomidx2lits
            if len(self.truelits) != 1 or atomidx not in self.truelits: return False
            if len(atomidx2lits[atomidx]) == 1: return True
            fst = item(atomidx2lits[atomidx])
            if all([x == fst for x in atomidx2lits[atomidx]]): return False # the atom appears with different polarity in the clause, this is not a bottleneck
            return True
        
        
        def turns_false_with(self, var, val):
            """
            Returns whether or not this clause would become false if the given variable would take
            the given value. Returns False if the clause is already False.
            """
            for a, v in var.atomvalues(val):
                if a.idx == self.bottleneck and v not in self.atomidx2lits[a.idx]: return True
            return False
        
        
        def turns_true_with(self, var, val):
            """
            Returns true if this clause will be rendered true by the given variable taking
            its given value.
            """
            for a, v in var.atomvalues(val):
                if self.unsatisfied and v in self.atomidx2lits[a.idx]: return True
            return False
            
        
        def update(self, var, val):
            """
            Updates the clause information with the given variable and value set in a SampleSAT state.
            """
            for a, v in var.atomvalues(val):
                if v not in self.atomidx2lits[a.idx]:
                    if a.idx in self.truelits: self.truelits.remove(a.idx)
                else: self.truelits.add(a.idx)
            if len(self.truelits) == 1 and self._isbottleneck(item(self.truelits)):
                self.bottleneck = item(self.truelits)
            else:
                self.bottleneck = None
            return self.satisfied, self.bottleneck
                
        
        def satisfied_in_world(self, world):
            return self.mrf.mln.logic.disjugate(self.lits)(world) == 1
        
        @property
        def unsatisfied(self):
            return not self.truelits
        
        @property
        def satisfied(self):
            return not self.unsatisfied
        
        
        def variables(self):
            return [self.mrf.variable(self.mrf.gndatom(a)) for a in self.atomidx2lits]
        
        def greedySatisfy(self):
            self.ss._pickAndFlipLiteral([x.gndAtom.idx for x in self.lits], self)
        
        def __str__(self):
            return ' v '.join(map(str, self.lits))
        
                
    class _CountConstraint:
        def __init__(self, sampleSAT, groundCountConstraint):
            self.ss = sampleSAT
            self.cc = groundCountConstraint
            self.trueOnes = []
            self.falseOnes = []
            # determine true and false ones
            for ga in groundCountConstraint.gndAtoms:
                idxGA = ga.idx
                if self.ss.state[idxGA]:
                    self.trueOnes.append(idxGA)
                else:
                    self.falseOnes.append(idxGA)
                self.ss._addGAOccurrence(idxGA, self)
            # determine bottlenecks
            self._addBottlenecks()
            # if the formula is unsatisfied, add it to the list
            if not self._isSatisfied():
                self.ss.unsatisfiedConstraints.append(self)
        
        def _isSatisfied(self):
            return eval("len(self.trueOnes) %s self.cc.count" % self.cc.op)
        
        def _addBottlenecks(self):
            # there are only bottlenecks if we are at the border of the interval
            numTrue = len(self.trueOnes)
            if self.cc.op == "!=":
                trueNecks = numTrue == self.cc.count + 1
                falseNecks = numTrue == self.cc.count - 1
            else:
                border = numTrue == self.cc.count
                trueNecks = border and self.cc.op in ["==", ">="]
                falseNecks = border and self.cc.op in ["==", "<="]
            if trueNecks:
                for idxGA in self.trueOnes:
                    self.ss._addBottleneck(idxGA, self)
            if falseNecks:
                for idxGA in self.falseOnes:
                    self.ss._addBottleneck(idxGA, self)
        
        def greedySatisfy(self):
            c = len(self.trueOnes)
            satisfied = self._isSatisfied()
            assert not satisfied
            if c < self.cc.count and not satisfied:
                self.ss._pickAndFlipLiteral(self.falseOnes, self)
            elif c > self.cc.count and not satisfied:
                self.ss._pickAndFlipLiteral(self.trueOnes, self)
            else: # count must be equal and op must be !=
                self.ss._pickAndFlipLiteral(self.trueOnes + self.falseOnes, self)
        
        def flipSatisfies(self, idxGA):
            if self._isSatisfied():
                return False
            c = len(self.trueOnes)            
            if idxGA in self.trueOnes:
                c2 = c - 1
            else:
                assert idxGA in self.falseOnes
                c2 = c + 1
            return eval("c2 %s self.cc.count" % self.cc.op)
        
        def handleFlip(self, idxGA):
            """
            Handle all effects of the flip except bottlenecks of the flipped
            gnd atom and clauses that became unsatisfied as a result of a bottleneck flip
            """
            wasSatisfied = self._isSatisfied()
            # update true and false ones
            if idxGA in self.trueOnes:
                self.trueOnes.remove(idxGA)
                self.falseOnes.append(idxGA)
            else:
                self.trueOnes.append(idxGA)
                self.falseOnes.remove(idxGA)
            isSatisfied = self._isSatisfied()
            # if the constraint was previously satisfied and is now unsatisfied or
            # if the constraint was previously satisfied and is still satisfied (i.e. we are pushed further into the satisfying interval, away from the border),
            # remove all the bottlenecks (if any)
            if wasSatisfied:
                for idxGndAtom in self.trueOnes + self.falseOnes: 
                    if idxGndAtom in self.ss.bottlenecks and self in self.ss.bottlenecks[idxGndAtom]: # TODO perhaps have a smarter method to know which ones actually were bottlenecks (or even info about whether we had bottlenecks)
                        if idxGA != idxGndAtom:
                            self.ss.bottlenecks[idxGndAtom].remove(self)
                # the constraint was added to the list of unsatisfied ones in SampleSAT._flipGndAtom (bottleneck flip)
            # if the constraint is newly satisfied, remove it from the list of unsatisfied ones
            elif not wasSatisfied and isSatisfied:
                self.ss.unsatisfiedConstraints.remove(self)
            # bottlenecks must be added if, because of the flip, we are now at the border of the satisfying interval
            self._addBottlenecks()
            
        def __str__(self):
            return str(self.cc)
    
        def getFormula(self):
            return self.cc
    

# class FuzzyMCSAT(Inference):
#     """
#     MC-SAT version supporting fuzzy evidence atoms.
#     """
#     
#     def __init__(self, mrf, queries=ALL, **params):
#         Inference.__init__(self, mrf, queries, **params)
#         
#         
#     def _run(self):
#         # create the transformed MLN without fuzzy evidence
#         mln_ = self.mrf.mln.copy()
# #         mln.domains = {}
#         mln_._rmformulas()
#         # remove fuzzy preds
#         grounder = FastConjunctionGrounding(self.mrf, self.mrf.formulas, unsatfailure=True, multicore=self.multicore)
#         for gf in grounder.itergroundings():
#             if gf.ishard: mln_.formula(gf, weight=HARD)
#             cnf = gf.cnf()
# #             out(cnf.weight, cnf)
#             if isinstance(cnf, Logic.TrueFalse) or not hasattr(cnf, 'children'): continue
#             mintruth = cnf.mintruth(self.mrf.evidence)
#             maxtruth = cnf.maxtruth(self.mrf.evidence)
# #             out(mintruth, maxtruth)
#             # the result of following list comprehension is a list of clauses of literals of the
#             # CNF, where all truth constants have been removed. If there are conjuncts consisting
#             # of single literals (e.g. such as A in A ^ (B v C)), those will be wrapped in a list
#             # with only one element
#             clauses = [([mln_.logic.lit(l.negated, l.predname, l.args, mln_) for l in d.children if not isinstance(l, Logic.TrueFalse)] if hasattr(d, 'children') else [mln_.logic.lit(d.negated, d.predname, d.args, mln_)]) for d in cnf.children if not isinstance(d, Logic.TrueFalse)]
# #             out(clauses)
#             weight = gf.weight * maxtruth
#             formula = mln_.logic.conjugate([mln_.logic.disjugate(clause) for clause in clauses])
#             mln_.formula(formula, weight)
# #             stop('=>', formula, weight)
# #             formula.print_structure()
# #             stop()
# #         mln_.write()
# #         stop()
#         mln_.tofile('fuzzyconv.mln')
#         mln__ = mln_.materialize(self.mrf.db)
#         mrf = mln__.ground(self.mrf.db)
#         self.mrf = mrf
#         mcsat = MCSAT(mrf, queries=self.queries, **self._params)
#         return mcsat._run()

