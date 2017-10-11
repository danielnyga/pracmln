# Markov Logic Networks -- Automated Cross-Validation Tool
#
# (C) 2012 by Daniel Nyga (nyga@cs.tum.edu)
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

import time
import os
import sys
import traceback
import shutil

from optparse import OptionParser
from random import shuffle, sample
import math

from dnutils import logs, stop, out

from .mln.methods import LearningMethods, InferenceMethods
from .utils.eval import ConfusionMatrix
from multiprocessing import Pool
import logging
from . import praclog
from logging import FileHandler
from .mln.database import Database
from .mlnquery import MLNQuery
from .mlnlearn import MLNLearn
from .mln.mlnpreds import FuzzyPredicate
from .utils.project import MLNProject

logger = logs.getlogger(__name__)


usage = '''Usage: %prog [options] <predicate> <mlnproject> <dbfile>'''

parser = OptionParser(usage=usage)
parser.add_option("-k", "--folds", dest="folds", type='int', default=10,
                  help="Number of folds for k-fold Cross Validation")
parser.add_option("-p", "--percent", dest="percent", type='int', default=100,
                  help="Use only PERCENT% of the data. (default=100)")
parser.add_option("-v", "--verbose", dest="verbose", action='store_true', default=False,
                  help="Verbose mode.")
parser.add_option("-m", "--multicore", dest="multicore", action='store_true', default=False,
                  help="Distribute the folds over all CPUs.")
parser.add_option('-n', '--noisy', dest='noisy', type='str', default=None,
                  help='-nDOMAIN defines DOMAIN as a noisy string.')
parser.add_option('-f', '--folder', dest='folder', type='str', default=None,
                  help='-f <folder> the folder in which the results shall be saved.')


class XValFoldParams:

    def __init__(self):
        self.mln = None
        self.learn_dbs = None
        self.test_dbs = None
        self.fold_idx = None
        self.folds = None
        self.directory = None
        self.querypred = None
        self.queryconf = None
        self.learnconf = None


class XValFold(object):
    '''
    Class representing and providing methods for a cross validation fold.
    '''
    
    def __init__(self, params):
        '''
        params being a XValFoldParams object.  
        '''
        self.params = params
        self.fold_id = 'Fold-%d' % params.fold_idx
        self.confmat = ConfusionMatrix()
        # write the training and testing databases into a file
        with open(os.path.join(params.directory, 'train_dbs_%d.db' % params.fold_idx), 'w+') as dbfile:
            Database.write_dbs(params.learn_dbs, dbfile)
        with open(os.path.join(params.directory, 'test_dbs_%d.db' % params.fold_idx), 'w+') as dbfile:
            Database.write_dbs(params.test_dbs, dbfile)
        
            
    def eval(self, mln, dbs):
        '''
        Returns a confusion matrix for the given (learned) MLN evaluated on
        the databases given in dbs.
        '''
        querypred = self.params.querypred
#         query_dom = self.params.query_dom
        
#         sig = ['?arg%d' % i for i, _ in enumerate(mln.predicates[query_pred])]
#         querytempl = '%s(%s)' % (query_pred, ','.join(sig))
        
#         dbs = map(lambda db: db.copy(mln), dbs)
        
        for db_ in dbs:
            # save and remove the query predicates from the evidence
            db = db_.copy()
            gndtruth = mln.ground(db)
            gndtruth.apply_cw()
            for atom, _ in db.gndatoms(querypred):
                out('removing evidence', repr(atom))
                del db.evidence[atom]
            db.write()
            stop()
            try:
                resultdb = MLNQuery(config=self.params.queryconf, mln=mln, method=InferenceMethods.WCSPInference, db=db, 
                                  cw_preds=[p.name for p in mln.predicates if p.name != self.params.querypred], multicore=False).run().resultdb
                result = mln.ground(db)
                result.set_evidence(resultdb)
                for variable in result.variables:
                    if variable.predicate.name != querypred: continue
                    pvalue = variable.evidence_value()
                    tvalue = variable.evidence_value()
                    prediction = [a for a, v in variable.atomvalues(pvalue) if v == 1]
                    truth = [a for a, v in variable.atomvalues(tvalue) if v == 1]
                    prediction = str(prediction[0]) if prediction else None
                    truth = str(truth[0]) if truth else None
                    self.confmat.addClassificationResult(prediction, truth)
#                 sig2 = list(sig)
#                 entityIdx = mln.predicates[query_pred].argdoms.index(query_dom)
#                 for entity in db.domains[]:
#                     sig2[entityIdx] = entity
#                     query = '%s(%s)' % (queryPred, ','.join(sig2))
#                     for truth in trueDB.query(query):
#                         truth = truth.values().pop()
#                     for pred in resultDB.query(query):
#                         pred = pred.values().pop()
#                     self.confMatrix.addClassificationResult(pred, truth)
#                 for e, v in trueDB.evidence.iteritems():
#                     if v is not None:
#                         db.addGroundAtom('%s%s' % ('' if v is True else '!', e))
            except:
                logger.critical(''.join(traceback.format_exception(*sys.exc_info())))

    def run(self):
        '''
        Runs the respective fold of the crossvalidation.
        '''
        logger.info('Running fold %d of %d...' % (self.params.fold_idx + 1, self.params.folds))
        directory = self.params.directory
        try:
#             # Apply noisy string clustering
#             log.debug('Transforming noisy strings...')
#             if self.params.noisyStringDomains is not None:
#                 noisyStrTrans = NoisyStringTransformer(self.params.mln, self.params.noisyStringDomains, True)
#                 learnDBs_ = noisyStrTrans.materializeNoisyDomains(self.params.learnDBs)
#                 testDBs_ = noisyStrTrans.transformDBs(self.params.testDBs)
#             else:
#                 learnDBs_ = self.params.learnDBs
#                 testDBs_ = self.params.testDBs

            # train the MLN
            mln = self.params.mln
            logger.debug('Starting learning...')
            learn_dbs = [db.copy() for db in self.params.learn_dbs]
            # apply closed world for fuzzy atoms
            for db in learn_dbs:
                for a, v in db.gndatoms([p.name for p in mln.predicates if isinstance(p, FuzzyPredicate)]):
                    if v != 1: db[a] = 0
                    
            learned = MLNLearn(config=self.params.learnconf, mln=mln, db=learn_dbs, multicore=False).run()#200
            # store the learned MLN in a file
            learned.tofile(os.path.join(directory, 'run_%d.mln' % self.params.fold_idx))
            logger.debug('Finished learning.')
            
            # evaluate the MLN
            logger.debug('Evaluating.')
#             learnedMLN.setClosedWorldPred(None)
#             if self.params.cwPreds is None:
#                 self.params.cwPreds = [p for p in mln.predicates if p != self.params.queryPred]
#             for pred in [pred for pred in self.params.cwPreds if pred in learnedMLN.predicates]:
#                 learnedMLN.setClosedWorldPred(pred)
            self.eval(learned, self.params.test_dbs)
            self.confmat.toFile(os.path.join(directory, 'conf_matrix_%d.cm' % self.params.fold_idx))
            logger.debug('Evaluation finished.')
        except (KeyboardInterrupt, SystemExit):
            logger.critical("Exiting...")
            return None
        
    
# class NoisyStringTransformer(object):
#     '''
#     This transformer takes a set of strings and performs a clustering
#     based on the edit distance. It transforms databases wrt to the clusters.
#     '''
#     
#     def __init__(self, mln, noisyStringDomains, verbose=True):
#         self.mln = mln
#         self.noisyStringDomains = noisyStringDomains
#         self.verbose = verbose
#         self.clusters = {} # maps domain name -> list of clusters
#         self.noisyDomains = {}
#         self.log = logging.getLogger('NoisyString')
#     
#     def materializeNoisyDomains(self, dbs):
#         '''
#         For each noisy domain, (1) if there is a static domain specification,
#         map the values of that domain in all dbs to their closest neighbor
#         in the domain.
#         (2) If there is no static domain declaration, apply SAHN clustering
#         to the values appearing dbs, take the cluster centroids as the values
#         of the domain and map the dbs as in (1).
#         '''
#         fullDomains = mergeDomains(*[db.domains for db in dbs])
#         if self.verbose and len(self.noisyStringDomains) > 0:
#             self.log.info('materializing noisy domains...')
#         for nDomain in self.noisyStringDomains:
#             if fullDomains.get(nDomain, None) is None: continue
#             # apply the clustering step
#             values = fullDomains[nDomain]
#             clusters = SAHN(values)
#             self.clusters[nDomain] = clusters
#             self.noisyDomains[nDomain] = [c._computeCentroid()[0] for c in clusters]
#             if self.verbose:
#                 self.log.info('  reducing domain %s: %d -> %d values' % (nDomain, len(values), len(clusters)))
#                 self.log.info('   %s', str(self.noisyDomains[nDomain]))
#         return self.transformDBs(dbs)
#         
#     def transformDBs(self, dbs):
#         newDBs = []
#         for db in dbs:
# #             if len(db.softEvidence) > 0:
# #                 raise Exception('This is not yet implemented for soft evidence.')
#             commonDoms = set(db.domains.keys()).intersection(set(self.noisyStringDomains))
#             if len(commonDoms) == 0:
#                 newDBs.append(db)
#                 continue
#             newDB = db.duplicate()
#             for domain in commonDoms:
#                 # map the values in the database to the static domain values
#                 valueMap = dict([(val, computeClosestCluster(val, self.clusters[domain])[1][0]) for val in newDB.domains[domain]])
#                 newDB.domains[domain] = valueMap.values()
#                 # replace the affected evidences
#                 for ev in newDB.evidence.keys():
#                     truth = newDB.evidence[ev]
#                     _, pred, params = db.mln.logic.parseLiteral(ev)
#                     if domain in self.mln.predicates[pred]: # domain is affected by the mapping  
#                         newDB.retractGndAtom(ev)
#                         newArgs = [v if domain != self.mln.predicates[pred][i] else valueMap[v] for i, v in enumerate(params)]
#                         atom = '%s%s(%s)' % ('' if truth else '!', pred, ','.join(newArgs))
#                         newDB.addGroundAtom(atom)
#             newDBs.append(newDB)
#         return newDBs

def runFold(fold):
    try:
        fold.run()
    except:
        raise Exception(''.join(traceback.format_exception(*sys.exc_info())))
    return fold

if __name__ == '__main__':
    (options, args) = parser.parse_args()
    folds = options.folds
    percent = options.percent
    verbose = options.verbose
    multicore = options.multicore
    dirname = options.folder
    predname = args[0]
    mlnproject = args[1]
    dbfiles = args[2:]
    startTime = time.time()

    #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  
    # set up the directory    
    #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #
    timestamp = time.strftime("%Y-%b-%d-%H-%M-%S", time.localtime())
    project = MLNProject.open(os.path.abspath(os.path.join(os.getcwd(), mlnproject)))
    project.write()
    if dirname is None:  
        mlnname = project.queryconf['mln'][:-4]
        idx = 1
        while True:
            dirname = '%s-%d' % (mlnname, idx)
            idx += 1
            if not os.path.exists(dirname): break
        dirname += '-' + timestamp
    
    expdir = os.getenv('PRACMLN_EXPERIMENTS', '.')
    expdir = os.path.join(expdir, dirname)
    if os.path.exists(expdir):
        print('Directory "%s" exists. Overwrite? ([y]/n)' % expdir, end=' ')
        answer = sys.stdin.read(1)
        if answer not in ('y','\n'):
            exit(0)
        else:
            shutil.rmtree(expdir)
    os.mkdir(expdir)
    # set up the logger
    praclog.level(logging.INFO)
    fileLogger = FileHandler(os.path.join(expdir, 'xval.log'))
    fileLogger.setFormatter(praclog.formatter)
    logger.addHandler(fileLogger)

    logger.info('Log for %d-fold cross-validation of %s using %s' % (folds, mlnproject, dbfiles))
    logger.info('Date: %s' % timestamp)
    logger.info('Results will be written into %s' % expdir)

    # preparations: Read the MLN and the databases
    learn_mln = project.loadmln('learn') 
#     query_mln = project.loadmln('query')
    dbs = project.loaddb(learn_mln, project.queryconf, db=dbfiles[0])
    logger.info('Read %d databases.' % len(dbs))
    
    # create the partition of data
    subsetLen = int(math.ceil(len(dbs) * percent / 100.0))
    if subsetLen < len(dbs):
        logger.info('Using only %d of %d DBs' % (subsetLen, len(dbs)))
    dbs = sample(dbs, subsetLen)

    if len(dbs) < folds:
        logger.error('Cannot do %d-fold cross validation with only %d databases.' % (folds, len(dbs)))
        exit(-1)
    
    shuffle(dbs)
    partSize = int(math.ceil(len(dbs)/float(folds)))
    partition = []
    for i in range(folds):
        partition.append(dbs[i*partSize:(i+1)*partSize])
    
    
    foldRunnables = []
    for fold_idx in range(folds):
        params = XValFoldParams()
        params.mln = learn_mln.copy()
        params.learn_dbs = []
        for dbs in [d for i, d in enumerate(partition) if i != fold_idx]:
            params.learn_dbs.extend(dbs)
        params.test_dbs = partition[fold_idx]
        params.fold_idx = fold_idx
        params.folds = folds
        params.directory = expdir
        params.learnconf = project.learnconf
        params.queryconf = project.queryconf
        params.querypred = predname
        foldRunnables.append(XValFold(params))
        logger.info('Params for fold %d:\n%s' % (fold_idx, str(params)))
    
    if multicore:
        # set up a pool of worker processes
        try:
            workerPool = Pool()
            logger.info('Starting %d-fold Cross-Validation in %d processes.' % (folds, workerPool._processes))
            result = workerPool.map_async(runFold, foldRunnables).get()
            workerPool.close()
            workerPool.join()
            cm = ConfusionMatrix()
            for r in result:
                cm.combine(r.confmat)
            elapsedTimeMP = time.time() - startTime
            cm.toFile(os.path.join(expdir, 'conf_matrix.cm'))
            # create the pdf table and move it into the log directory
            # this is a dirty hack since pdflatex apparently
            # does not support arbitrary output paths
            pdfname = 'conf_matrix'
            logger.info('creating pdf if confusion matrix...')
            cm.toPDF(pdfname)
            os.rename('%s.pdf' % pdfname, os.path.join(expdir, '%s.pdf' % pdfname))
        except (KeyboardInterrupt, SystemExit, SystemError):
            logger.critical("Caught KeyboardInterrupt, terminating workers")
            workerPool.terminate()
            workerPool.join()
            exit(1)
        except:
            logger.error('\n' + ''.join(traceback.format_exception(*sys.exc_info())))
            exit(1)
#     startTime = time.time()
    else:
        logger.info('Starting %d-fold Cross-Validation in 1 process.' % (folds))
        cm = ConfusionMatrix()
        for fold in foldRunnables:
            cm.combine(runFold(fold).confmat)
        cm.toFile(os.path.join(expdir, 'conf_matrix.cm'))
        pdfname = 'conf_matrix'
        logger.info('creating pdf if confusion matrix...')
        cm.toPDF(pdfname)
        os.rename('%s.pdf' % pdfname, os.path.join(expdir, '%s.pdf' % pdfname))
        elapsedTimeSP = time.time() - startTime
    
    if multicore:
        logger.info('%d-fold crossvalidation (MP) took %.2f min' % (folds, elapsedTimeMP / 60.0))
    else:
        logger.info('%d-fold crossvalidation (SP) took %.2f min' % (folds, elapsedTimeSP / 60.0))
        
