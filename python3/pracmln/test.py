"""
Created on Oct 28, 2015

@author: nyga
"""
import os

from pracmln import MLN, Database
from pracmln import query, learn
from pracmln.mlnlearn import EVIDENCE_PREDS
import time

from pracmln.utils import locs


def test_inference_smokers():
    p = os.path.join(locs.examples, 'smokers', 'smokers.pracmln')
    mln = MLN(mlnfile=('%s:wts.pybpll.smoking-train-smoking.mln' % p),
              grammar='StandardGrammar')
    db = Database(mln, dbfile='%s:smoking-test-smaller.db' % p)
    for method in ('EnumerationAsk',
                   'MC-SAT',
                   'WCSPInference',
                   'GibbsSampler'):
        for multicore in (False, True):
            print('=== INFERENCE TEST:', method, '===')
            query(queries='Cancer,Smokes,Friends',
                  method=method,
                  mln=mln,
                  db=db,
                  verbose=True,
                  multicore=multicore).run()


def test_inference_taxonomies():
    p = os.path.join(locs.examples, 'taxonomies', 'taxonomies.pracmln')
    mln = MLN(mlnfile=('%s:wts.learned.taxonomy.mln' % p),
              grammar='PRACGrammar',
              logic='FuzzyLogic')
    db = Database(mln, dbfile='%s:evidence.db' % p)
    for method in ('EnumerationAsk', 'WCSPInference'):
        print('=== INFERENCE TEST:', method, '===')
        query(queries='has_sense, action_role',
              method=method,
              mln=mln,
              db=db,
              verbose=False,
              cw=True).run().write()
    
    
def test_learning_smokers():
    p = os.path.join(locs.examples, 'smokers', 'smokers.pracmln')
    mln = MLN(mlnfile=('%s:smoking.mln' % p), grammar='StandardGrammar')
    mln.write()
    db = Database(mln, dbfile='%s:smoking-train.db' % p)
    for method in ('BPLL', 'BPLL_CG', 'CLL'):
        for multicore in (True, False):
            print('=== LEARNING TEST:', method, '===')
            learn(method=method,
                  mln=mln,
                  db=db,
                  verbose=True,
                  multicore=multicore).run()


def test_learning_taxonomies():
    p = os.path.join(locs.examples, 'taxonomies', 'taxonomies.pracmln')
    mln = MLN(mlnfile=('%s:senses_and_roles.mln' % p), grammar='PRACGrammar')
    mln.write()
    dbs = Database.load(mln, dbfiles='%s:training.db' % p)
    for method in ('DPLL', 'DBPLL_CG', 'DCLL'):
        for multicore in (True, False):
            print('=== LEARNING TEST:', method, '===')
            learn(method=method,
                  mln=mln,
                  db=dbs,
                  verbose=True,
                  multicore=multicore,
                  epreds='is_a',
                  discr_preds=EVIDENCE_PREDS).run()


def runall():
    start = time.time()
    test_inference_smokers()
    test_inference_taxonomies()
    test_learning_smokers()
    test_learning_taxonomies()
    print()
    print('all test finished after', time.time() - start, 'secs')

def main():
    runall()

if __name__ == '__main__':
    main()
