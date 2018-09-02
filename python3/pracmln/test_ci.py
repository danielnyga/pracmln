import os

from pracmln import MLN, Database
from pracmln import query, learn
from pracmln.mlnlearn import EVIDENCE_PREDS
import time

from pracmln.utils import locs

p = os.path.join(locs.examples, 'smokers', 'smokers.pracmln')
mln = MLN(mlnfile=('%s:wts.pybpll.smoking-train-smoking.mln' % p),
          grammar='StandardGrammar')
db = Database(mln, dbfile='%s:smoking-test-smaller.db' % p)

def test_inference_smokers_EnumerationAsk_singlecore():
    global p
    global mln
    global db
    print('=== INFERENCE TEST: EnumerationAsk ===')
    query(queries='Cancer,Smokes,Friends',
          method='EnumerationAsk',
          mln=mln,
          db=db,
          verbose=False,
          multicore=False).run()

def test_inference_smokers_MCSAT_singlecore():
    global p
    global mln
    global db
    print('=== INFERENCE TEST: MC-SAT ===')
    query(queries='Cancer,Smokes,Friends',
          method='MC-SAT',
          mln=mln,
          db=db,
          verbose=False,
          multicore=False).run()

def test_inference_smokers_WCSP_singlecore():
    global p
    global mln
    global db
    print('=== INFERENCE TEST: WCSPInference ===')
    query(queries='Cancer,Smokes,Friends',
          method='WCSPInference',
          mln=mln,
          db=db,
          verbose=False,
          multicore=False).run()

# output not getting redirected to output file
def test_inference_smokers_Gibbs_singlecore():#(capsys):
    global p
    global mln
    global db
    print('=== INFERENCE TEST: GibbsSampler ===')
    query(queries='Cancer,Smokes,Friends',
          method='GibbsSampler',
          mln=mln,
          db=db,
          #output_filename="output.txt",
          verbose=True,
          multicore=False).run()
    #out, err = capsys.readouterr()
    #sys.stdout.write(out)
    #sys.stderr.write(err)
    #assert("44.400 % Cancer(Ann)" in out)
    #assert("50.000 % Cancer(Bob)" in out)
    #assert("50.200 % Friends(Ann,Ann)" in out)
    #assert("52.600 % Friends(Ann,Bob)" in out)
    #assert("36.600 % Friends(Bob,Ann)" in out)
    #assert("50.600 % Friends(Bob,Bob)" in out)
    #assert("40.800 % Smokes(Ann)" in out)
    #assert("21.800 % Smokes(Bob)" in out)



def test_inference_smokers_EnumerationAsk_multicore():
    global p
    global mln
    global db
    print('=== INFERENCE TEST: EnumerationAsk ===')
    query(queries='Cancer,Smokes,Friends',
          method='EnumerationAsk',
          mln=mln,
          db=db,
          verbose=False,
          multicore=True).run()

def test_inference_smokers_MCSAT_multicore():
    global p
    global mln
    global db
    print('=== INFERENCE TEST: MC-SAT ===')
    query(queries='Cancer,Smokes,Friends',
          method='MC-SAT',
          mln=mln,
          db=db,
          verbose=False,
          multicore=True).run()

def test_inference_smokers_WCSP_multicore():
    global p
    global mln
    global db
    print('=== INFERENCE TEST: WCSPInference ===')
    query(queries='Cancer,Smokes,Friends',
          method='WCSPInference',
          mln=mln,
          db=db,
          verbose=False,
          multicore=True).run()

def test_inference_smokers_Gibbs_multicore():
    global p
    global mln
    global db
    print('=== INFERENCE TEST: GibbsSampler ===')
    query(queries='Cancer,Smokes,Friends',
          method='GibbsSampler',
          mln=mln,
          db=db,
          verbose=True,
          multicore=True).run()

