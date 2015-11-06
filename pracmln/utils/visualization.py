'''
Created on Sep 11, 2014

@author: nyga
'''

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import rc
import itertools
from numpy.ma.core import floor, ceil
from pracmln.mln.util import parse_queries, out
from pracmln.utils.latexmath2png import math2png


COLORS = ['blue', 'green', 'red', 'orange']
CVALUE = {'blue': '#355FD6',
          'green': '#47A544',
          'red': '#A54D44',
          'orange': '#D0742F'}

MARKERS = ['s', 'v', 'o', '^']

def plot_fscores(labels, series):
    length = max(map(len, series))
    fig = plt.figure()
    ax = fig.gca()
    ax.set_xticks(np.arange(0,float(len(series))), 1)
    ymin = min(map(min, series))
    ymax = max(map(max, series))
    ymin = floor(ymin * 10) / 10
    ymax = ceil(ymax * 10) / 10
    ax.set_yticks(np.arange(ymin,ymax,0.1))
    plt.axis([0, length-1, ymin, ymax])
    fontProperties = {'family':'sans-serif','sans-serif':['Helvetica'],
    'weight' : 'normal', 'size' : 20}
    rc('text', usetex=True)
    rc('font',**fontProperties)
    ax.set_xticklabels([r'$\frac{%d}{%d}$' % (i+1, length-i) for i in range(length)], fontProperties)
    plt.grid()
    for i, [l, s] in enumerate(zip(labels, series)):
        c = CVALUE[COLORS[i]]
        plt.plot(range(len(s)), s, '-', marker=MARKERS[i], color=c, linewidth=2.5, markersize=12, fillstyle='full', label=l)
    plt.legend(loc="best")
    plt.ylabel(r'$F_1$')
    plt.xlabel(r'$k$')
    
    
def plot_KLDiv_with_logscale(series):
    length = len(series)
    fig = plt.figure()
    ax = fig.gca()
    ax.set_xticks(np.arange(0,float(len(series))), 1)
    ymin = min(series)
    ymax = max(series)
    ymin = floor(ymin * 10) / 10
    ymax = ceil(ymax * 10) / 10
    ax.set_yticks(np.arange(ymin,ymax,0.1))
    plt.axis([0, length-1, ymin, ymax])
    fontProperties = {'family':'sans-serif','sans-serif':['Helvetica'],
    'weight' : 'normal', 'size' : 20}
    rc('text', usetex=True)
    rc('font',**fontProperties)
#     ax.set_xticklabels([r'$\frac{%d}{%d}$' % (i+1, length-i) for i in range(length)], fontProperties)
    plt.grid()
    a = plt.axes()#plt.axis([0, length-1, ymin, ymax])
    plt.yscale('log')
    
    c = CVALUE[COLORS[0]]
    m = MARKERS[0]
    plt.plot(range(len(series)), series, '-', marker=m, color=c, linewidth=2.5, markersize=12, fillstyle='full', label='Label')
    c = CVALUE[COLORS[1]]
    m = MARKERS[1]
    plt.plot(range(len(series)), series, '-', marker=m, color=c, linewidth=2.5, markersize=12, fillstyle='full', label='Label')
    
    plt.legend(loc="best")
    plt.ylabel(r'$F_1$')
    plt.xlabel(r'$k$')
    

def get_cond_prob_png(queries, dbs, filename='cond_prob', filedir='/tmp'):
    if isinstance(queries, str):
        queries = queries.split(',')

    declarations = r'''
    \DeclareMathOperator*{\argmin}{\arg\!\min}
    \DeclareMathOperator*{\argmax}{\arg\!\max}
    \newcommand{\Pcond}[1]{\ensuremath{P\left(\begin{array}{c|c}#1\end{array}\right)}}
    '''

    evidencelist = []
    if isinstance(dbs, list):
        for db in dbs:
            evidencelist.extend([e for e in db.evidence.keys() if db.evidence[e] == 1.0])
    else:
        evidencelist.extend([e if dbs.evidence[e] == 1.0 else '!'+e for e in dbs.evidence.keys() ])
    query    = r'''\\'''.join([r'''\text{{ {0} }} '''.format(q.replace('_', '\_')) for q in queries])
    evidence = r'''\\'''.join([r'''\text{{ {0} }} '''.format(e.replace('_', '\_')) for e in evidencelist])
    eq       = r'''\argmax \Pcond{{ \begin{{array}}{{c}}{0}\end{{array}} & \begin{{array}}{{c}}{1}\end{{array}} }}'''.format(query, evidence)

    return math2png(eq, filedir, declarations=[declarations], filename=filename, size=10)


if __name__ == '__main__':
#     fol = [[0.40, 0.41, 0.41, 0.42, 0.44, 0.49, 0.44, 0.46, 0.51],
#            [0.27, 0.29, 0.29, 0.32, 0.29, 0.34, 0.38, 0.36, 0.38],
#            [0.28, 0.30, 0.30, 0.31, 0.31, 0.34, 0.34, 0.34, 0.34],
#            [0.27, 0.28, 0.29, 0.29, 0.32, 0.32, 0.34, 0.34, 0.34],
#            [0.42, 0.43, 0.43, 0.44, 0.46, 0.45, 0.46, 0.53, 0.55],
#            [0.16, 0.16, 0.16, 0.16, 0.16, 0.16, 0.16, 0.16, 0.16]]
#     fuzzy = [[0.64, 0.69, 0.67, 0.68, 0.75, 0.75, 0.75, 0.75, 0.75],
#              [0.44, 0.50, 0.49, 0.51, 0.49, 0.52, 0.57, 0.56, 0.57],
#              [0.36, 0.49, 0.54, 0.48, 0.60, 0.56, 0.61, 0.61, 0.65],
#              [0.40, 0.51, 0.57, 0.62, 0.64, 0.64, 0.66, 0.66, 0.66],
#              [0.43, 0.48, 0.48, 0.50, 0.53, 0.50, 0.51, 0.51, 0.50],
#              [0.53, 0.79, 0.73, 0.77, 0.76, 0.83, 0.83, 0.82, 0.82]]
#     fol_avg = []
#     fuzzy_avg = []
#     for (fo, fu) in zip(zip(*fol), zip(*fuzzy)):
#         fol_avg.append(np.mean(fo))
#         fuzzy_avg.append(np.mean(fu))
#     print fol_avg
#     print fuzzy_avg
#     actioncore ='avg'
# #     actioncore = ['filling', 'add', 'slice', 'cutting', 'putting', 'stirring']
#     for (fo, fu, ac) in zip([fol_avg], [fuzzy_avg], actioncore):
#         plot_fscores(['FOL', 'Fuzzy'],[fo, fu])
#         plt.savefig('%s.pdf' % ac)

    kl = [1.1624788834,0.2733511075,0.0031577895,0.0032276985,0.0048089408,0.0014932027,0.0005206932,0.0006083846,3.61E-005,1.10E-005,3.16E-006,2.93E-006,5.44E-006,4.36E-006,2.94E-006,3.69E-006,1.52E-007,1.35E-007,1.35E-009,1.35E-007]
    plot_KLDiv_with_logscale(kl)
    plt.show()
