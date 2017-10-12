'''
Evaluation of sequence models - comparing obtained labels to ground truth
'''

from sys import argv,exit

def lagDist(x):
    #return float(x)/10
    return float(x**2)/25**2

def editDistance(s, t):
    '''Levenshtein distance between two strings/sequences'''
    d = [[0 for j in range(len(t)+1)] for i in range(len(s)+1)]
    for i in range(len(d)):
        d[i][0] = i 
    for j in range(len(t)+1):
        d[0][j] = j
    for j in range(1, len(t)+1):   
        for i in range(1, len(s)+1):
            if s[i-1] == t[j-1]:
                d[i][j] = d[i-1][j-1]
            else:
                d[i][j] = min(
                      d[i-1][j] + 1,  # deletion
                      d[i][j-1] + 1,  # insertion
                      d[i-1][j-1] + 1 # substitution
                    )
    return d[len(s)][len(t)]

def segmentify(s):
    ''' builds a list of segment labels from a list of frame labels '''
    segments = []
    prev = None
    for frame in s:
        if frame == prev:
            continue
        segments.append(frame)
        prev = frame
    return segments

def evalLabels(groundTruthFile, resultsFile, verbose=True):
    ret = {}
    
    labels1 = [int(float(x.strip())) for x in file(groundTruthFile).readlines()] # ground truth
    labels2 = [int(float(x.strip())) for x in file(resultsFile).readlines()] # classification
    i = 1
    numCorrect = 0
    dist = 0
    while i < len(labels1) and i < len(labels2):
        l1 = labels1[i]
        l2 = labels2[i]
        if l1 != l2:
            # determine (semantic) "edit distance"
            
            d1 = d2 = 1.0
            # classified labels change too late
            #   ground truth    11111222222
            #   classification  31111111122
            #                    l  k i  j
            j = k = l = i
            while j < len(labels2) and labels2[j] == l2: j += 1 # search for next label in classification
            while k > 0 and labels1[k] == l1: k -= 1 # search for previous label in ground truth (-> must be equal to current label)
            while l > 0 and labels2[l] == l2: l -= 1 # search for segment start in classification
            if j < len(labels2) and labels2[j] == l1 and labels1[k] == l2 and l < k:
                lag = j-i
                d1 = lagDist(lag)
            # classified labels change too early
            #   ground truth    1111122222
            #   classification  1222222223
            #                   j i  k   l
            j = k = l = i
            while j > 0 and labels2[j] == l2: j -= 1 # previous label in classification (-> must match current label in ground truth)
            while k < len(labels1) and labels1[k] == l1: k += 1 # next label in ground truth (-> must match current label in classification)
            while l < len(labels2) and labels2[l] == l2: l += 1 # next segment start in classification
            if j >= 0 and k < len(labels1) and labels2[j] == l1 and labels1[k] == l2 and l > k:
                lag = i-j
                d2 = lagDist(lag)
            # regular error
            d = min(d1,d2,1.0)
            
            if verbose: print("%d: %d should have been %d [d=%.2f]" % (i,l2,l1,d))
        else:
            d = 0
            if verbose: print("%d: %d" % (i,l1))
            numCorrect += 1
        dist += d
        i += 1
    i -= 1
    
    ret["perFrameErrors"] =  i-numCorrect
    ret["perFrameAccuracy"] = float(numCorrect)/i*100
    ret["semanticErrors"] = dist
    ret["semanticAccuracy"] = (i-dist)/i*100
    if verbose:    
        print("\n\n*** Per-Frame Accuracy ***\n")
        print("errors: %d" % ret["perFrameErrors"])
        print("correct: %d/%d (%f%%)" % (numCorrect, i, ret["perFrameAccuracy"]))
        
        print("\n\n*** Semantic Distance ***\n")
        print("semantic distance: %f   implied accuracy: %f%%" % (ret["semanticErrors"], ret["semanticAccuracy"]))
    
    # segment-level comparisons
    segs1 = segmentify(labels1[:len(labels2)])
    segs2 = segmentify(labels2)
    ret["segmentsEditDist"] = dist = editDistance(segs1, segs2)
    ret["segmentsAccuracy"] = accuracy = 100.0 - (float(dist) * 100.0 / len(segs2))
    if verbose:
        print("\n\n*** Segment-Level Edit Distance ***\n")
        print("identified segments: %d" % len(segs2))
        print(segs2)
        print("true segments: %d" % len(segs1))
        print(segs1)
        print("\nedit distance at segment level: %d  (implied accuracy %d/%d = %f%%)\n\n" % (dist, len(segs2)-dist, len(segs2), accuracy))
    
    return ret

if __name__ == '__main__':
    if len(argv) != 3:
        print("usage: evalSeqLabels <ground truth file> <classified file>")
        exit(1)
    evalLabels(argv[1], argv[2])
