# Markov Logic Networks - Grounding
#
# (C) 2013 by Daniel Nyga (nyga@cs.tum.edu)
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


class AbstractGroundingFactory(object):
    """
    Abstract super class for all grounding factories.
    """
    
    def __init__(self, mrf, db, **params):
        self.params = params
        self.mrf = mrf
        self.mln = mrf.mln
        self.db = db
        
    def _createGroundAtoms(self):
        raise Exception('Not implemented')
    
    def _createGroundFormulas(self, simplify=False):
        raise Exception('Not implemented')

    def groundMRF(self, cwAssumption=False, simplify=False):
        self._createGroundAtoms()
        self.mrf.setEvidence(self.db.evidence, cwAssumption=cwAssumption)
        self.mln.watch.tag('Grounding formulas', self.mln.verbose)
        self._createGroundFormulas(simplify=simplify)
        self.mln.watch.finish()
        return self.mrf