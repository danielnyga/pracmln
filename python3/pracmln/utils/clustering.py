#
# Clustering Methods
#
# (C) 2013 by Daniel Nyga, (nyga@cs.uni-bremen.de)
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
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.'''
from dnutils import getlogger, first

from pracmln.utils.project import MLNProject

from pracmln import MLN, Database, mlnpath

from pracmln.mln.util import mergedom
from evalSeqLabels import editDistance
import math
import numpy
from collections import defaultdict
from itertools import combinations


class Cluster(object):
    '''
    Class representing a cluster of some set of abstract data points.
    '''
    
    def __init__(self, dataPoints=None):
        if dataPoints is None:
            dataPoints = []
        else:
            self.dataPoints = dataPoints
        self.type = None
        for point in dataPoints:
            t = type(point)
            t = 'number' if t is int or t is float or t is int else 'str'
            if self.type is not None and self.type != t:
                raise Exception('Data points must be all of the same type (%s).' % self.type)
            self.type = t
            
            
    def _computeCentroid(self, distance='auto'):
        '''
        Compute the centroid of the cluster.
        '''
        dist = self._getDistanceMetrics(distance)
        centroid = None
        if self.type == 'str':
            minAvgDist = float('inf')
            if len(self.dataPoints) == 1:
                return (self.dataPoints[0], 0)
            for p1 in self.dataPoints:
                avgDist = .0
                counter = 0
                for p2 in self.dataPoints:
                    if p1 is p2: continue
                    counter += 1
                    avgDist += dist(p1, p2)
                avgDist /= float(counter)
                if avgDist < minAvgDist:
                    minAvgDist = avgDist
                    centroid = p1
        elif self.type == 'number':
            centroid = [sum(x) / float(len(self.dataPoints)) for x in zip(self.dataPoints)]
        return centroid, minAvgDist
    
    def _getDistanceMetrics(self, distance):
        if distance == 'auto' and self.type == 'str':
            dist = editDistance
        elif distance == 'auto' and self.type == 'number':
            dist = lambda x, y: math.sqrt(sum(map(lambda x_1, x_2: (x_1 - x_2) ** 2, list(zip(x, y)))))
        elif type(distance) is callable:
            dist = distance
        else:
            raise Exception('Distance measure not supported for the given data.')
        return dist
            
    def addPoint(self, dataPoint):
        '''
        Adds a data Point to the cluster.
        '''
        self.dataPoints.append(dataPoint)
        
    def computeDistance(self, cluster, linkage='avg', distance='auto'):
        '''
        Computes the distance between from the current cluster to the given one.
        - linkage:     specifies the linkage method for the clustering:
            - 'avg':   average linkage
            - 'single': single linkage
            - 'complete': complete coverage. 
        - distance:    the distance measure. Currently supported:
            - 'euclid':     the euclidean distance
            - 'edit':       the edit (Levenshtein) distance
            - 'manh':       the Manhatten distance
          distance also might be a callable for custom distance metrics.
        '''
        dist = self._getDistanceMetrics(distance)
        
        if linkage == 'avg':
            totalDist = .0
            for p1 in self.dataPoints:
                for p2 in cluster.dataPoints:
                    totalDist += dist(p1, p2)
            totalDist /= float(len(self.dataPoints))
        elif linkage == 'single':
            totalDist = float('inf')
            for p1 in self.dataPoints:
                for p2 in cluster.dataPoints:
                    d = dist(p1, p2)
                    if d < totalDist: totalDist = d
        elif linkage == 'complete':
            totalDist = .0
            for p1 in self.dataPoints:
                for p2 in cluster.dataPoints:
                    d = dist(p1, p2)
                    if d > totalDist: totalDist = d
        else:
            raise Exception('Linkage "%s" not supported.' % linkage)
        return totalDist
    
    def merge(self, cluster):
        '''
        Merges this cluster with the given one. Returns a new cluster without
        modifying any of the original clusters.
        '''
        return Cluster(list(self.dataPoints) + list(cluster.dataPoints))
        
    def __repr__(self):
        s = 'ClUSTER: {%s}' % ','.join(self.dataPoints)
        return s
        
        
def SAHN(dataPoints, threshold=None, linkage='avg', dist='auto'):
    '''
    Performs sequential agglomerative hierarchical non-overlapping (SAHN) clustering.
    - dataPoints:     list of numerical or categorical data points.
    - threshold:      the threshold for cluster distances when the merging of
                      cluster shall stop. If threshold is None, the median
                      of the complete SAHN clustering will be taken.
    '''
    clusters = [Cluster([p]) for p in dataPoints]
    threshold2clusters = {}
    if threshold is None:
        thr = float('inf')
    else:
        thr = threshold
    while len(clusters) > 1:
        minDist = float('inf')
        for c1 in clusters:
            for c2 in clusters:
                if c1 is c2: continue
                d = c1.computeDistance(c2, linkage, dist)
                if d < minDist:
                    minDist = d
                    minDistC1 = c1
                    minDistC2 = c2
        if minDist > thr: break
        threshold2clusters[minDist] = list(clusters)
        newCluster = minDistC1.merge(minDistC2)
        clusters.remove(minDistC2)
        clusters.remove(minDistC1)
        clusters.append(newCluster)
    if threshold is None:
        # return the set of clusters associated to the median
        # (or the clostest smaller one, respectively)
        l = sorted(threshold2clusters, reverse=True)
        m = numpy.median(l)
        deltas = [abs(m - x) for x in l]
        clusters = threshold2clusters.get(l[deltas.index(min(deltas))])
    return clusters
    
def computeClosestCluster(dataPoint, clusters, linkage='avg', dist='auto'):
    '''
    Returns the closest cluster and its centroid to the given dataPoint.
    '''
    c1 = Cluster([dataPoint])
    minDist = float('inf')
    for c2 in clusters:
        d = c1.computeDistance(c2, linkage, dist)
        if d < minDist:
            minDist = d
            minDistC = c2
    return (minDistC, minDistC._computeCentroid(dist))
            
POS = 1
NEG = -1

class CorrelationClustering():
    '''
    Clustering based on similarity or correlation only, without having
    to represent the data points explicitly.
    '''
    
    def __init__(self, correlations, points, corr_matrix, thr=None):
        '''
        The data is given as a sequence of pairs ((d1,d2), corr(d1, d2)) representing
        pairs of data points and their correlation/similarity. Type of the data 
        points can be anything, but it must be ensured that instances representing the 
        same point have same hashes. 
        
            correlations:    the data to be clustered
            length:          the number of distinct data points
            thr:             threshold for correlation specifying a termination criterion
        
        Example:
        
            correlations = [(('a','b'), .2), (('b', 'c'), .7), ....]
        '''
        self.corr_matrix = corr_matrix
        # sort the points wrt to their absolute correlations
        sorted_data = sorted(correlations, key=lambda corr: abs(corr[1]), reverse=True)
        for data in sorted_data:
            print('%s = %f' % (list(map(str, data[0])), data[1]))
        # use as the default threashold the median of correlations
        if thr is None:
            thr = numpy.mean(numpy.array([abs(c[1]) for c in correlations])) * 2
        thr2 = .05
#         thr = 0
        self.clusters = defaultdict(set)
#         self.posclusters = defaultdict(set)#dict([(a, i+1) for i, a in enumerate(points)])
#         self.negclusters = defaultdict(set)#dict([(a, -i-1) for i, a in enumerate(points)])
        cluster2data = defaultdict(set)
        self.cluster2data = cluster2data
#         for clusters in (self.posclusters, self.negclusters):
#             for a, idx in clusters.iteritems(): 
#                 cluster2data[idx] = [a]
        self.counter = {POS: 0, NEG: 0}
        for i, ((d1, d2), corr) in enumerate(sorted_data):
            print(d1, d2, corr)
            if abs(corr) <= thr:# or remainder == 0: 
                break
            if corr < 0:
                posneg = NEG
#                 clusters = self.negclusters
            else:
                posneg = POS
#                 clusters = self.posclusters
            c1 = self.clusters[d1]#.get(d1)
            c2 = self.clusters[d2]#.get(d2)
            if not c1 and not c2:
                self.create_cluster(d1, d2, posneg)
            elif c1 and not c2:
                create_new = True
                for c in c1:
                    if self.avgcorr(d2, c) is None or self.avgcorr(d2, c) * corr > 0 and abs(self.avgcorr(d2, c) - corr) <= thr2: 
                        self.add_to_cluster(d2, c)
                        create_new = False
                if create_new:
                    self.create_cluster(d1, d2, posneg)
            elif not c1 and c2:
                create_new = True
                for c in c2:
                    if self.avgcorr(d1, c) is None or self.avgcorr(d1, c) * corr > 0 and abs(self.avgcorr(d1, c) - corr) <= thr2:
                        self.add_to_cluster(d1, c)
                        create_new = False
                if create_new:
                    self.create_cluster(d1, d2, posneg)
            elif c1 and c2:
                to_delete = set()
                for c1_, c2_ in combinations(c1 | c2, 2):
                    print('trying to merge (%s) and (%s)' % (self.strcluster(c1_), self.strcluster(c2_)))
                    if c1_ == c2_: continue
                    corr1 = self.avgcorr(d2, c1_)
                    corr2 = self.avgcorr(d1, c2_)
                    print('  %s ~ %s = %s' % (d2, self.strcluster(c1_), corr1))
                    print('  %s ~ %s = %s' % (d1, self.strcluster(c2_), corr2))
                    if corr1 is None or corr2 is None or abs(corr - corr1) <= thr2 and abs(corr - corr2) < thr2:
                        print('merging (%s) (%s) and (%s) (%s)' % (self.strcluster(c1_), c1_, self.strcluster(c2_), c2_))
                        self.merge_clusters(c2_, c1_)
                        to_delete.add(c1_)
                for c in to_delete:
                    print('removing cluster', c)
                    self.remove_cluster(c)
            print()
                        
#                 for d in list(cluster2data[c2]):
#                     clusters[d] = c1
#                     cluster2data[c1].add(d)
#                     cluster2data[c2].remove(d)
#                     if not cluster2data[c2]:
#                         del cluster2data[c2]
#         self.clusters = dict_union(self.posclusters, self.negclusters)
        
    def avgcorr(self, atom, cluster):
        atom_groups = defaultdict(list)
        for atom in self.cluster2data[cluster] | {atom}:
            atom_groups[self.corr_matrix.groups[atom]].append(atom)
        total = 0.
        count = 0
        for atom2 in self.cluster2data[cluster]:
            if atom_groups[atom] == atom_groups[atom2]: continue
            corr = self.corr_matrix[atom, atom2]
            if corr is not None:
                total += corr
                count += 1 
        if count == 0: return None
        return total / count
            
    def create_cluster(self, d1, d2, posneg):
        self.counter[posneg] += posneg # increment or decrement, depending on whether positively or negatively correlated
        print('creating', d1, d2, 'as', self.counter[posneg])
#         if posneg < 0:
#             clusters = self.negclusters
#         else:
#             clusters = self.posclusters
        self.clusters[d1].add(self.counter[posneg])
        self.clusters[d2].add(self.counter[posneg])
        self.cluster2data[self.counter[posneg]].update((d1, d2))
        
    def add_to_cluster(self, d, c):
        print('adding', d, 'to', c)
#         if c < 0: clusters = self.negclusters
#         else: clusters = self.posclusters
        self.clusters[d].add(c)
        self.cluster2data[c].add(d)
        
    def merge_clusters(self, c1, c2):
        assert c1 * c2 > 0
#         if c1 < 0: clusters = self.negclusters
#         else: clusters = self.posclusters
        for d in list(self.cluster2data[c2]):
            self.clusters[d].add(c1)
            self.cluster2data[c1].add(d)
                
    def remove_cluster(self, c):
#         if c < 0: clusters = self.negclusters
#         else: clusters = self.posclusters
        print(list(map(str, self.cluster2data[c])))
        for d in list(self.cluster2data[c]):
            print(d)
            print(list(map(str, self.clusters[d])), '->', end=' ')
            self.clusters[d].remove(c)
            print(list(map(str, self.clusters[d])))
        del self.cluster2data[c]
        
    def strcluster(self, c):
        return map(str, self.cluster2data[c])


class NoisyStringClustering(object):
    '''
    This transformer takes a set of strings and performs a clustering
    based on the edit distance. It transforms databases wrt to the clusters.
    '''

    def __init__(self, mln, domains, verbose=True):
        self.mln = mln
        self.domains = domains
        self.verbose = verbose
        self.clusters = {} # maps domain name -> list of clusters
        self.noisy_domains = {}
        self.log = getlogger('noisystr')

    def materialize(self, dbs):
        '''
        For each noisy domain, (1) if there is a static domain specification,
        map the values of that domain in all dbs to their closest neighbor
        in the domain.
        (2) If there is no static domain declaration, apply SAHN clustering
        to the values appearing dbs, take the cluster centroids as the values
        of the domain and map the dbs as in (1).
        '''
        fulldomains = mergedom(*[db.domains for db in dbs])
        for domain in self.domains:
            if fulldomains.get(domain, None) is None:
                continue
            # apply the clustering step
            values = fulldomains[domain]
            clusters = SAHN(values)
            self.clusters[domain] = clusters
            self.noisy_domains[domain] = [c._computeCentroid()[0] for c in clusters]
            if self.verbose:
                self.log.info('  reducing domain %s: %d -> %d values' % (domain, len(values), len(clusters)))
                self.log.info('   %s', str(self.noisy_domains[domain]))
        return self.transform_dbs(dbs)

    def transform_dbs(self, dbs):
        newdbs = []
        for db in dbs:
            common_doms = set(db.domains.keys()).intersection(set(self.domains))
            if len(common_doms) == 0:
                newdbs.append(db)
                continue
            newdb = db.copy()
            for domain in common_doms:
                # map the values in the database to the static domain values
                valmap = dict([(val, computeClosestCluster(val, self.clusters[domain])[1][0]) for val in newdb.domains[domain]])
                newdb.domains[domain] = valmap.values()
                # replace the affected evidences
                for ev in newdb.evidence.keys():
                    truth = newdb.evidence[ev]
                    _, pred, params = db.mln.logic.parse_literal(ev)
                    if domain in self.mln.predicate(pred).argdoms:  # domain is affected by the mapping
                        newdb.retract(ev)
                        newargs = [v if domain != self.mln.predicate(pred).argdoms[i] else valmap[v] for i, v in enumerate(params)]
                        atom = '%s%s(%s)' % ('' if truth else '!', pred, ','.join(newargs))
                        newdb << atom
            newdbs.append(newdb)
        return newdbs

            
if __name__ == '__main__':
    mln = MLN.load('/home/nyga/code/pracmln/examples/object-recognition/object-recognition.pracmln:object-detection.mln')
    dbs = Database.load(mln, '/home/nyga/code/pracmln/examples/object-recognition/object-recognition.pracmln:scenes-new.db')

    # do some plain clustering on texts
    s = ['otto', 'otte', 'obama', 'markov logic network', 'markov logic', 'otta', 'markov random field']
    s = set([val for db in Database.load(mln, '/home/nyga/code/pracmln/examples/object-recognition/object-recognition.pracmln:scenes-new.db') for val in db.domains['text']])
    clusters = SAHN(s)
    for c in clusters:
        print(c)

    # apply clustering to a set of databases
    cluster = NoisyStringClustering(mln, ['text'])
    cluster.materialize(dbs)

