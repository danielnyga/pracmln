# -*- coding: utf-8 -*-
#
# Markov Logic Networks
#
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

import re
import time
import logging
import traceback
import colored

from dnutils import out, ifnone

from collections import defaultdict
import random
from functools import reduce
from importlib import util as imputil

# math functions

USE_MPMATH = True

try:
    if not USE_MPMATH:
        raise Exception()
    if imputil.find_spec('mpmath') is not None:
        import mpmath  # @UnresolvedImport
        mpmath.mp.dps = 80
        from mpmath import exp, fsum, log  # @UnresolvedImport
except:
    from math import exp, log
    if imputil.find_spec('math', 'fsum') is not None:
        from math import fsum
    else:
        fsum = sum

from math import sqrt

import math

def crash(*args, **kwargs):
    out(*args, **edict(kwargs) + {'tb': kwargs.get('tb', 1) + 1})
    print(colorize('TERMINATING.', ('red', None, True), True))
    exit(-1)

def flip(value):
    '''
    Flips the given binary value to its complement.
    
    Works with ints and booleans. 
    '''
    if type(value) is bool:
        return True if value is False else False
    elif type(value) is int:
        return 1 - value
    else:
        TypeError('type {} not allowed'.format(type(value)))

def logx(x):
    if x == 0:
        return - 100
    return math.log(x) #used for weights -> no high precision (mpmath) necessary


def batches(i, size):
    batch = []
    for e in i:
        batch.append(e)
        if len(batch) == size: 
            yield batch
            batch = []
    if batch: yield batch
    

def rndbatches(i, size):
    i = list(i)
    random.shuffle(i)
    return batches(i, size)


def stripComments(text):
#     comment = re.compile(r'//.*?$|/\*.*?\*/', re.DOTALL | re.MULTILINE)
#     return re.sub(comment, '', text)
    # this is a more sophisticated regex to replace c++ style comments
    # taken from http://stackoverflow.com/questions/241327/python-snippet-to-remove-c-and-c-comments
    def replacer(match):
        s = match.group(0)
        if s.startswith('/'):
            return " " # note: a space and not an empty string
        else:
            return s
    pattern = re.compile(
        r'//.*?$|/\*.*?\*/|"(?:\\.|[^\\"])*"',
        re.DOTALL | re.MULTILINE
    )
    return re.sub(pattern, replacer, text)


def parse_queries(mln, query_str):
    '''
    Parses a list of comma-separated query strings.
    
    Admissible queries are all kinds of formulas or just predicate names.
    Returns a list of the queries.
    '''
    queries = []
    query_preds = set()
    q = ''
    for s in map(str.strip, query_str.split(',')):
        if not s: continue
        if q != '': q += ','
        q += s
        if balancedParentheses(q):
            try:
                # try to read it as a formula and update query predicates
                f = mln.logic.parse_formula(q)
                literals = f.literals()
                prednames = [lit.predname for lit in literals]
                query_preds.update(prednames)
            except:
                # not a formula, must be a pure predicate name 
                query_preds.add(s)
            queries.append(q)
            q = ''
    if q != '': raise Exception('Unbalanced parentheses in queries: ' + q)
    return queries

def predicate_declaration_string(predName, domains, blocks):
    '''
    Returns a string representation of the given predicate.
    '''
    args_list = ['{}{}'.format(arg, {True: '!', False: ''}[block]) for arg, block in zip(domains, blocks)]
    args = ', '.join(args_list)
    return '{}({})'.format(predName, args)


def getPredicateList(filename):
    ''' 
    Gets the set of predicate names from an MLN file 
    '''
    content = open(filename, "r").read() + "\n"
    content = stripComments(content)
    lines = content.split("\n")
    predDecl = re.compile(r"(\w+)\([^\)]+\)")
    preds = set()
    for line in lines:
        line = line.strip()
        m = predDecl.match(line)
        if m is not None:
            preds.add(m.group(1))
    return list(preds)

def avg(*a):
    return sum(map(float, a)) / len(a)


class CallByRef(object):
    '''
    Convenience class for treating any kind of variable as an object that can be
    manipulated in-place by a call-by-reference, in particular for primitive data types such as numbers.
    '''
    
    def __init__(self, value):
        self.value = value
        
INC = 1
EXC = 2


class Interval:
    
    def __init__(self, interval):
        tokens = re.findall(r'(\(|\[|\])([-+]?\d*\.\d+|\d+),([-+]?\d*\.\d+|\d+)(\)|\]|\[)', interval.strip())[0]
        if tokens[0] in ('(', ']'):
            self.left = EXC
        elif tokens[0] == '[':
            self.left = INC
        else:
            raise Exception('Illegal interval: {}'.format(interval))
        if tokens[3] in (')', '['): 
            self.right = EXC
        elif tokens[3] == ']':
            self.right = INC
        else:
            raise Exception('Illegal interval: {}'.format(interval))
        self.start = float(tokens[1]) 
        self.end = float(tokens[2])
        
    def __contains__(self, x):
        return (self.start <= x if self.left == INC else self.start < x) and (self.end >= x if self.right == INC else self.end > x)
        
    
def elapsedtime(start, end=None):
    '''
    Compute the elapsed time of the interval `start` to `end`.
    
    Returns a pair (t,s) where t is the time in seconds elapsed thus 
    far (since construction) and s is a readable string representation thereof.
    
    :param start:    the starting point of the time interval.
    :param end:      the end point of the time interval. If `None`, the current time is taken.
    '''
    if end is not None:
        elapsed = end - start
    else:
        elapsed = time.time() - start
    return elapsed_time_str(elapsed)
    
    
def elapsed_time_str(elapsed):
    hours = int(elapsed / 3600)
    elapsed -= hours * 3600
    minutes = int(elapsed / 60)
    elapsed -= minutes * 60
    secs = int(elapsed)
    msecs = int((elapsed - secs) * 1000)
    return '{}:{:02d}:{:02d}.{:03d}'.format(hours, minutes, secs, msecs)


def balancedParentheses(s):
    cnt = 0
    for c in s:
        if c == '(':
            cnt += 1
        elif c == ')':
            if cnt <= 0:
                return False
            cnt -= 1
    return cnt == 0
  
def fstr(f):
    s = str(f)
    while s[0] == '(' and s[ -1] == ')':
        s2 = s[1:-1]
        if not balancedParentheses(s2):
            return s
        s = s2
    return s


def cumsum(i, upto=None):
    return 0 if (not i or upto == 0) else reduce(int.__add__, i[:ifnone(upto, len(i))])


def evidence2conjunction(evidence):
    '''
    Converts the evidence obtained from a database (dict mapping ground atom names to truth values) to a conjunction (string)
    '''
    evidence = [("" if x[1] else "!") + x[0] for x in iter(list(evidence.items()))]
    return " ^ ".join(evidence)


def tty(stream):
    isatty = getattr(stream, 'isatty', None)
    return isatty and isatty()

BOLD = (None, None, True)
            
def headline(s):
    line = ''.ljust(len(s), '=')
    return '{}\n{}\n{}'.format(colorize(line, BOLD, True), colorize(s, BOLD, True), colorize(line, BOLD, True))


def gaussianZeroMean(x, sigma):
    return 1.0/sqrt(2 * math.pi * sigma**2) * math.exp(- (x**2) / (2 * sigma**2))


def gradGaussianZeroMean(x, sigma):
    return - (0.3990434423 * x * math.exp(-0.5 * x**2 / sigma**2) ) / (sigma**3)


def mergedom(*domains):
    ''' 
    Returning a new domains dictionary that contains the elements of all the given domains
    '''
    fullDomain = {}
    for domain in domains:
        for domName, values in list(domain.items()):
            if domName not in fullDomain:
                fullDomain[domName] = set(values)
            else:
                fullDomain[domName].update(values)
    for key, s in list(fullDomain.items()):
        fullDomain[key] = list(s)
    return fullDomain


def colorize(message, format, color=False):
    '''
    Returns the given message in a colorized format
    string with ANSI escape codes for colorized console outputs:
    - message:   the message to be formatted.
    - format:    triple containing format information:
                 (bg-color, fg-color, bf-boolean) supported colors are
                 'black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white'
    - color:     boolean determining whether or not the colorization
                 is to be actually performed.
    '''

    if color is False: return message
    (bg, fg, bold) = format
    params = []
    if bold:
        params.append(colored.attr('bold'))
    if bg:
        params.append(colored.bg(bg))
    if fg:
        params.append(colored.fg(fg))

    return colored.stylize(message, set(params))


class StopWatchTag:
    
    def __init__(self, label, starttime, stoptime=None):
        self.label = label
        self.starttime = starttime
        self.stoptime = stoptime
        
    @property
    def elapsedtime(self):
        return ifnone(self.stoptime, time.time()) - self.starttime 
    
    @property
    def finished(self):
        return self.stoptime is not None
    

class StopWatch(object):
    '''
    Simple tagging of time spans.
    '''
    
    
    def __init__(self):
        self.tags = {}
    
        
    def tag(self, label, verbose=True):
        if verbose:
            print('{}...'.format(label))
        tag = self.tags.get(label)
        now = time.time()
        if tag is None:
            tag = StopWatchTag(label, now)
        else:
            tag.starttime = now
        self.tags[label] = tag
    
    
    def finish(self, label=None):
        now = time.time()
        if label is None:
            for _, tag in list(self.tags.items()):
                tag.stoptime = ifnone(tag.stoptime, now)
        else:
            tag = self.tags.get(label)
            if tag is None:
                raise Exception('Unknown tag: {}'.format(label))
            tag.stoptime = now

    
    def __getitem__(self, key):
        return self.tags.get(key)

    
    def reset(self):
        self.tags = {}

        
    def printSteps(self):
        for tag in sorted(list(self.tags.values()), key=lambda ta: ta.starttime):
            if tag.finished:
                print('{} took {}'.format(colorize(tag.label, (None, None, True), True), elapsed_time_str(tag.elapsedtime)))
            else:
                print('{} is running for {} now...'.format(colorize(tag.label, (None, None, True), True), elapsed_time_str(tag.elapsedtime)))


def combinations(domains):
    if len(domains) == 0:
        raise Exception('domains mustn\'t be empty')
    return _combinations(domains, [])

def _combinations(domains, comb):
    if len(domains) == 0:
        yield comb
        return
    for v in domains[0]:
        for ret in _combinations(domains[1:], comb + [v]):
            yield ret
            
def deprecated(func):
    '''
    This is a decorator which can be used to mark functions
    as deprecated. It will result in a warning being emmitted
    when the function is used.
    '''
    def newFunc(*args, **kwargs):
        logging.getLogger().warning("Call to deprecated function: {}.".format(func.__name__))
        return func(*args, **kwargs)
    newFunc.__name__ = func.__name__
    newFunc.__doc__ = func.__doc__
    newFunc.__dict__.update(func.__dict__)
    return newFunc
            
def unifyDicts(d1, d2):
    '''
    Adds all key-value pairs from d2 to d1.
    '''
    for key in d2:
        d1[key] = d2[key]
        
def dict_union(d1, d2):
    '''
    Returns a new dict containing all items from d1 and d2. Entries in d1 are
    overridden by the respective items in d2.
    '''
    d_new = {}
    for key, value in list(d1.items()):
        d_new[key] = value
    for key, value in list(d2.items()):
        d_new[key] = value
    return d_new


def dict_subset(subset, superset):
    '''
    Checks whether or not a dictionary is a subset of another dictionary.
    '''
    return all(it in list(superset.items()) for it in list(subset.items()))


class edict(dict):
    
    def __add__(self, d):
        return dict_union(self, d)
    
    def __radd__(self, d):
        return self + d
    
    def __sub__(self, d):
        if type(d) in (dict, defaultdict):
            ret = dict(self)
            for k in d:
                del ret[k]
        else:
            ret = dict(self)
            del ret[d]
        return ret
    
    
class eset(set):
    
    def __add__(self, s):
        return set(self).union(s)
    

def item(s):
    '''
    Returns an arbitrary item from the given set `s`.
    '''
    if not s:
        raise Exception('Argument of type {} is empty.'.format(type(s).__name__))
    for it in s: break
    return it

class temporary_evidence:
    '''
    Context guard class for enabling convenient handling of temporary evidence in
    MRFs using the python `with` statement. This guarantees that the evidence
    is set back to the original whatever happens in the `with` block.
    
    :Example:
    
    >> with temporary_evidence(mrf, [0, 0, 0, 1, 0, None, None]) as mrf_:
    '''
    
    
    def __init__(self, mrf, evidence=None):
        self.mrf = mrf
        self.evidence_backup = list(mrf.evidence)
        if evidence is not None:
            self.mrf.evidence = evidence 
        
    def __enter__(self):
        return self.mrf
    
    def __exit__(self, exception_type, exception_value, tb):
        if exception_type is not None:
            traceback.print_exc()
            raise exception_type(exception_value)
        self.mrf.evidence = self.evidence_backup
        return True
        
        
        


    
if __name__ == '__main__':
    
    l = [1,2,3]
    upto = 2
    out(ifnone(upto, len(l)))
    out(l[:ifnone(upto, len(l))])
    out(cumsum(l,1))
    
#     d = edict({1:2,2:3,'hi':'world'})
#     print d
#     print d + {'bla': 'blub'}
#     print d
#     print d - 1
#     print d - {'hi': 'bla'}
#     print d
#     
