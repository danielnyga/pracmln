"""This file holds a PyTorch implementation of Markov Logic Networks."""
from . import base
import copy
from .learning.bpll import BPLL
import torch
from torch_mrf import mrf
from torch_mrf import torch_random_variable

class TorchMLN(base.MLN):
    """This class describes a Markov Logic Network (MLN) that utilizes
       PyTorch and torch_mrfs for a faster training. The class inherits
       from pracmln.base.MLN and can be used the same way."""

    def __init__(self, logic='FirstOrderLogic', grammar='PRACGrammar', mlnfile=None, device="cpu"):
        super(TorchMLN, self).__init__(logic, grammar, mlnfile)
        self.device = device

    def copy(self):
        '''
        Returns a deep copy of this MLN, which is not yet materialized.
        '''
        mln_ = TorchMLN(logic=self.logic.__class__.__name__, grammar=self.logic.grammar.__class__.__name__)
        for pred in self.iterpreds():
            mln_.predicate(copy.copy(pred))
        mln_.domain_decls = list(self.domain_decls)
        for i, f in self.iterformulas():
            mln_.formula(f.copy(mln=mln_), weight=self.weight(i), fixweight=self.fixweights[i], unique_templvars=self._unique_templvars[i])
        mln_.domains = dict(self.domains)
        mln_.vars = dict(self.vars)
        mln_._probreqs = list(self.probreqs)
        mln_.fuzzypreds = list(self.fuzzypreds)
        mln_.device = self.device
        return mln_
    
    def learn(self, databases, method=BPLL, db_weights=None, discard_unused_predicates=True, **params):
        '''
        Triggers the learning parameter learning process for a given set of databases.
        Returns a new MLN object with the learned parameters.
        
        :param databases:     list of :class:`mln.database.Database` objects or filenames
        :param db_weights:    optional, list of floats which are used to weight
                              the databases and optimize with a weighted loss function
        '''

    def ground(self, dbs):
        '''
        Creates and returns a ground Markov Random Field for the given database.
        
        :param db:         database filename (string) or Database object
        :param cw:         if the closed-world assumption shall be applied (to all predicates)
        :param cwpreds:    a list of predicate names the closed-world assumption shall be applied.
        '''
        mrf_variables = []
        for name, domain in self.domains.items():
            mrf_variables.append(torch_random_variable.RandomVariable(name, domain))
        
        cliques = []

        for formula in self.iterformulas():
            print(formula)