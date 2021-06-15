"""This file holds a PyTorch implementation of Markov Logic Networks."""
from . import base
import torch
from torch_mrf import mrf

class TorchMLN(base.MLN):
    """This class describes a Markov Logic Network (MLN) that utilizes
       PyTorch and torch_mrfs for a faster training. The class inherits
       from pracmln.base.MLN and can be used the same way."""

    def __init__(self, logic='FirstOrderLogic', grammar='PRACGrammar', mlnfile=None, device="cpu"):
        super(TorchMLN, self).__init__(logic, grammar, mlnfile)
        self.device = device
    
    def learn(self, databases, method=BPLL, db_weights=None, discard_unused_predicates=True, **params):
        '''
        Triggers the learning parameter learning process for a given set of databases.
        Returns a new MLN object with the learned parameters.
        
        :param databases:     list of :class:`mln.database.Database` objects or filenames
        :param db_weights:    optional, list of floats which are used to weight
                              the databases and optimize with a weighted loss function
        '''

    