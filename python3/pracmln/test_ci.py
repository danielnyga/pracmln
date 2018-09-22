import os

import random
random.seed(0)

from pracmln import MLN, Database
from pracmln import query, learn
from pracmln.mlnlearn import EVIDENCE_PREDS
import time

from pracmln.utils import locs

p = os.path.join(locs.examples, 'smokers', 'smokers.pracmln')
mln = MLN(mlnfile=('%s:wts.pybpll.smoking-train-smoking.mln' % p),
          grammar='StandardGrammar')
db = Database(mln, dbfile='%s:smoking-test-smaller.db' % p)

expected_result = {'Friends(Ann,Ann)': 0.5, 'Friends(Bob,Bob)': 0.5, 'Cancer(Ann)': 1.0, 'Friends(Bob,Ann)': 0.376, 'Smokes(Bob)': 0.245, 'Smokes(Ann)': 0.437, 'Friends(Ann,Bob)': 0.0, 'Cancer(Bob)': 0.0}


def test_inference_smokers_EnumerationAsk_singlecore():
    global p
    global mln
    global db
    global expected_result
    delta = 0.05
    print('=== INFERENCE TEST: EnumerationAsk ===')
    r = query(queries='Cancer,Smokes,Friends',
          method='EnumerationAsk',
          mln=mln,
          db=db,
          verbose=False,
          multicore=False).run()
    #print(r.results)
    for k, v in r.results.items():
        assert(abs(expected_result[k]-v) < delta)

def test_inference_smokers_MCSAT_singlecore():
    global p
    global mln
    global db
    global expected_result
    delta = 0.1
    print('=== INFERENCE TEST: MC-SAT ===')
    r = query(queries='Cancer,Smokes,Friends',
          method='MC-SAT',
          mln=mln,
          db=db,
          verbose=False,
          multicore=False).run()
    #print(r.results)
    for k, v in r.results.items():
        assert(abs(expected_result[k]-v) < delta)

def test_inference_smokers_WCSP_singlecore():
    global p
    global mln
    global db
    global expected_result
    delta = 0.6
    print('=== INFERENCE TEST: WCSPInference ===')
    r = query(queries='Cancer,Smokes,Friends',
          method='WCSPInference',
          mln=mln,
          db=db,
          verbose=False,
          multicore=False).run()
    #print(r.results)
    for k, v in r.results.items():
        assert(abs(expected_result[k]-v) < delta)

# output not getting redirected to output file
def test_inference_smokers_Gibbs_singlecore():#(capsys):
    global p
    global mln
    global db
    global expected_result
    delta = 0.6
    print('=== INFERENCE TEST: GibbsSampler ===')
    r = query(queries='Cancer,Smokes,Friends',
          method='GibbsSampler',
          mln=mln,
          db=db,
          #output_filename="output.txt",
          verbose=False,
          multicore=False).run()
    #print(r)
    #r.write_elapsed_time()
    #r.write()
    #print(r.results)
    #print(r.results)
    for k, v in r.results.items():
        assert(abs(expected_result[k]-v) < delta)
        
    #print(type(r.results))
    #print(expected_result)
    #print(type(expected_result))
    #assert(r.results == expected_result)
    
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
    global expected_result
    delta = 0.05
    print('=== INFERENCE TEST: EnumerationAsk ===')
    r = query(queries='Cancer,Smokes,Friends',
          method='EnumerationAsk',
          mln=mln,
          db=db,
          verbose=False,
          multicore=True).run()
    #print(r.results)
    for k, v in r.results.items():
        assert(abs(expected_result[k]-v) < delta)

def test_inference_smokers_MCSAT_multicore():
    global p
    global mln
    global db
    global expected_result
    delta = 0.1
    print('=== INFERENCE TEST: MC-SAT ===')
    r = query(queries='Cancer,Smokes,Friends',
          method='MC-SAT',
          mln=mln,
          db=db,
          verbose=False,
          multicore=True).run()
    #print(r.results)
    for k, v in r.results.items():
        assert(abs(expected_result[k]-v) < delta)

def test_inference_smokers_WCSP_multicore():
    global p
    global mln
    global db
    global expected_result
    delta = 0.6
    print('=== INFERENCE TEST: WCSPInference ===')
    r = query(queries='Cancer,Smokes,Friends',
          method='WCSPInference',
          mln=mln,
          db=db,
          verbose=False,
          multicore=True).run()
    #print(r.results)
    for k, v in r.results.items():
        assert(abs(expected_result[k]-v) < delta)

def test_inference_smokers_Gibbs_multicore():
    global p
    global mln
    global db
    global expected_result
    delta = 0.6
    print('=== INFERENCE TEST: GibbsSampler ===')
    r = query(queries='Cancer,Smokes,Friends',
          method='GibbsSampler',
          mln=mln,
          db=db,
          verbose=False,
          multicore=True).run()
    #print(r.results)
    for k, v in r.results.items():
        assert(abs(expected_result[k]-v) < delta)

def main():
    test_inference_smokers_EnumerationAsk_singlecore()
    test_inference_smokers_MCSAT_singlecore()
    test_inference_smokers_WCSP_singlecore()
    test_inference_smokers_Gibbs_singlecore()
    test_inference_smokers_EnumerationAsk_multicore()
    test_inference_smokers_MCSAT_multicore()
    test_inference_smokers_WCSP_multicore()
    test_inference_smokers_Gibbs_multicore()


if __name__ == '__main__':
    main()








