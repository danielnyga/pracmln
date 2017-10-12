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

from .inference.gibbs import GibbsSampler
from .inference.mcsat import MCSAT
from .inference.exact import EnumerationAsk
from .inference.wcspinfer import WCSPInference
from .inference.maxwalk import SAMaxWalkSAT
from .learning.cll import CLL, DCLL
from .learning.ll import LL
from .learning.bpll import BPLL, DPLL , BPLL_CG, DBPLL_CG

class Enum(object):
    
    def __init__(self, items):
        self.id2name = dict([(clazz.__name__, name) for (clazz, name) in items])
        self.name2id = dict([(name, clazz.__name__) for (clazz, name) in items])
        self.id2clazz = dict([(clazz.__name__, clazz) for (clazz, _) in items])
    
    
    def __getattr__(self, id_):
        if id_ in self.id2clazz:
            return self.id2clazz[id_]
        raise KeyError('Enum does not define %s, only %s' % (id_, list(self.id2clazz.keys())))
    
    
    def clazz(self, key):
        if type(key).__name__ == 'type':
            key = key.__name__ 
        if key in self.id2clazz:
            return self.id2clazz[str(key)]
        else:
            return self.id2clazz[self.name2id[key]]
        raise KeyError('No such element "%s"' % key)
    
    def id(self, key):
        if type(key).__name__ == 'type':
            return key.__name__
        if key in self.name2id: 
            return self.name2id[key]
        raise KeyError('No such element "%s"' % key)
    
    def name(self, id_):
        if id_ in self.id2name:
            return self.id2name[id_]
        raise KeyError('No element with id "%s"' % id_)
    
    def names(self):
        return list(self.id2name.values())
    
    def ids(self):
        return list(self.id2name.keys())
    
InferenceMethods = Enum(
    (
     (GibbsSampler, 'Gibbs sampling'), 
     (MCSAT, 'MC-SAT'), 
#      (FuzzyMCSAT,  'Fuzzy MC-SAT'),
#      (IPFPM, 'IPFP-M'), 
     (EnumerationAsk, 'Enumeration-Ask (exact)'),
     (WCSPInference, 'WCSP (exact MPE with toulbar2)'),
     (SAMaxWalkSAT, 'Max-Walk-SAT with simulated annealing (approx. MPE)')
    ))


LearningMethods = Enum(
     (
      (CLL, 'composite-log-likelihood'),
      (DCLL, '[discriminative] composite-log-likelihood'),
      (LL, "log-likelihood"),
      (DPLL, '[discriminative] pseudo-log-likelihood'),
      (BPLL, 'pseudo-log-likelihood'),
      (BPLL_CG, 'pseudo-log-likelihood (fast conjunction grounding)'),
      (DBPLL_CG, '[discriminative] pseudo-log-likelihood (fast conjunction grounding)')
#     'MLNBoost': 'MLN-BOOST',
#     'WPLL': 'Weighted Pseudo-likelihood',
      #"SLL": "sampling-based log-likelihood via direct descent",
#      "PLL": "pseudo-log-likelihood (deprecated)",
#      "VP": "[discriminative] Voted Perceptron",
#      "CD": "[discriminative] Contrastive Divergence",
#      "DBPLL_CG": "[discriminative] pseudo-log-likelihood with blocking (custom grounding, deprecated)",
#     "BPLL_CG": "pseudo-log-likelihood with blocking (custom grounding, deprecated)",
#       "BPLL_SF": "pseudo-log-likelihood with support for soft-functional constraints",
      #"BPLLMemoryEfficient": "pseudo-log-likelihood with blocking, memory-efficient", # NOTE: this method has now been merged into BPLL
#      "PLL_fixed": "pseudo-log-likelihood with fixed unitary clauses [deprecated]",
#      "BPLL_fixed": "pseudo-log-likelihood with blocking and fixed unitary clauses [deprecated]",
 #     "NPL_fixed": "negative pseudo-likelihood with fixed unitary clauses [deprecated]",
#       "LL_ISE": "[soft evidence] log-likelihood with soft features (independent soft evidence)",
#       "PLL_ISE": "[soft evidence] pseudo-log-likelihood with soft features (independent soft evidence)",
#       "DPLL_ISE": "[soft evidence][discriminative] pseudo-log-likelihood with soft features (indep. soft ev.)",
#       "LL_ISEWW": "[soft evidence] log-likelihood with independent soft evidence and weighting of worlds",
#       "E_ISEWW": "[soft evidence] error with independent soft evidence and weighting of worlds",
      #"SLL_ISE": "[soft evidence] sampling-based log-likelihood with soft features (independent soft evidence)", 
#       "SLL_SE": "[soft evidence] sampling-based log-likelihood",
#       "SLL_SE_DN": "[soft evidence] sampling-based log-likelihood via diagonal Newton" 
    ))


if __name__ =='__main__':
    
    print(InferenceMethods.id2clazz)
    print(InferenceMethods.id2name)
    print(InferenceMethods.name2id)
    print(LearningMethods.names())
    print(InferenceMethods.clazz(MCSAT))
    print(InferenceMethods.name('WCSPInference'))
    
