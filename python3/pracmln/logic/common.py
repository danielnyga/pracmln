# LOGIC -- COMMON BASE CLASSES
#
# (C) 2012-2013 by Daniel Nyga (nyga@cs.uni-bremen.de)
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

import sys

from dnutils import logs, ifnone

from .grammar import StandardGrammar, PRACGrammar
from ..mln.util import fstr, dict_union, colorize
from ..mln.errors import NoSuchDomainError, NoSuchPredicateError
from ..mln.constants import HARD, predicate_color, inherit, auto
from collections import defaultdict
import itertools
from functools import reduce

logger = logs.getlogger(__name__)

def latexsym(sym):
#     import re
#     sym = re.sub(r'^\w+^[_]', '', sym)
#     print sym
#     sym = re.sub(r'_', r'\_', sym)
#     if len(sym) == 1:
#         return ' %s' % sym
#     elif sym.startswith('?'):
#         return ' '
    return r'\textit{%s}' % str(sym)

class Logic(object):
    """
    Abstract factory class for instantiating logical constructs like conjunctions, 
    disjunctions etc. Every specifc logic should implement the methods and return
    an instance of the respective element. They also might override the respective
    implementations and behavior of the logic.
    """
    
    def __init__(self, grammar, mln):
        """
        Creates a new instance of a Logic factory class.
        
        :param grammar:     an instance of grammar.Grammar
        :param mln:         the MLN instance that the logic shall be tied to.
        """
        if grammar not in ('StandardGrammar', 'PRACGrammar'):
            raise Exception('Invalid grammar: %s' % grammar)
        self.grammar = eval(grammar)(self)
        self.mln = mln
    
    
    def __getstate__(self):
        d = self.__dict__.copy()
        d['grammar'] = type(self.grammar).__name__
        return d
        
    def __setstate__(self, d):
        self.__dict__ = d
        self.grammar = eval(d['grammar'])(self)
        
    
#  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #   
    class Constraint(object):
        """
        Super class of every constraint.
        """
        
        
        def template_variants(self, mln):
            """
            Gets all the template variants of the constraint for the given mln/ground markov random field.
            """
            raise Exception("%s does not implement getTemplateVariants" % str(type(self)))
        
        
        def truth(self, world):
            """
            Returns the truth value of the constraint in given a complete possible world
            
            
            :param world:     a possible world as a list of truth values
            """
            raise Exception("%s does not implement truth" % str(type(self)))
    
    
        def islogical(self):
            """
            Returns whether this is a logical constraint, i.e. a logical formula
            """
            raise Exception("%s does not implement islogical" % str(type(self)))
    
    
        def itergroundings(self, mrf, simplify=False, domains=None):
            """
            Iteratively yields the groundings of the formula for the given ground MRF
            - simplify:     If set to True, the grounded formulas will be simplified
                            according to the evidence set in the MRF.
            - domains:      If None, the default domains will be used for grounding.
                            If its a dict mapping the variable names to a list of values,
                            these values will be used instead.
            """
            raise Exception("%s does not implement itergroundings" % str(type(self)))
    
        
        def idx_gndatoms(self, l=None):
            raise Exception("%s does not implement idxgndatoms" % str(type(self)))
    
        
        def gndatoms(self, l=None):
            raise Exception("%s does not implement gndatoms" % str(type(self)))
        
        
#  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #

      
    class Formula(Constraint): 
        """ 
        The base class for all logical formulas.
        """
        
        def __init__(self, mln=None, idx=None):
            self.mln = mln
            if idx == auto and mln is not None:
                self.idx = len(mln.formulas)
            else:
                self.idx = idx
        
        @property
        def idx(self):
            """
            The formula's weight.
            """
#             if self._idx is None:
#                 try: return self.mln._formulas.index(self)
#                 except ValueError: 
#                     return None 
            return self._idx
        
        
        @idx.setter
        def idx(self, idx):
#             print 'setting idx to', idx
            self._idx = idx
        
            
        @property
        def mln(self):
            """
            Specifies whether the weight of this formula is fixed for learning.
            """
            return self._mln
        
        
        @mln.setter
        def mln(self, mln):
            if hasattr(self, 'children'):
                for child in self.children:
                    child.mln = mln
            self._mln = mln
        
        
        @property
        def weight(self):
            return self.mln.weight(self.idx)
        
        
        @weight.setter
        def weight(self, w):
            if self.idx is None:
                raise Exception('%s does not have an index' % str(self))
            self.mln.weight(self.idx, w)
        
        
        @property
        def ishard(self):
            return self.weight == HARD
        
        
        def contains_gndatom(self, gndatomidx):
            """
            Checks if this formula contains the ground atom with the given index.
            """
            if not hasattr(self, "children"):
                return False
            for child in self.children:
                if child.contains_gndatom(gndatomidx):
                    return True
            return False
    
    
        def gndatom_indices(self, l=None):
            """
            Returns a list of the indices of all ground atoms that
            are contained in this formula.
            """
            if l == None: l = []
            if not hasattr(self, "children"):
                return l
            for child in self.children:
                child.gndatom_indices(l)
            return l
    
    
        def gndatoms(self, l=None):
            """
            Returns a list of all ground atoms that are contained
            in this formula.
            """
            if l is None: l = []
            if not hasattr(self, "children"):
                return l
            for child in self.children:
                child.gndatoms(l)
            return l
    
    
        def templ_atoms(self):
            """
            Returns a list of template variants of all atoms 
            that can be generated from this formula and the given mln.
            
            :Example: 
            
            foo(?x, +?y) ^ bar(?x, +?z) --> [foo(?x, X1), foo(?x, X2), ..., 
                                                      bar(?x, Z1), bar(?x, Z2), ...]
            """
            templ_atoms = []
            for literal in self.literals():
                for templ in literal.template_variants():
                    templ_atoms.append(templ)
            return templ_atoms
        
        
        def atomic_constituents(self, oftype=None):
            """
            Returns a list of all atomic logical constituents, optionally filtered
            by type. 
            
            Example: f.atomic_constituents(oftype=Logic.Equality)
            
            returns a list of all equality constraints in this formula.
            """
            const = list(self.literals())
            if oftype is None: return const
            else: return [c for c in const if isinstance(c, oftype)]
            
    
        def template_variants(self):
            """
            Gets all the template variants of the formula for the given MLN 
            """
            uniqvars = list(self.mln._unique_templvars[self.idx])
            vardoms = self.template_variables()
            # get the vars with the same domains that should not be expanded ambiguously
            uniqvars_ = defaultdict(set)
            for var in uniqvars:
                dom = vardoms[var]
                uniqvars_[dom].add(var)
            assignments = []
            # create sets of admissible variable assignments for the groups of unique template variables
            for domain, variables in uniqvars_.items():
                group = []
                domvalues = self.mln.domains[domain] 
                if not domvalues:
                    logger.warning('Template variants cannot be constructed since the domain "{}" is empty.'.format(domain))
                for values in itertools.combinations(domvalues, len(variables)):
                    group.append(dict([(var, val) for var, val in zip(variables, values)]))
                assignments.append(group)
            # add the non-unique variables
            for variable, domain in vardoms.items():
                if variable in uniqvars: continue
                group = []
                domvalues = self.mln.domains[domain] 
                if not domvalues:
                    logger.warning('Template variants cannot be constructed since the domain "{}" is empty.'.format(domain))
                for value in self.mln.domains[domain]:
                    group.append(dict([(variable, value)]))
                assignments.append(group)
            # generate the combinations of values
            def product(assign, result=[]):
                if len(assign) == 0:
                    yield result
                    return
                for a in assign[0]:
                    for r in product(assign[1:], result+[a]): yield r
            for assignment in product(assignments):
                if assignment:
                    for t in self._ground_template(reduce(lambda x, y: dict_union(x, y), itertools.chain(assignment))):
                        yield t
                else: 
                    for t in self._ground_template({}):
                        yield t

        def template_variables(self, variable=None):
            """
            Gets all variables of this formula that are required to be expanded 
            (i.e. variables to which a '+' was appended) and returns a 
            mapping (dict) from variable name to domain name.
            """
            raise Exception("%s does not implement template_variables" % str(type(self)))
        
        
        def _ground_template(self, assignment):
            """
            Grounds this formula for the given assignment of template variables 
            and returns a list of formulas, the list of template variants
            - assignment: a mapping from variable names to constants
            """
            raise Exception("%s does not implement _ground_template" % str(type(self)))
    
    
        def itervargroundings(self, mrf, partial=None):
            """
            Yields dictionaries mapping variable names to values
            this formula may be grounded with without grounding it. If there are not free
            variables in the formula, returns an empty dict.
            """
#             try:
            variables = self.vardoms()
            if partial is not None: 
                for v in [p for p in partial if p in variables]: del variables[v]
#             except Exception, e:
#                 raise Exception("Error finding variable assignments '%s': %s" % (str(self), str(e)))
            for assignment in self._itervargroundings(mrf, variables, {}):
                yield assignment
                
    
        def _itervargroundings(self, mrf, variables, assignment):
            # if all variables have been assigned a value...
            if variables == {}:
                yield assignment
                return
            # ground the first variable...
            variables = dict(variables)
            varname, domname = variables.popitem()
            domain = mrf.domains[domname]
            assignment = dict(assignment)
            for value in domain: # replacing it with one of the constants
                assignment[varname] = value
                # recursive descent to ground further variables
                for assign in self._itervargroundings(mrf, dict(variables), assignment):
                    yield assign
                    
    
        def itergroundings(self, mrf, simplify=False, domains=None):
            """
            Iteratively yields the groundings of the formula for the given grounder
            
            :param mrf:          an object, such as an MRF instance, which
            :param simplify:     If set to True, the grounded formulas will be simplified
                                 according to the evidence set in the MRF.
            :param domains:      If None, the default domains will be used for grounding.
                                 If its a dict mapping the variable names to a list of values,
                                 these values will be used instead.
            :returns:            a generator for all ground formulas
            """
            try:
                variables = self.vardoms()
            except Exception as e:
                raise Exception("Error grounding '%s': %s" % (str(self), str(e)))
            for grounding in self._itergroundings(mrf, variables, {}, simplify, domains):
                yield grounding
            
            
        def iter_true_var_assignments(self, mrf, world=None, truth_thr=1.0, strict=False, unknown=False, partial=None):
            """
            Iteratively yields the variable assignments (as a dict) for which this
            formula exceeds the given truth threshold. 
            
            Same as itergroundings, but returns variable mappings only for assignments rendering this formula true.
            
            :param mrf:        the MRF instance to be used for the grounding.
            :param world:      the possible world values. if `None`, the evidence in the MRF is used.
            :param thr:        a truth threshold for this formula. Only variable assignments rendering this
                               formula true with at least this truth value will be returned.
            :param strict:     if `True`, the truth value of the formula must be strictly greater than the `thr`.
                               if `False`, it can be greater or equal.
            :param unknown:    If `True`, also groundings with the truth value `None` are returned
            """
            if world is None:
                world = list(mrf.evidence)
            if partial is None:
                partial = {}
            try:
                variables = self.vardoms()
                for var in partial:
                    if var in variables: del variables[var]
            except Exception as e:
                raise Exception("Error grounding '%s': %s" % (str(self), str(e)))
            for assignment in self._iter_true_var_assignments(mrf, variables, partial, world,
                                                                dict(variables), truth_thr=truth_thr, strict=strict, unknown=unknown):
                yield assignment
        
        
        def _iter_true_var_assignments(self, mrf, variables, assignment, world, allvars, truth_thr=1.0, strict=False, unknown=False):
            # if all variables have been grounded...
            if variables == {}:
                gf = self.ground(mrf, assignment)
                truth = gf(world)
                if (((truth >= truth_thr) if not strict else (truth > truth_thr)) and truth is not None) or (truth is None and unknown):
                    true_assignment = {}
                    for v in allvars:
                        true_assignment[v] = assignment[v]
                    yield true_assignment
                return
            # ground the first variable...
            varname, domname = variables.popitem()
            assignment_ = dict(assignment) # copy for avoiding side effects
            if domname not in mrf.domains: raise NoSuchDomainError('The domain %s does not exist, but is needed to ground the formula %s' % (domname, str(self)))
            for value in mrf.domains[domname]: # replacing it with one of the constants
                assignment_[varname] = value
                # recursive descent to ground further variables
                for ass in self._iter_true_var_assignments(mrf, dict(variables), assignment_, world, allvars,
                                                             truth_thr=truth_thr, strict=strict, unknown=unknown):
                    yield ass
                    
                    
        def _itergroundings(self, mrf, variables, assignment, simplify=False, domains=None):
            # if all variables have been grounded...
            if not variables:
                gf = self.ground(mrf, assignment, simplify, domains)
                yield gf
                return
            # ground the first variable...
            varname, domname = variables.popitem()
            domain = domains[varname] if domains is not None else mrf.domains[domname]
            for value in domain: # replacing it with one of the constants
                assignment[varname] = value
                # recursive descent to ground further variables
                for gf in self._itergroundings(mrf, dict(variables), assignment, simplify, domains):
                    yield gf
        
        
        def vardoms(self, variables=None, constants=None):
            """
            Returns a dictionary mapping each variable name in this formula to
            its domain name as specified in the associated MLN.
            """
            raise Exception("%s does not implement vardoms()" % str(type(self)))
        
        
        def prednames(self, prednames=None):
            """
            Returns a list of all predicate names used in this formula.
            """
            raise Exception('%s does not implement prednames()' % str(type(self)))
        
        
        def ground(self, mrf, assignment, simplify=False, partial=False):
            """
            Grounds the formula using the given assignment of variables to values/constants and, if given a list in referencedAtoms, 
            fills that list with indices of ground atoms that the resulting ground formula uses
            
            :param mrf:            the :class:`mln.base.MRF` instance
            :param assignment:     mapping of variable names to values
            :param simplify:       whether or not the formula shall be simplified wrt, the evidence
            :param partial:        by default, only complete groundings are allowed. If `partial` is `True`,
                                   the result formula may also contain free variables.
            :returns:              a new formula object instance representing the grounded formula
            """
            raise Exception("%s does not implement ground" % str(type(self)))
        
        
        def copy(self, mln=None, idx=inherit):
            """
            Produces a deep copy of this formula.
            
            If `mln` is specified, the copied formula will be tied to `mln`. If not, it will be tied to the same
            MLN as the original formula is. If `idx` is None, the index of the original formula will be used.
            
            :param mln:     the MLN that the new formula shall be tied to.
            :param idx:     the index of the formula. 
                            If `None`, the index of this formula will be erased to `None`.
                            if `idx` is `auto`, the formula will get a new index from the MLN. 
                            if `idx` is :class:`mln.constants.inherit`, the index from this formula will be inherited to the copy (default). 
            """
            raise Exception('%s does not implement copy()' % str(type(self)))#self._copy(ifnone(mln, self.mln), ifnone(idx, self.idx))


        def vardom(self, varname):
            """
            Returns the domain values of the variable with name `vardom`.
            """
            return self.mln.domains.get(self.vardoms()[varname])


        def cnf(self, level=0):
            """
            Convert to conjunctive normal form.
            """
            return self


        def nnf(self, level=0):
            """
            Convert to negation normal form.
            """
            return self.copy()


        def print_structure(self, world=None, level=0, stream=sys.stdout):
            """
            Prints the structure of the formula to the given `stream`.
            """
            stream.write(''.rjust(level * 4, ' '))
            stream.write('%s: [idx=%s, weight=%s] %s = %s\n' % (repr(self), ifnone(self.idx, '?'), '?' if self.idx is None else self.weight,
                                                                str(self), ifnone(world, '?', lambda mrf: ifnone(self.truth(world), '?'))))
            if hasattr(self, 'children'):
                for child in self.children:
                    child.print_structure(world, level+1, stream)


        def islogical(self):
            return True


        def simplify(self, mrf):
            """
            Simplify the formula by evaluating it with respect to the ground atoms given
            by the evidence in the mrf.
            """
            raise Exception('%s does not implement simplify()' % str(type(self)))


        def literals(self):
            """
            Traverses the formula and returns a generator for the literals it contains.
            """
            if not hasattr(self, 'children'):
                yield self
                return
            else:
                for child in self.children:
                    for lit in child.literals():
                        yield lit


        def expandgrouplits(self):
            #returns list of formulas
            for t in self._ground_template({}):
                yield t


        def truth(self, world):
            """
            Evaluates the formula for its truth wrt. the truth values
            of ground atoms in the possible world `world`.

            :param world:     a vector of truth values representing a possible world.
            :returns:         the truth of the formula in `world` in [0,1] or None if
                              the truth value cannot be determined.
            """
            raise Exception('%s does not implement truth()' % str(type(self)))


        def countgroundings(self, mrf):
            """
            Computes the number of ground formulas based on the domains of free
            variables in this formula. (NB: this does _not_ generate the groundings.)
            """
            gf_count = 1
            for _, dom in self.vardoms().items():
                domain = mrf.domains[dom]
                gf_count *= len(domain)
            return gf_count


        def maxtruth(self, world):
            """
            Returns the maximum truth value of this formula given the evidence.
            For FOL, this is always 1 if the formula is not rendered false by evidence.
            """
            raise Exception('%s does not implement maxtruth()' % self.__class__.__name__)


        def mintruth(self, world):
            """
            Returns the minimum truth value of this formula given the evidence.
            For FOL, this is always 0 if the formula is not rendered true by evidence.
            """
            raise Exception('%s does not implement mintruth()' % self.__class__.__name__)


        def __call__(self, world):
            return self.truth(world)


        def __repr__(self):
            return '<%s: %s>' % (self.__class__.__name__, str(self))

#  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #


    class ComplexFormula(Formula):
        """
        A formula that has other formulas as subelements (children)
        """

        def __init__(self, mln, idx=None):
            Formula.__init__(self, mln, idx)


        def vardoms(self, variables=None, constants=None):
            """
            Get the free (unquantified) variables of the formula in a dict that maps the variable name to the corresp. domain name
            The vars and constants parameters can be omitted.
            If vars is given, it must be a dictionary with already known variables.
            If constants is given, then it must be a dictionary that is to be extended with all constants appearing in the formula;
                it will be a dictionary mapping domain names to lists of constants
            If constants is not given, then constants are not collected, only variables.
            The dictionary of variables is returned.
            """
            if variables is None: variables = defaultdict(set)
            for child in self.children:
                if not hasattr(child, "vardoms"): continue
                variables = child.vardoms(variables, constants)
            return variables


        def constants(self, constants=None):
            """
            Get the constants appearing in the formula in a dict that maps the constant
            name to the domain name the constant belongs to.
            """
            if constants == None: constants = defaultdict
            for child in self.children:
                if not hasattr(child, "constants"): continue
                constants = child.constants(constants)
            return constants


        def ground(self, mrf, assignment, simplify=False, partial=False):
            children = []
            for child in self.children:
                gndchild = child.ground(mrf, assignment, simplify, partial)
                children.append(gndchild)
            gndformula = self.mln.logic.create(type(self), children, mln=self.mln, idx=self.idx)
            if simplify:
                gndformula = gndformula.simplify(mrf.evidence)
            gndformula.idx = self.idx
            return gndformula


        def copy(self, mln=None, idx=inherit):
            children = []
            for child in self.children:
                child_ = child.copy(mln=ifnone(mln, self.mln), idx=None)
                children.append(child_)
            return type(self)(children, mln=ifnone(mln, self.mln), idx=self.idx if idx is inherit else idx)


        def _ground_template(self, assignment):
            variants = [[]]
            for child in self.children:
                child_variants = child._ground_template(assignment)
                new_variants = []
                for variant in variants:
                    for child_variant in child_variants:
                        v = list(variant)
                        v.append(child_variant)
                        new_variants.append(v)
                variants = new_variants
            final_variants = []
            for variant in variants:
                if isinstance(self, Logic.Exist):
                    final_variants.append(self.mln.logic.exist(self.vars, variant[0], mln=self.mln))
                else:
                    final_variants.append(self.mln.logic.create(type(self), variant, mln=self.mln))
            return final_variants


        def template_variables(self, variables=None):
            if variables == None:
                variables = {}
            for child in self.children:
                child.template_variables(variables)
            return variables


        def prednames(self, prednames=None):
            if prednames is None:
                prednames = []
            for child in self.children:
                if not hasattr(child, 'prednames'): continue
                prednames = child.prednames(prednames)
            return prednames


#  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #

    class Conjunction(ComplexFormula):
        """
        Represents a logical conjunction.
        """


        def __init__(self, children, mln, idx=None):
            Formula.__init__(self, mln, idx)
            self.children = children

        @property
        def children(self):
            return self._children

        @children.setter
        def children(self, children):
            if len(children) < 2:
                raise Exception('Conjunction needs at least 2 children.')
            self._children = children


        def __str__(self):
            return ' ^ '.join([('(%s)' % str(c)) if isinstance(c, Logic.ComplexFormula) else str(c) for c in self.children])


        def cstr(self, color=False):
            return ' ^ '.join([('(%s)' % c.cstr(color)) if isinstance(c, Logic.ComplexFormula) else c.cstr(color) for c in self.children])


        def latex(self):
            return ' \land '.join([('(%s)' % c.latex()) if isinstance(c, Logic.ComplexFormula) else c.latex() for c in self.children])


        def maxtruth(self, world):
            mintruth = 1
            for c in self.children:
                truth = c.truth(world)
                if truth is None: continue
                if truth < mintruth: mintruth = truth
            return mintruth


        def mintruth(self, world):
            mintruth = 1
            for c in self.children:
                truth = c.truth(world)
                if truth is None: return 0
                if truth < mintruth: mintruth = truth
            return mintruth


        def cnf(self, level=0):
            clauses = []
            litSets = []
            for child in self.children:
                c = child.cnf(level+1)
                if isinstance(c, Logic.Conjunction): # flatten nested conjunction
                    l = c.children
                else:
                    l = [c]
                for clause in l: # (clause is either a disjunction, a literal or a constant)
                    # if the clause is always true, it can be ignored; if it's always false, then so is the conjunction
                    if isinstance(clause, Logic.TrueFalse):
                        if clause.truth() == 1:
                            continue
                        elif clause.truth() == 0:
                            return self.mln.logic.true_false(0, mln=self.mln, idx=self.idx)
                    # get the set of string literals
                    if hasattr(clause, "children"):
                        litSet = set(map(str, clause.children))
                    else: # unit clause
                        litSet = set([str(clause)])
                    # check if the clause is equivalent to another (subset/superset of the set of literals) -> always keep the smaller one
                    doAdd = True
                    i = 0
                    while i < len(litSets):
                        s = litSets[i]
                        if len(litSet) < len(s):
                            if litSet.issubset(s):
                                del litSets[i]
                                del clauses[i]
                                continue
                        else:
                            if litSet.issuperset(s):
                                doAdd = False
                                break
                        i += 1
                    if doAdd:
                        clauses.append(clause)
                        litSets.append(litSet)
            if not clauses:
                return self.mln.logic.true_false(1, mln=self.mln, idx=self.idx)
            elif len(clauses) == 1:
                return clauses[0].copy(idx=self.idx)
            return self.mln.logic.conjunction(clauses, mln=self.mln, idx=self.idx)


        def nnf(self, level = 0):
            conjuncts = []
            for child in self.children:
                c = child.nnf(level+1)
                if isinstance(c, Logic.Conjunction): # flatten nested conjunction
                    conjuncts.extend(c.children)
                else:
                    conjuncts.append(c)
            return self.mln.logic.conjunction(conjuncts, mln=self.mln, idx=self.idx)


#  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #

    class Disjunction(ComplexFormula):
        """
        Represents a disjunction of formulas.
        """


        def __init__(self, children, mln, idx=None):
            Formula.__init__(self, mln, idx)
            self.children = children


        @property
        def children(self):
            """
            A list of disjuncts.
            """
            return self._children


        @children.setter
        def children(self, children):
            if len(children) < 2:
                raise Exception('Disjunction needs at least 2 children.')
            self._children = children


        def __str__(self):
            return ' v '.join([('(%s)' % str(c)) if isinstance(c, Logic.ComplexFormula) else str(c) for c in self.children])


        def cstr(self, color=False):
            return ' v '.join([('(%s)' % c.cstr(color)) if isinstance(c, Logic.ComplexFormula) else c.cstr(color) for c in self.children])


        def latex(self):
            return ' \lor '.join([('(%s)' % c.latex()) if isinstance(c, Logic.ComplexFormula) else c.latex() for c in self.children])

        def maxtruth(self, world):
            maxtruth = 0
            for c in self.children:
                truth = c.truth(world)
                if truth is None: return 1
                if truth > maxtruth: maxtruth = truth
            return maxtruth


        def mintruth(self, world):
            maxtruth = 0
            for c in self.children:
                truth = c.truth(world)
                if truth is None: continue
                if truth > maxtruth: maxtruth = truth
            return maxtruth


        def cnf(self, level=0):
            disj = []
            conj = []
            # convert children to CNF and group by disjunction/conjunction; flatten nested disjunction, remove duplicates, check for tautology
            for child in self.children:
                c = child.cnf(level+1) # convert child to CNF -> must be either conjunction of clauses, disjunction of literals, literal or boolean constant
                if isinstance(c, Logic.Conjunction):
                    conj.append(c)
                else:
                    if isinstance(c, Logic.Disjunction):
                        lits = c.children
                    else: # literal or boolean constant
                        lits = [c]
                    for l in lits:
                        # if the literal is always true, the disjunction is always true; if it's always false, it can be ignored
                        if isinstance(l, Logic.TrueFalse):
                            if l.truth():
                                return self.mln.logic.true_false(1, mln=self.mln, idx=self.idx)
                            else: continue
                        # it's a regular literal: check if the negated literal is already among the disjuncts
                        l_ = l.copy()
                        l_.negated = True
                        if l_ in disj:
                            return self.mln.logic.true_false(1, mln=self.mln, idx=self.idx)
                        # check if the literal itself is not already there and if not, add it
                        if l not in disj: disj.append(l)
            # if there are no conjunctions, this is a flat disjunction or unit clause
            if not conj:
                if len(disj) >= 2:
                    return self.mln.logic.disjunction(disj, mln=self.mln, idx=self.idx)
                else:
                    return disj[0].copy()
            # there are conjunctions among the disjuncts
            # if there is only one conjunction and no additional disjuncts, we are done
            if len(conj) == 1 and not disj: return conj[0].copy()
            # otherwise apply distributivity
            # use the first conjunction to distribute: (C_1 ^ ... ^ C_n) v RD = (C_1 v RD) ^ ... ^  (C_n v RD)
            # - C_i = conjuncts[i]
            conjuncts = conj[0].children
            # - RD = disjunction of the elements in remaining_disjuncts (all the original disjuncts except the first conjunction)
            remaining_disjuncts = disj + conj[1:]
            # - create disjunctions
            disj = []
            for c in conjuncts:
                disj.append(self.mln.logic.disjunction([c] + remaining_disjuncts, mln=self.mln, idx=self.idx))
            return self.mln.logic.conjunction(disj, mln=self.mln, idx=self.idx).cnf(level + 1)


        def nnf(self, level = 0):
            disjuncts = []
            for child in self.children:
                c = child.nnf(level+1)
                if isinstance(c, Logic.Disjunction): # flatten nested disjunction
                    disjuncts.extend(c.children)
                else:
                    disjuncts.append(c)
            return self.mln.logic.disjunction(disjuncts, mln=self.mln, idx=self.idx)


#  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #


    class Lit(Formula):
        """
        Represents a literal.
        """

        def __init__(self, negated, predname, args, mln, idx=None):
            Formula.__init__(self, mln, idx)
            self.negated = negated
            self.predname = predname
            self.args = list(args)


        @property
        def negated(self):
            return self._negated


        @negated.setter
        def negated(self, value):
            self._negated = value


        @property
        def predname(self):
            return self._predname


        @predname.setter
        def predname(self, predname):
            if self.mln is not None and self.mln.predicate(predname) is None:
            # if self.mln is not None and any(self.mln.predicate(p) is None for p in predname):
                raise NoSuchPredicateError('Predicate %s is undefined.' % predname)
            self._predname = predname


        @property
        def args(self):
            return self._args


        @args.setter
        def args(self, args):
            if self.mln is not None and len(args) != len(self.mln.predicate(self.predname).argdoms):
                raise Exception('Illegal argument length: %s. %s requires %d arguments: %s' % (str(args), self.predname,
                                                                                               len(self.mln.predicate(self.predname).argdoms),
                                                                                               self.mln.predicate(self.predname).argdoms))
            self._args = args


        def __str__(self):
            return {True:'!', False:'', 2: '*'}[self.negated] + self.predname + "(" + ",".join(self.args) + ")"


        def cstr(self, color=False):
            return {True:"!", False:"", 2:'*'}[self.negated] + colorize(self.predname, predicate_color, color) + "(" + ",".join(self.args) + ")"


        def latex(self):
            return {True:r'\lnot ', False:'', 2: '*'}[self.negated] + latexsym(self.predname) + "(" + ",".join(map(latexsym, self.args)) + ")"


        def vardoms(self, variables=None, constants=None):
            if variables == None:
                variables = {}
            argdoms = self.mln.predicate(self.predname).argdoms
            if len(argdoms) != len(self.args):
                raise Exception("Wrong number of parameters in '%s'; expected %d!" % (str(self), len(argdoms)))
            for i, arg in enumerate(self.args):
                if self.mln.logic.isvar(arg):
                    varname = arg
                    domain = argdoms[i]
                    if varname in variables and variables[varname] != domain and variables[varname] is not None:
                        raise Exception("Variable '%s' bound to more than one domain: %s" % (varname, str((variables[varname], domain))))
                    variables[varname] = domain
                elif constants is not None:
                    domain = argdoms[i]
                    if domain not in constants: constants[domain] = []
                    constants[domain].append(arg)
            return variables


        def template_variables(self, variables=None):
            if variables == None: variables = {}
            for i, arg in enumerate(self.args):
                if self.mln.logic.istemplvar(arg):
                    varname = arg
                    pred = self.mln.predicate(self.predname)
                    domain = pred.argdoms[i]
                    if varname in variables and variables[varname] != domain:
                        raise Exception("Variable '%s' bound to more than one domain" % varname)
                    variables[varname] = domain
            return variables


        def prednames(self, prednames=None):
            if prednames is None:
                prednames = []
            if self.predname not in prednames:
                prednames.append(self.predname)
            return prednames


        def ground(self, mrf, assignment, simplify=False, partial=False):
            args = [assignment.get(x, x) for x in self.args]
            if not any(map(self.mln.logic.isvar, args)):
                atom = "%s(%s)" % (self.predname, ",".join(args))
                gndatom = mrf.gndatom(atom)
                if gndatom is None:
                    raise Exception('Could not ground "%s". This atom is not among the ground atoms.' % atom)
                # simplify if necessary
                if simplify and gndatom.truth(mrf.evidence) is not None:
                    truth = gndatom.truth(mrf.evidence)
                    if self.negated: truth = 1 - truth
                    return self.mln.logic.true_false(truth, mln=self.mln, idx=self.idx)
                gndformula = self.mln.logic.gnd_lit(gndatom, self.negated, mln=self.mln, idx=self.idx)
                return gndformula
            else:
                if partial:
                    return self.mln.logic.lit(self.negated, self.predname, args, mln=self.mln, idx=self.idx)
                if any([self.mln.logic.isvar(arg) for arg in args]):
                    raise Exception('Partial formula groundings are not allowed. Consider setting partial=True if desired.')
                else:
                    print("\nground atoms:")
                    mrf.print_gndatoms()
                    raise Exception("Could not ground formula containing '%s' - this atom is not among the ground atoms (see above)." % self.predname)


        def _ground_template(self, assignment):
            args = [assignment.get(x, x) for x in self.args]
            if self.negated == 2: # template
                return [self.mln.logic.lit(False, self.predname, args, mln=self.mln), self.mln.logic.lit(True, self.predname, args, mln=self.mln)]
            else:
                return [self.mln.logic.lit(self.negated, self.predname, args, mln=self.mln)]


        def copy(self, mln=None, idx=inherit):
            return self.mln.logic.lit(self.negated, self.predname, self.args, mln=ifnone(mln, self.mln), idx=self.idx if idx is inherit else idx)


        def truth(self, world):
            return None
#             raise Exception('Literals do not have a truth value. Ground the literal first.')


        def mintruth(self, world):
            raise Exception('Literals do not have a truth value. Ground the literal first.')


        def maxtruth(self, world):
            raise Exception('Literals do not have a truth value. Ground the literal first.')


        def constants(self, constants=None):
            if constants is None: constants = {}
            for i, c in enumerate(self.params):
                domname = self.mln.predicate(self.predname).argdoms[i]
                values = constants.get(domname, None)
                if values is None:
                    values = []
                    constants[domname] = values
                if not self.mln.logic.isvar(c) and not c in values: values.append(c)
            return constants


        def simplify(self, world):
            return self.mln.logic.lit(self.negated, self.predname, self.args, mln=self.mln, idx=self.idx)


        def __eq__(self, other):
            return str(self) == str(other)


        def __ne__(self, other):
            return not self == other


#  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #


    class LitGroup(Formula):
        """
        Represents a group of literals with identical arguments.
        """

        def __init__(self, negated, predname, args, mln, idx=None):
            Formula.__init__(self, mln, idx)
            self.negated = negated
            self.predname = predname
            self.args = list(args)


        @property
        def negated(self):
            return self._negated


        @negated.setter
        def negated(self, value):
            self._negated = value


        @property
        def predname(self):
            return self._predname


        @predname.setter
        def predname(self, prednames):
            """
            predname is a list of predicate names, of which each is tested if it is None
            """
            if self.mln is not None and any(self.mln.predicate(p) is None for p in prednames):
                erroneouspreds = [p for p in prednames if self.mln.predicate(p) is None]
                raise NoSuchPredicateError('Predicate{} {} is undefined.'.format('s' if len(erroneouspreds) > 1 else '', ', '.join(erroneouspreds)))
            self._predname = prednames


        @property
        def lits(self):
            return [Lit(self.negated, lit, self.args, self.mln) for lit in self.predname]


        @property
        def args(self):
            return self._args


        @args.setter
        def args(self, args):
            # arguments are identical for all predicates in group, so choose
            # arbitrary predicate
            predname = self.predname[0]
            if self.mln is not None and len(args) != len(self.mln.predicate(predname).argdoms):
                raise Exception('Illegal argument length: %s. %s requires %d arguments: %s' % (str(args), predname,
                                                                                               len(self.mln.predicate(predname).argdoms),
                                                                                               self.mln.predicate(predname).argdoms))
            self._args = args


        def __str__(self):
            return {True:'!', False:'', 2: '*'}[self.negated] + '|'.join(self.predname) + "(" + ",".join(self.args) + ")"


        def cstr(self, color=False):
            return {True:"!", False:"", 2:'*'}[self.negated] + colorize('|'.join(self.predname), predicate_color, color) + "(" + ",".join(self.args) + ")"


        def latex(self):
            return {True:r'\lnot ', False:'', 2: '*'}[self.negated] + latexsym('|'.join(self.predname)) + "(" + ",".join(map(latexsym, self.args)) + ")"


        def vardoms(self, variables=None, constants=None):
            if variables == None:
                variables = {}
            argdoms = self.mln.predicate(self.predname[0]).argdoms
            if len(argdoms) != len(self.args):
                raise Exception("Wrong number of parameters in '%s'; expected %d!" % (str(self), len(argdoms)))
            for i, arg in enumerate(self.args):
                if self.mln.logic.isvar(arg):
                    varname = arg
                    domain = argdoms[i]
                    if varname in variables and variables[varname] != domain and variables[varname] is not None:
                        raise Exception("Variable '%s' bound to more than one domain" % varname)
                    variables[varname] = domain
                elif constants is not None:
                    domain = argdoms[i]
                    if domain not in constants: constants[domain] = []
                    constants[domain].append(arg)
            return variables


        def template_variables(self, variables=None):
            if variables == None: variables = {}
            for i, arg in enumerate(self.args):
                if self.mln.logic.istemplvar(arg):
                    varname = arg
                    pred = self.mln.predicate(self.predname[0])
                    domain = pred.argdoms[i]
                    if varname in variables and variables[varname] != domain:
                        raise Exception("Variable '%s' bound to more than one domain" % varname)
                    variables[varname] = domain
            return variables


        def prednames(self, prednames=None):
            if prednames is None:
                prednames = []
            prednames.extend([p for p in self.predname if p not in prednames])
            return prednames


        def _ground_template(self, assignment):
            # args = map(lambda x: assignment.get(x, x), self.args)
            if self.negated == 2: # template
                return [self.mln.logic.lit(False, predname, self.args, mln=self.mln) for predname in self.predname] + \
                       [self.mln.logic.lit(True, predname, self.args, mln=self.mln) for predname in self.predname]
            else:
                return [self.mln.logic.lit(self.negated, predname, self.args, mln=self.mln) for predname in self.predname]

        def copy(self, mln=None, idx=inherit):
            return self.mln.logic.litgroup(self.negated, self.predname, self.args, mln=ifnone(mln, self.mln), idx=self.idx if idx is inherit else idx)


        def truth(self, world):
            return None


        def mintruth(self, world):
            raise Exception('LitGroups do not have a truth value. Ground the literal first.')


        def maxtruth(self, world):
            raise Exception('LitGroups do not have a truth value. Ground the literal first.')


        def constants(self, constants=None):
            if constants is None: constants = {}
            for i, c in enumerate(self.params):
                # domname = self.mln.predicate(self.predname).argdoms[i]
                domname = self.mln.predicate(self.predname[0]).argdoms[i]
                values = constants.get(domname, None)
                if values is None:
                    values = []
                    constants[domname] = values
                if not self.mln.logic.isvar(c) and not c in values: values.append(c)
            return constants


        def simplify(self, world):
            return self.mln.logic.litgroup(self.negated, self.predname, self.args, mln=self.mln, idx=self.idx)


        def __eq__(self, other):
            return str(self) == str(other)


        def __ne__(self, other):
            return not self == other


#  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #


    class GroundLit(Formula):
        """
        Represents a ground literal.
        """


        def __init__(self, gndatom, negated, mln, idx=None):
            Formula.__init__(self, mln, idx)
            self.gndatom = gndatom
            self.negated = negated


        @property
        def gndatom(self):
            return self._gndatom


        @gndatom.setter
        def gndatom(self, gndatom):
            self._gndatom = gndatom


        @property
        def negated(self):
            return self._negated


        @negated.setter
        def negated(self, negate):
            self._negated = negate


        @property
        def predname(self):
            return self.gndatom.predname

        @property
        def args(self):
            return self.gndatom.args


        def truth(self, world):
            tv = self.gndatom.truth(world)
            if tv is None: return None
            if self.negated: return (1. - tv)
            return tv


        def mintruth(self, world):
            truth = self.truth(world)
            if truth is None: return 0
            else: return truth


        def maxtruth(self, world):
            truth = self.truth(world)
            if truth is None: return 1
            else: return truth


        def __str__(self):
            return {True:"!", False:""}[self.negated] + str(self.gndatom)


        def cstr(self, color=False):
            return {True:"!", False:""}[self.negated] + self.gndatom.cstr(color)


        def contains_gndatom(self, atomidx):
            return (self.gndatom.idx == atomidx)


        def vardoms(self, variables=None, constants=None):
            return self.gndatom.vardoms(variables, constants)


        def constants(self, constants=None):
            if constants is None: constants = {}
            for i, c in enumerate(self.gndatom.args):
                domname = self.mln.predicates[self.gndatom.predname][i]
                values = constants.get(domname, None)
                if values is None:
                    values = []
                    constants[domname] = values
                if not c in values: values.append(c)
            return constants


        def gndatom_indices(self, l=None):
            if l == None: l = []
            if self.gndatom.idx not in l: l.append(self.gndatom.idx)
            return l


        def gndatoms(self, l=None):
            if l == None: l = []
            if not self.gndatom in l: l.append(self.gndatom)
            return l


        def ground(self, mrf, assignment, simplify=False, partial=False):
            # always get the gnd atom from the mrf, so that
            # formulas can be transferred between different MRFs
            return self.mln.logic.gnd_lit(mrf.gndatom(str(self.gndatom)), self.negated, mln=self.mln, idx=self.idx)


        def copy(self, mln=None, idx=inherit):
            mln = ifnone(mln, self.mln)
            if mln is not self.mln:
                raise Exception('GroundLit cannot be copied among MLNs.')
            return self.mln.logic.gnd_lit(self.gndatom, self.negated, mln=ifnone(mln, self.mln), idx=self.idx if idx is inherit else idx)


        def simplify(self, world):
            truth = self.truth(world)
            if truth is not None:
                return self.mln.logic.true_false(truth, mln=self.mln, idx=self.idx)
            return self.mln.logic.gnd_lit(self.gndatom, self.negated, mln=self.mln, idx=self.idx)


        def prednames(self, prednames=None):
            if prednames is None:
                prednames = []
            if self.gndatom.predname not in prednames:
                prednames.append(self.gndatom.predname)
            return prednames


        def template_variables(self, variables=None):
            return {}


        def _ground_template(self, assignment):
            return [self.mln.logic.gnd_lit(self.gndatom, self.negated, mln=self.mln)]


        def __eq__(self, other):
            return str(self) == str(other)#self.negated == other.negated and self.gndAtom == other.gndAtom


        def __ne__(self, other):
            return not self == other


#  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #


    class GroundAtom:
        """
        Represents a ground atom.
        """

        def __init__(self, predname, args, mln, idx=None):
            self.predname = predname
            self.args = args
            self.idx = idx
            self.mln = mln


        @property
        def predname(self):
            return self._predname


        @predname.setter
        def predname(self, predname):
            self._predname = predname


        @property
        def args(self):
            return self._args


        @args.setter
        def args(self, args):
            self._args = args


        @property
        def idx(self):
            return self._idx


        @idx.setter
        def idx(self, idx):
            self._idx = idx


        def truth(self, world):
            return world[self.idx]


        def mintruth(self, world):
            truth = self.truth(world)
            if truth is None: return 0
            else: return truth


        def maxtruth(self, world):
            truth = self.truth(world)
            if truth is None: return 1
            else: return truth


        def __repr__(self):
            return '<GroundAtom: %s>' % str(self)


        def __str__(self):
            return "%s(%s)" % (self.predname, ",".join(self.args))


        def cstr(self, color=False):
            return "%s(%s)" % (colorize(self.predname, predicate_color, color), ",".join(self.args))


        def prednames(self, prednames=None):
            if prednames is None:
                prednames = []
            if self.predname not in prednames:
                prednames.append(self.predname)
            return prednames


        def vardoms(self, variables=None, constants=None):
            if variables is None:
                variables = {}
            if constants is None:
                constants = {}
            for d, c in zip(self.args, self.mln.predicate(self.predname).argdoms):
                if d not in constants:
                    constants[d] = []
                if c not in constants[d]:
                    constants[d].append(c)
            return variables


        def __eq__(self, other):
            return str(self) == str(other)

        def __ne__(self, other):
            return not self == other


#  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #


    class Equality(ComplexFormula):
        """
        Represents (in)equality constraints between two symbols.
        """


        def __init__(self, args, negated, mln, idx=None):
            ComplexFormula.__init__(self, mln, idx)
            self.args = args
            self.negated = negated


        @property
        def args(self):
            return self._args


        @args.setter
        def args(self, args):
            if len(args) != 2:
                raise Exception('Illegal number of aeguments of equality: %d' % len(args))
            self._args = args


        @property
        def negated(self):
            return self._negated

        @negated.setter
        def negated(self, negate):
            self._negated = negate


        def __str__(self):
            return "%s%s%s" % (str(self.args[0]), '=/=' if self.negated else '=', str(self.args[1]))


        def cstr(self, color=False):
            return str(self)


        def latex(self):
            return "%s%s%s" % (latexsym(self.args[0]), r'\neq ' if self.negated else '=', latexsym(self.args[1]))


        def ground(self, mrf, assignment, simplify=False, partial=False):
            # if the parameter is a variable, do a lookup (it must be bound by now),
            # otherwise it's a constant which we can use directly
            args = [assignment.get(x, x) for x in self.args]
            if self.mln.logic.isvar(args[0]) or self.mln.logic.isvar(args[1]):
                if partial:
                    return self.mln.logic.equality(args, self.negated, mln=self.mln)
                else: raise Exception("At least one variable was not grounded in '%s'!" % str(self))
            if simplify:
                equal = (args[0] == args[1])
                return self.mln.logic.true_false(1 if {True: not equal, False: equal}[self.negated] else 0, mln=self.mln, idx=self.idx)
            else:
                return self.mln.logic.equality(args, self.negated, mln=self.mln, idx=self.idx)


        def copy(self, mln=None, idx=inherit):
            return self.mln.logic.equality(self.args, self.negated, mln=ifnone(mln, self.mln), idx=self.idx if idx is inherit else idx)


        def _ground_template(self, assignment):
            return [self.mln.logic.equality(self.args, negated=self.negated, mln=self.mln)]


        def template_variables(self, variables=None):
            return variables


        def vardoms(self, variables=None, constants=None):
            if variables is None:
                variables = {}
            if self.mln.logic.isvar(self.args[0]) and self.args[0] not in variables: variables[self.args[0]] = None
            if self.mln.logic.isvar(self.args[1]) and self.args[1] not in variables: variables[self.args[1]] = None
            return variables


        def vardom(self, varname):
            return None


        def vardomain_from_formula(self, formula):
            f_var_domains = formula.vardoms()
            eq_vars = self.vardoms()
            for var_ in eq_vars:
                if var_ not in f_var_domains:
                    raise Exception('Variable %s not bound to a domain by formula %s' % (var_, fstr(formula)))
                eq_vars[var_] = f_var_domains[var_]
            return eq_vars


        def prednames(self, prednames=None):
            if prednames is None:
                prednames = []
            return prednames


        def truth(self, world=None):
            if any(map(self.mln.logic.isvar, self.args)):
                return None
            equals = 1 if (self.args[0] == self.args[1]) else 0
            return (1 - equals) if self.negated else equals


        def maxtruth(self, world):
            truth = self.truth(world)
            if truth is None: return 1
            else: return truth


        def mintruth(self, world):
            truth = self.truth(world)
            if truth is None: return 0
            else: return truth


        def simplify(self, world):
            truth = self.truth(world)
            if truth != None: return self.mln.logic.true_false(truth, mln=self.mln, idx=self.idx)
            return self.mln.logic.equality(list(self.args), negated=self.negated, mln=self.mln, idx=self.idx)


#  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #


    class Implication(ComplexFormula):
        """
        Represents an implication
        """


        def __init__(self, children, mln, idx=None):
            Formula.__init__(self, mln, idx)
            self.children = children

        @property
        def children(self):
            return self._children

        @children.setter
        def children(self, children):
            if len(children) != 2:
                raise Exception('Implication needs exactly 2 children (antescedant and consequence)')
            self._children = children


        def __str__(self):
            c1 = self.children[0]
            c2 = self.children[1]
            return (str(c1) if not isinstance(c1, Logic.ComplexFormula) \
                else '(%s)' % str(c1)) + " => " + (str(c2) if not isinstance(c2, Logic.ComplexFormula) else '(%s)' % str(c2))


        def cstr(self, color=False):
            c1 = self.children[0]
            c2 = self.children[1]
            (s1, s2) = (c1.cstr(color), c2.cstr(color))
            (s1, s2) = (('(%s)' if isinstance(c1, Logic.ComplexFormula) else '%s') % s1, ('(%s)' if isinstance(c2, Logic.ComplexFormula) else '%s') % s2)
            return '%s => %s' % (s1, s2)


        def latex(self):
            return self.children[0].latex() + r" \rightarrow " + self.children[1].latex()


        def cnf(self, level=0):
            return self.mln.logic.disjunction([self.mln.logic.negation([self.children[0]], mln=self.mln, idx=self.idx), self.children[1]], mln=self.mln, idx=self.idx).cnf(level+1)


        def nnf(self, level=0):
            return self.mln.logic.disjunction([self.mln.logic.negation([self.children[0]], mln=self.mln, idx=self.idx), self.children[1]], mln=self.mln, idx=self.idx).nnf(level+1)


        def simplify(self, world):
            return self.mln.logic.disjunction([Negation([self.children[0]], mln=self.mln, idx=self.idx), self.children[1]], mln=self.mln, idx=self.idx).simplify(world)


#  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #


    class Biimplication(ComplexFormula):
        """
        Represents a bi-implication.
        """


        def __init__(self, children, mln, idx=None):
            Formula.__init__(self, mln, idx)
            self.children = children


        @property
        def children(self):
            return self._children


        @children.setter
        def children(self, children):
            if len(children) != 2:
                raise Exception('Biimplication needs exactly 2 children')
            self._children = children


        def __str__(self):
            c1 = self.children[0]
            c2 = self.children[1]
            return (str(c1) if not isinstance(c1, Logic.ComplexFormula) \
                else '(%s)' % str(c1)) + " <=> " + (str(c2) if not isinstance(c2, Logic.ComplexFormula) else str(c2))


        def cstr(self, color=False):
            c1 = self.children[0]
            c2 = self.children[1]
            (s1, s2) = (c1.cstr(color), c2.cstr(color))
            (s1, s2) = (('(%s)' if isinstance(c1, Logic.ComplexFormula) else '%s') % s1, ('(%s)' if isinstance(c2, Logic.ComplexFormula) else '%s') % s2)
            return '%s <=> %s' % (s1, s2)


        def latex(self):
            return r'%s \leftrightarrow %s' % (self.children[0].latex(), self.children[1].latex())


        def cnf(self, level=0):
            cnf = self.mln.logic.conjunction([self.mln.logic.implication([self.children[0], self.children[1]], mln=self.mln, idx=self.idx),
                                self.mln.logic.implication([self.children[1], self.children[0]], mln=self.mln, idx=self.idx)], mln=self.mln, idx=self.idx)
            return cnf.cnf(level+1)


        def nnf(self, level = 0):
            return self.mln.logic.conjunction([self.mln.logic.implication([self.children[0], self.children[1]], mln=self.mln, idx=self.idx),
                                self.mln.logic.implication([self.children[1], self.children[0]], mln=self.mln, idx=self.idx)], mln=self.mln, idx=self.idx).nnf(level+1)


        def simplify(self, world):
            c1 = self.mln.logic.disjunction([self.mln.logic.negation([self.children[0]], mln=self.mln), self.children[1]], mln=self.mln)
            c2 = self.mln.logic.disjunction([self.children[0], self.mln.logic.negation([self.children[1]], mln=self.mln)], mln=self.mln)
            return self.mln.logic.conjunction([c1,c2], mln=self.mln, idx=self.idx).simplify(world)


#  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #


    class Negation(ComplexFormula):
        """
        Represents a negation of a complex formula.
        """

        def __init__(self, children, mln, idx=None):
            ComplexFormula.__init__(self, mln, idx)
            if hasattr(children, '__iter__'):
                assert len(children) == 1
            else:
                children = [children]
            self.children = children


        @property
        def children(self):
            return self._children

        @children.setter
        def children(self, children):
            if hasattr(children, '__iter__'):
                if len(children) != 1:
                    raise Exception('Negation may have only 1 child.')
            else:
                children = [children]
            self._children = children


        def __str__(self):
            return ('!(%s)' if isinstance(self.children[0], Logic.ComplexFormula) else '!%s') % str(self.children[0])


        def cstr(self, color=False):
            return ('!(%s)' if isinstance(self.children[0], Logic.ComplexFormula) else '!%s') % self.children[0].cstr(color)


        def latex(self):
            return r'\lnot (%s)' % self.children[0].latex()


        def truth(self, world):
            childValue = self.children[0].truth(world)
            if childValue is None:
                return None
            return 1 - childValue


        def cnf(self, level=0):
            # convert the formula that is negated to negation normal form (NNF),
            # so that if it's a complex formula, it will be either a disjunction
            # or conjunction, to which we can then apply De Morgan's law.
            # Note: CNF conversion would be unnecessarily complex, and,
            # when the children are negated below, most of it would be for nothing!
            child = self.children[0].nnf(level+1)
            # apply negation to child (pull inwards)
            if hasattr(child, 'children'):
                neg_children = []
                for c in child.children:
                    neg_children.append(self.mln.logic.negation([c], mln=self.mln, idx=None).cnf(level+1))
                if isinstance(child, Logic.Conjunction):
                    return self.mln.logic.disjunction(neg_children, mln=self.mln, idx=self.idx).cnf(level+1)
                elif isinstance(child, Logic.Disjunction):
                    return self.mln.logic.conjunction(neg_children, mln=self.mln, idx=self.idx).cnf(level+1)
                elif isinstance(child, Logic.Negation):
                    return c.cnf(level+1)
                else:
                    raise Exception("Unexpected child type %s while converting '%s' to CNF!" % (str(type(child)), str(self)))
            elif isinstance(child, Logic.Lit):
                return self.mln.logic.lit(not child.negated, child.predname, child.args, mln=self.mln, idx=self.idx)
            elif isinstance(child, Logic.LitGroup):
                return self.mln.logic.litgroup(not child.negated, child.predname, child.args, mln=self.mln, idx=self.idx)
            elif isinstance(child, Logic.GroundLit):
                return self.mln.logic.gnd_lit(child.gndatom, not child.negated, mln=self.mln, idx=self.idx)
            elif isinstance(child, Logic.TrueFalse):
                return self.mln.logic.true_false(1 - child.value, mln=self.mln, idx=self.idx)
            elif isinstance(child, Logic.Equality):
                return self.mln.logic.equality(child.params, not child.negated, mln=self.mln, idx=self.idx)
            else:
                raise Exception("CNF conversion of '%s' failed (type:%s)" % (str(self), str(type(child))))


        def nnf(self, level = 0):
            # child is the formula that is negated
            child = self.children[0].nnf(level+1)
            # apply negation to the children of the formula that is negated (pull inwards)
            # - complex formula (should be disjunction or conjunction at this point), use De Morgan's law
            if hasattr(child, 'children'):
                neg_children = []
                for c in child.children:
                    neg_children.append(self.mln.logic.negation([c], mln=self.mln, idx=None).nnf(level+1))
                if isinstance(child, Logic.Conjunction): # !(A ^ B) = !A v !B
                    return self.mln.logic.disjunction(neg_children, mln=self.mln, idx=self.idx).nnf(level+1)
                elif isinstance(child, Logic.Disjunction): # !(A v B) = !A ^ !B
                    return self.mln.logic.conjunction(neg_children, mln=self.mln, idx=self.idx).nnf(level+1)
                elif isinstance(child, Logic.Negation):
                    return c.nnf(level+1)
                # !(A => B) = A ^ !B
                # !(A <=> B) = (A ^ !B) v (B ^ !A)
                else:
                    raise Exception("Unexpected child type %s while converting '%s' to NNF!" % (str(type(child)), str(self)))
            # - non-complex formula, i.e. literal or constant
            elif isinstance(child, Logic.Lit):
                return self.mln.logic.lit(not child.negated, child.predname, child.args, mln=self.mln, idx=self.idx)
            elif isinstance(child, Logic.LitGroup):
                return self.mln.logic.litgroup(not child.negated, child.predname, child.args, mln=self.mln, idx=self.idx)
            elif isinstance(child, Logic.GroundLit):
                return self.mln.logic.gnd_lit(child.gndatom, not child.negated, mln=self.mln, idx=self.idx)
            elif isinstance(child, Logic.TrueFalse):
                return self.mln.logic.true_false(1 - child.value, mln=self.mln, idx=self.idx)
            elif isinstance(child, Logic.Equality):
                return self.mln.logic.equality(child.args, not child.negated, mln=self.mln, idx=self.idx)
            else:
                raise Exception("NNF conversion of '%s' failed (type:%s)" % (str(self), str(type(child))))


        def simplify(self, world):
            f = self.children[0].simplify(world)
            if isinstance(f, Logic.TrueFalse):
                return f.invert()
            else:
                return self.mln.logic.negation([f], mln=self.mln, idx=self.idx)


#  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #


    class Exist(ComplexFormula):
        """
        Existential quantifier.
        """


        def __init__(self, variables, formula, mln, idx=None):
            Formula.__init__(self, mln, idx)
            self.formula = formula
            self.vars = variables


        @property
        def children(self):
            return self._children

        @children.setter
        def children(self, children):
            if len(children) != 1:
                raise Exception('Illegal number of formulas in Exist: %s' % str(children))
            self._children = children


        @property
        def formula(self):
            return self._children[0]

        @formula.setter
        def formula(self, f):
            self._children = [f]

        @property
        def vars(self):
            return self._vars

        @vars.setter
        def vars(self, v):
            self._vars = v


        def __str__(self):
            return 'EXIST %s (%s)' % (', '.join(self.vars), str(self.formula))


        def cstr(self, color=False):
            return colorize('EXIST ', predicate_color, color) + ', '.join(self.vars) + ' (' + self.formula.cstr(color) + ')'


        def latex(self):
            return '\exists\ %s (%s)' % (', '.join(map(latexsym, self.vars)), self.formula.latex())


        def vardoms(self, variables=None, constants=None):
            if variables == None:
                variables = {}
            # get the child's variables:
            newvars = self.formula.vardoms(None, constants)
            # remove the quantified variable(s)
            for var in self.vars:
                try: del newvars[var]
                except:
                    raise Exception("Variable '%s' in '%s' not bound to a domain!" % (var, str(self)))
            # add the remaining ones that are not None and return
            variables.update(dict([(k, v) for k, v in newvars.items() if v is not None]))
            return variables


        def ground(self, mrf, assignment, partial=False, simplify=False):
            # find out variable domains
            vardoms = self.formula.vardoms()
            if not set(self.vars).issubset(vardoms):
                raise Exception('One or more variables do not appear in formula: %s' % str(set(self.vars).difference(vardoms)))
            variables = dict([(k,v) for k,v in vardoms.items() if k in self.vars])
            # ground
            gndings = []
            self._ground(self.children[0], variables, assignment, gndings, mrf, partial=partial)
            if len(gndings) == 1:
                return gndings[0]
            if not gndings:
                return self.mln.logic.true_false(0, mln=self.mln, idx=self.idx)
            disj = self.mln.logic.disjunction(gndings, mln=self.mln, idx=self.idx)
            if simplify:
                return disj.simplify(mrf.evidence)
            else:
                return disj


        def _ground(self, formula, variables, assignment, gndings, mrf, partial=False):
            # if all variables have been grounded...
            if variables == {}:
                gndFormula = formula.ground(mrf, assignment, partial=partial)
                gndings.append(gndFormula)
                return
            # ground the first variable...
            varname,domname = variables.popitem()
            for value in mrf.domains[domname]: # replacing it with one of the constants
                assignment[varname] = value
                # recursive descent to ground further variables
                self._ground(formula, dict(variables), assignment, gndings, mrf, partial=partial)


        def copy(self, mln=None, idx=inherit):
            return self.mln.logic.exist(self.vars, self.formula, mln=ifnone(mln, self.mln), idx=self.idx if idx is inherit else idx)


        def cnf(self,l=0):
            raise Exception("'%s' cannot be converted to CNF. Ground this formula first!" % str(self))


        def truth(self, w):
            raise Exception("'%s' does not implement truth()" % self.__class__.__name__)


#  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #


    class TrueFalse(Formula):
        """
        Represents constant truth values.
        """

        def __init__(self, truth, mln, idx=None):
            Formula.__init__(self, mln, idx)
            self.value = truth

        @property
        def value(self):
            return self._value

        def cstr(self, color=False):
            return str(self)

        def truth(self, world=None):
            return self.value

        def mintruth(self, world=None):
            return self.truth

        def maxtruth(self, world=None):
            return self.truth

        def invert(self):
            return self.mln.logic.true_false(1 - self.truth(), mln=self.mln, idx=self.idx)

        def simplify(self, world):
            return self.copy()

        def vardoms(self, variables=None, constants=None):
            if variables is None:
                variables = {}
            return variables

        def ground(self, mln, assignment, simplify=False, partial=False):
            return self.mln.logic.true_false(self.value, mln=self.mln, idx=self.idx)

        def copy(self, mln=None, idx=inherit):
            return self.mln.logic.true_false(self.value, mln=ifnone(mln, self.mln), idx=self.idx if idx is inherit else idx)


#  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #


    class NonLogicalConstraint(Constraint):
        """
        A constraint that is not somehow made up of logical connectives and (ground) atoms.
        """

        def template_variants(self, mln):
            # non logical constraints are never templates; therefore, there is just one variant, the constraint itself
            return [self]

        def islogical(self):
            return False

        def negate(self):
            raise Exception("%s does not implement negate()" % str(type(self)))


#  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #


    class CountConstraint(NonLogicalConstraint):
        """
        A constraint that tests the number of relation instances against an integer.
        """

        def __init__(self, predicate, predicate_params, fixed_params, op, count):
            """op: an operator; one of "=", "<=", ">=" """
            self.literal = self.mln.logic.lit(False, predicate, predicate_params)
            self.fixed_params = fixed_params
            self.count = count
            if op == "=": op = "=="
            self.op = op

        def __str__(self):
            op = self.op
            if op == "==": op = "="
            return "count(%s | %s) %s %d" % (str(self.literal), ", ".join(self.fixed_params), op, self.count)

        def cstr(self, color=False):
            return str(self)

        def iterGroundings(self, mrf, simplify=False):
            a = {}
            other_params = []
            for param in self.literal.params:
                if param[0].isupper():
                    a[param] = param
                else:
                    if param not in self.fixed_params:
                        other_params.append(param)
            #other_params = list(set(self.literal.params).difference(self.fixed_params))
            # for each assignment of the fixed parameters...
            for assignment in self._iterAssignment(mrf, list(self.fixed_params), a):
                gndAtoms = []
                # generate a count constraint with all the atoms we obtain by grounding the other params
                for full_assignment in self._iterAssignment(mrf, list(other_params), assignment):
                    gndLit = self.literal.ground(mrf, full_assignment, None)
                    gndAtoms.append(gndLit.gndAtom)
                yield self.mln.logic.gnd_count_constraint(gndAtoms, self.op, self.count), []

        def _iterAssignment(self, mrf, variables, assignment):
            """iterates over all possible assignments for the given variables of this constraint's literal
                    variables: the variables that are still to be grounded"""
            # if all variables have been grounded, we have the complete assigment
            if len(variables) == 0:
                yield dict(assignment)
                return
            # otherwise one of the remaining variables in the list...
            varname = variables.pop()
            domName = self.literal.getVarDomain(varname, mrf.mln)
            for value in mrf.domains[domName]: # replacing it with one of the constants
                assignment[varname] = value
                # recursive descent to ground further variables
                for a in self._iterAssignment(mrf, variables, assignment):
                    yield a

        def getVariables(self, mln, variables = None, constants = None):
            if constants is not None:
                self.literal.getVariables(mln, variables, constants)
            return variables


#  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #


    class GroundCountConstraint(NonLogicalConstraint):
        def __init__(self, gndAtoms, op, count):
            self.gndAtoms = gndAtoms
            self.count = count
            self.op = op

        def isTrue(self, world_values):
            c = 0
            for ga in self.gndAtoms:
                if(world_values[ga.idx]):
                    c += 1
            return eval("c %s self.count" % self.op)

        def __str__(self):
            op = self.op
            if op == "==": op = "="
            return "count(%s) %s %d" % (";".join(map(str, self.gndAtoms)), op, self.count)

        def cstr(self, color=False):
            op = self.op
            if op == "==": op = "="
            return "count(%s) %s %d" % (";".join([c.cstr(color) for c in self.gndAtoms]), op, self.count)

        def negate(self):
            if self.op == "==":
                self.op = "!="
            elif self.op == "!=":
                self.op = "=="
            elif self.op == ">=":
                self.op = "<="
                self.count -= 1
            elif self.op == "<=":
                self.op = ">="
                self.count += 1

        def idxGroundAtoms(self, l = None):
            if l is None: l = []
            for ga in self.gndAtoms:
                l.append(ga.idx)
            return l

        def getGroundAtoms(self, l = None):
            if l is None: l = []
            for ga in self.gndAtoms:
                l.append(ga)
            return l


#  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #


    def isvar(self, identifier):
        """
        Returns True if identifier is a logical variable according
        to the used grammar, and False otherwise.
        """
        return self.grammar.isvar(identifier)

    def isconstant(self, identifier):
        """
        Returns True if identifier is a logical constant according
        to the used grammar, and False otherwise.
        """
        return self.grammar.isConstant(identifier)

    def istemplvar(self, s):
        """
        Returns True if `s` is template variable or False otherwise.
        """
        return self.grammar.istemplvar(s)

    def parse_formula(self, formula):
        """
        Returns the Formula object parsed by the grammar.
        """
        return self.grammar.parse_formula(formula)

    def parse_predicate(self, string):
        return self.grammar.parse_predicate(string)

    def parse_atom(self, string):
        return self.grammar.parse_atom(string)

    def parse_domain(self, decl):
        return self.grammar.parse_domain(decl)

    def parse_literal(self, lit):
        return self.grammar.parse_literal(lit)


    def islit(self, f):
        """
        Determines whether or not a formula is a literal.
        """
        return isinstance(f, Logic.GroundLit) or isinstance(f, Logic.Lit) or isinstance(f, Logic.GroundAtom)


    def iseq(self, f):
        """
        Determines wheter or not a formula is an equality consttaint.
        """
        return isinstance(f, Logic.Equality)


    def islitconj(self, f):
        """
        Returns true if the given formula is a conjunction of literals.
        """
        if self.islit(f): return True
        if not isinstance(f, Logic.Conjunction):
            if not isinstance(f, Logic.Lit) and \
                 not isinstance(f, Logic.GroundLit) and \
                 not isinstance(f, Logic.Equality) and \
                 not isinstance(f, Logic.TrueFalse):
                return False
            return True
        for child in f.children:
            if not isinstance(child, Logic.Lit) and \
                not isinstance(child, Logic.GroundLit) and \
                not isinstance(child, Logic.Equality) and \
                not isinstance(child, Logic.TrueFalse):
                return False
        return True


    def isclause(self, f):
        """
        Returns true if the given formula is a clause (a disjunction of literals)
        """
        if self.islit(f): return True
        if not isinstance(f, Logic.Disjunction):
            if not isinstance(f, Logic.Lit) and \
                 not isinstance(f, Logic.GroundLit) and \
                 not isinstance(f, Logic.Equality) and \
                 not isinstance(f, Logic.TrueFalse):
                return False
            return True
        for child in f.children:
            if not isinstance(child, Logic.Lit) and \
                not isinstance(child, Logic.GroundLit) and \
                not isinstance(child, Logic.Equality) and \
                not isinstance(child, Logic.TrueFalse):
                return False
        return True


    def negate(self, formula):
        """
        Returns a negation of the given formula.

        The original formula will be copied first. The resulting negation is tied
        to the same mln and will have the same formula index. Also performs
        a rudimentary simplification in case of `formula` is a (ground) literal
        or equality.
        """
        if isinstance(formula, Logic.Lit) or isinstance(formula, Logic.GroundLit):
            ret = formula.copy()
            ret.negated = not ret.negated
        elif isinstance(formula, Logic.Equality):
            ret = formula.copy()
            ret.negated = not ret.negated
        else:
            ret = self.negation([formula.copy(mln=formula.mln, idx=None)], mln=formula.mln, idx=formula.idx)
        return ret


    def conjugate(self, children, mln=None, idx=inherit):
        """
        Returns a conjunction of the given children.

        Performs rudimentary simplification in the sense that if children
        has only one element, it returns this element (e.g. one literal)
        """
        if not children:
            return self.true_false(0, mln=ifnone(mln, self.mln), idx=idx)
        elif len(children) == 1:
            return children[0].copy(mln=ifnone(mln, self.mln), idx=idx)
        else:
            return self.conjunction(children, mln=ifnone(mln,self.mln), idx=idx)


    def disjugate(self, children, mln=None, idx=inherit):
        """
        Returns a conjunction of the given children.

        Performs rudimentary simplification in the sense that if children
        has only one element, it returns this element (e.g. one literal)
        """
        if not children:
            return self.true_false(0, mln=ifnone(mln, self.mln), idx=idx)
        elif len(children) == 1:
            return children[0].copy(mln=ifnone(mln, self.mln), idx=idx)
        else:
            return self.disjunction(children, mln=ifnone(mln,self.mln), idx=idx)
    
    
    @staticmethod
    def iter_eq_varassignments(eq, f, mln):
        """
        Iterates over all variable assignments of an (in)equality constraint.
        
        Needs a formula since variables in equality constraints are not typed per se.
        """
        doms = f.vardoms()
        eqVars_ = eq.vardoms()
        if not set(eqVars_).issubset(doms):
            raise Exception('Variable in (in)equality constraint not bound to a domain: %s' % eq)
        eqVars = {}
        for v in eqVars_:
            eqVars[v] = doms[v]
        for assignment in Logic._iter_eq_varassignments(mln, eqVars, {}):
            yield assignment
            
    @staticmethod
    def _iter_eq_varassignments(mrf, variables, assignment):
        if len(variables) == 0:
            yield assignment
            return
        variables = dict(variables)
        variable, domName = variables.popitem()
        domain = mrf.domains[domName]
        for value in domain:
            for assignment in Logic._iter_eq_varassignments(mrf, variables, dict_union(assignment, {variable: value})):
                yield assignment


    @staticmethod
    def clauseset(cnf):
        """
        Takes a formula in CNF and returns a set of clauses, i.e. a list of sets
        containing literals. All literals are converted into strings.
        """
        clauses = []
        if isinstance(cnf, Logic.Disjunction):
            clauses.append(set(map(str, cnf.children)))
        elif isinstance(cnf, Logic.Conjunction):
            for disj in cnf.children:
                clause = set()
                clauses.append(clause)
                if isinstance(disj, Logic.Disjunction):
                    for c in disj.children:
                        clause.add(str(c))
                else:
                    clause.add(str(disj))
        else:
            clauses.append(set([str(cnf)]))
        return clauses
    
    
    @staticmethod
    def cnf(gfs, formulas, logic, allpos=False):
        """
        convert the given ground formulas to CNF
        if allPositive=True, then formulas with negative weights are negated to make all weights positive
        @return a new pair (gndformulas, formulas)
        
        .. warning::
        
        If allpos is True, this might have side effects on the formula weights of the MLN.
        
        """    
        # get list of formula indices which we must negate
        formulas_ = []    
        negated = []
        if allpos:
            for f in formulas:
                if f.weight < 0:
                    negated.append(f.idx)
                    f = logic.negate(f)                 
                    f.weight = -f.weight
                formulas_.append(f)
        # get CNF version of each ground formula
        gfs_ = []
        for gf in gfs:
            # non-logical constraint
            if not gf.islogical(): # don't apply any transformations to non-logical constraints
                if gf.idx in negated:
                    gf.negate()
                gfs_.append(gf)
                continue
            # logical constraint
            if gf.idx in negated:
                cnf = logic.negate(gf).cnf()
            else:
                cnf = gf.cnf()
            if isinstance(cnf, Logic.TrueFalse): # formulas that are always true or false can be ignored
                continue
            cnf.idx = gf.idx
            gfs_.append(cnf)
        # return modified formulas
        return gfs_, formulas_
    
    
    def conjunction(self, *args, **kwargs):
        """
        Returns a new instance of a Conjunction object.
        """
        raise Exception('%s does not implement conjunction()' % str(type(self)))
    
    def disjunction(self, *args, **kwargs):
        """
        Returns a new instance of a Disjunction object.
        """
        raise Exception('%s does not implement disjunction()' % str(type(self)))
    
    def negation(self, *args, **kwargs):
        """
        Returns a new instance of a Negation object.
        """
        raise Exception('%s does not implement negation()' % str(type(self)))
    
    def implication(self, *args, **kwargs):
        """
        Returns a new instance of a Implication object.
        """
        raise Exception('%s does not implement implication()' % str(type(self)))
    
    def biimplication(self, *args, **kwargs):
        """
        Returns a new instance of a Biimplication object.
        """
        raise Exception('%s does not implement biimplication()' % str(type(self)))
    
    def equality(self, *args, **kwargs):
        """
        Returns a new instance of a Equality object.
        """
        raise Exception('%s does not implement equality()' % str(type(self)))
    
    def exist(self, *args, **kwargs):
        """
        Returns a new instance of a Exist object.
        """
        raise Exception('%s does not implement exist()' % str(type(self)))
    
    def gnd_atom(self, *args, **kwargs):
        """
        Returns a new instance of a GndAtom object.
        """
        raise Exception('%s does not implement gnd_atom()' % str(type(self)))
    
    def lit(self, *args, **kwargs):
        """
        Returns a new instance of a Lit object.
        """
        raise Exception('%s does not implement lit()' % str(type(self)))
    
    def litgroup(self, *args, **kwargs):
        """
        Returns a new instance of a Lit object.
        """
        raise Exception('%s does not implement litgroup()' % str(type(self)))

    def gnd_lit(self, *args, **kwargs):
        """
        Returns a new instance of a GndLit object.
        """
        raise Exception('%s does not implement gnd_lit()' % str(type(self)))
    
    def count_constraint(self, *args, **kwargs):
        """
        Returns a new instance of a CountConstraint object.
        """
        raise Exception('%s does not implement count_constraint()' % str(type(self)))
    
    def true_false(self, *args, **kwargs):
        """
        Returns a new instance of a TrueFalse constant object.
        """
        raise Exception('%s does not implement true_false()' % str(type(self)))
    
    def create(self, clazz, *args, **kwargs):
        """
        Takes the type of a logical element (class type) and creates
        a new instance of it.
        """
        return clazz(*args, **kwargs)
    

        
    
# this is a little hack to make nested classes pickleable
Constraint = Logic.Constraint
Formula = Logic.Formula
ComplexFormula = Logic.ComplexFormula
Conjunction = Logic.Conjunction
Disjunction = Logic.Disjunction
Lit = Logic.Lit
LitGroup = Logic.LitGroup
GroundLit = Logic.GroundLit
GroundAtom = Logic.GroundAtom
Equality = Logic.Equality
Implication = Logic.Implication
Biimplication = Logic.Biimplication
Negation = Logic.Negation
Exist = Logic.Exist
TrueFalse = Logic.TrueFalse
NonLogicalConstraint = Logic.NonLogicalConstraint
CountConstraint = Logic.CountConstraint
GroundCountConstraint = Logic.GroundCountConstraint
