# Weighted Constraint Satisfaction Problems -- Representation and Solving
#
# (C) 2012-2015 by Daniel Nyga (nyga@cs.uni-bremen.edu)
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

import sys
import os
from subprocess import Popen, PIPE
import bisect
import re
from collections import defaultdict
import _thread
import platform

from dnutils import logs

from ..utils import locs
from ..mln.errors import NoConstraintsError
import tempfile
from functools import reduce


logger = logs.getlogger(__name__)


class MaxCostExceeded(Exception): pass

toulbar_version = '0.9.7.0'

def is_executable_win(program):
    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    if not program.endswith('.exe'):
        program += '.exe'
    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

    return None

def is_executable_unix(path):
    if os.path.exists(path) and os.access(path, os.X_OK):
        return path
    else:
        return None

def is_executable(path):
    return is_executable_unix(path) or is_executable_win(path)


def toulbar2_path():
    (osname, _, _, _, arch, _) = platform.uname()
    execname = 'toulbar2'
    en = is_executable(execname)
    if en is not None: # use the version in PATH if it can be found
        return en
    # fallback: try to load shipped toulbar2 binary
    if osname == 'Windows': execname += '.exe'
    return os.path.join('3rdparty', 'toulbar2-{}'.format(toulbar_version), arch, osname, execname)


# Globally check if the toulbar2 executable can be found when
# this module is loaded. Print a warning if not.
_tb2path = os.path.join(locs.app_data, toulbar2_path())

if not is_executable(_tb2path):
    logger.error('toulbar2 was expected to be in {} but cannot be found. WCSP inference will not be possible.\n'.format(_tb2path))


class Constraint(object):
    '''
    Represents a a constraint in WCSP problem consisting of
    a range of variables (indices), a set tuples with each
    assigned costs and default costs. Costs are either a real
    valued non-negative weight or the WCSP.TOP constant
    indicating global inconsistency.
    
    :member tuples:     dictionary mapping a tuple to int (the costs)
    :member defcost:    the default cost of this constraint
    :param variables:   list of indices that identify the range of this constraint
    :param tuples:      (optional) list of tuples, where the last element of each
                        tuple specifies the costs for this assignment.
    :param defcost:     the default costs (if none of the tuples apply).
    '''
    
    def __init__(self, variables, tuples=None, defcost=0):
        self.tuples = dict()
        if tuples is not None:
            for t in tuples:
                self.tuples[tuple(t[:-1])] = t[-1]
        self.defcost = defcost
        self.variables = variables
        
        
    def tuple(self, t, cost):
        '''
        Adds a tuple to the constraint. A value in the tuple corresponds to the
        index of the value in the domain of the respective variable.
        '''
        if not len(t) == len(self.variables):
            print('tuple:', t)
            print('vars:', self.variables)
            raise Exception('List of variables and tuples must have the same length.')
        self.tuples[tuple(t)] = cost
    
    
    def write(self, stream=sys.stdout.buffer):
        stream.write('{} {} {} {}\n'.format(len(self.variables), ' '.join(map(str, self.variables)), self.defcost, len(self.tuples)).encode())
        for t in list(self.tuples.keys()):
            stream.write('{} {}\n'.format(' '.join(map(str, t)), self.tuples[t]).encode())
            
            
    def __eq__(self, other):
        eq = set(self.variables) == set(other.variables)
        eq = eq and self.defcost == other.defcost
        eq = eq and self.tuples == other.tuples
        return eq


class WCSP(object):
    '''
    Represents a WCSP problem.
    
    This class implements a wrapper around the `toulbar2` weighted-SAT solver.
    
    :member name:        (arbitrary) name of the problem
    :member domsizes:    list of domain sizes
    :member top:         maximal costs (entirely inconsistent worlds)
    :member constraints: list of :class:`Constraint` objects
    '''
    
    # maximum costs imposed by toulbar
    MAX_COST = 1537228672809129301
    

    def __init__(self, name=None, domsizes=None, top=-1):
        self.name = name
        self.domsizes = domsizes
        self.top = top
        self.constraints = {}
    
    
    def constraint(self, constraint):
        '''
        Adds the given constraint to the WCSP. If a constraint 
        with the same scope already exists, the tuples of the
        new constraint are merged with the existing ones.
        '''
        varindices = constraint.variables
        cold = self.constraints.get(tuple(sorted(varindices)))
        if cold is not None:
            c_ = Constraint(cold.variables, defcost=constraint.defcost)
            for t, cost in constraint.tuples.items():
                t = [t[constraint.variables.index(v)] for v in cold.variables]
                c_.tuple(t, cost)
            constraint = c_
            varindices = constraint.variables
            
            # update all the tuples of the old constraint with the tuples of the new constraint
            for t, cost in constraint.tuples.items():
                oldcost = cold.tuples.get(t, None)
                # if the tuple has caused maximal costs in the old constraint, it must also cause maximal costs in the
                # merged one. Or if the tuple was not part of the old constraint and the defcosts were maximal.
                if oldcost == self.top or oldcost is None and cold.defcost == self.top: continue
                # add the tuple costs of the new constraint or make them top if it's top in the new constraint
                if oldcost is not None:
                    cold.tuple(t, self.top if cost == self.top else (cost + oldcost))
                # add the tuple costs of the new constraint if the tuple is not conatined in the old one
                # or make them top if the tuple has maximal costs in the new constraint
                else:
                    cold.tuple(t, self.top if cost == self.top else (cost + cold.defcost))
                    
            # update the default costs of the old constraint
            if constraint.defcost != 0:# and cold.defcost != self.top:
                # all tuples that are part of the old constraint but not of the new constraint
                # have to be added the default costs of the new constraint, or made tops cost
                # in case the defcosts of the new constraint are top
                for t in [x for x in cold.tuples if x not in constraint.tuples]:
                    oldcost = cold.tuples[t]
                    if oldcost != self.top:
                        cold.tuple(t, self.top if constraint.defcost == self.top else (oldcost + constraint.defcost))
                # for all tuples that are neither in the old nor the new constraint, the default costs
                # have to be updated by the sum of the two defcosts, or tops if defcosts of the new constraint are tops.
                if cold.defcost != self.top:
                    cold.defcost = self.top if constraint.defcost == self.top else (cold.defcost + constraint.defcost)
            # if the constraint is fully specified by its tuples,
            # simplify it by introducing default costs
            if reduce(lambda x, y: x * y, [self.domsizes[x] for x in varindices]) == len(cold.tuples):
                cost2assignments = defaultdict(list)
                for t, c in cold.tuples.items():
                    cost2assignments[c].append(t)
                defaultCost = max(cost2assignments, key=lambda x: len(cost2assignments[x]))
                del cost2assignments[defaultCost]
                cold.defcost = defaultCost
                cold.tuples = {}
                for cost, tuples in cost2assignments.items():
                    for t in tuples: cold.tuple(t, cost)
        else:
            self.constraints[tuple(sorted(varindices))] = constraint
        
        
    def write(self, stream=sys.stdout.buffer):
        '''
        Writes the WCSP problem in WCSP format into an arbitrary stream
        providing a write method.
        '''
        self._make_integer_cost()
        stream.write('{} {} {} {} {}\n'.format(self.name, len(self.domsizes), max(self.domsizes), len(self.constraints), int(self.top)).encode())
        stream.write('{}\n'.format(' '.join(map(str, self.domsizes))).encode())
        for c in list(self.constraints.values()):
            stream.write('{} {} {} {}\n'.format(len(c.variables), ' '.join(map(str, c.variables)), c.defcost, len(c.tuples)).encode())
            for t in list(c.tuples.keys()):
                stream.write('{} {}\n'.format(' '.join(map(str, t)), int(c.tuples[t])).encode())
        
        
    def read(self, stream):
        '''
        Loads a WCSP problem from an arbitrary stream. Must be in the WCSP format.
        '''
        tuplesToRead = 0
        for i, line in enumerate(stream.readlines()):
            tokens = line.split()
            if i == 0:
                self.name = tokens[0]
                self.top = int(tokens[-1])
            elif i == 1:
                self.domsizes = list(map(int, tokens))
            else:
                if tuplesToRead == 0:
                    tuplesToRead = int(tokens[-1])
                    variables = list(map(int, tokens[1:-2]))
                    defcost = int(tokens[-2])
                    constraint = Constraint(variables, defcost=defcost)
                    self.constraints.append(constraint)
                else:
                    constraint.tuple(list(map(int,tokens[0:-1])), int(tokens[-1]))
                    tuplesToRead -= 1
                    
                    
    def _compute_divisor(self):
        '''
        Computes a divisor for making all constraint costs integers.
        '''
        # store all costs in a sorted list
        costs = []
        minWeight = None
        if len(self.constraints) == 0:
            raise NoConstraintsError('There are no satisfiable constraints.')
        for constraint in list(self.constraints.values()):
            for value in [constraint.defcost] + list(constraint.tuples.values()):
                if value == self.top: continue
                value = eval('{:.6f}'.format(value))
                if value in costs:
                    continue
                bisect.insort(costs, value)
                if (minWeight is None or value < minWeight) and value > 0:
                    minWeight = value
        # no smallest real-valued weight -> all constraints are hard
        if minWeight is None: 
            return None
        # compute the smallest difference between subsequent costs
        deltaMin = None
        w1 = costs[0]
        if len(costs) == 1:
            deltaMin = costs[0]
        for w2 in costs[1:]:
            diff = w2 - w1
            if deltaMin is None or diff < deltaMin:
                deltaMin = diff
            w1 = w2
        divisor = 1.0
        if minWeight < 1.0:
            divisor *= minWeight
        if deltaMin < 1.0:
            divisor *= deltaMin
        return divisor
    
    
    def _compute_hardcost(self, divisor):
        '''
        Computes the costs for hard constraints that determine
        costs for entirely inconsistent worlds (0 probability).
        '''
        if divisor is None:
            return 1
        costSum = int(0)
        for constraint in list(self.constraints.values()):
            maxCost = max([constraint.defcost] + list(constraint.tuples.values()))
            if maxCost == self.top or maxCost == 0.0: continue
            cost = abs(int(maxCost / divisor))
            newSum = costSum + cost
            if newSum < costSum:
                raise Exception("Numeric Overflow")
            costSum = newSum
        top = costSum + 1
        if top < costSum:
            raise Exception("Numeric Overflow")
        if top > WCSP.MAX_COST:
            logger.critical('Maximum costs exceeded: {} > {}'.format(top, WCSP.MAX_COST))
            raise MaxCostExceeded()
        return int(top)
    
    
    def _make_integer_cost(self):
        '''
        Returns a new WCSP problem instance, which is semantically
        equivalent to the original one, but whose costs have been converted
        to integers.
        '''
#         wcsp_ = copy.copy(self)
        if self.top != -1: return
        divisor = self._compute_divisor()
        top = self._compute_hardcost(divisor)
        for constraint in list(self.constraints.values()):
            if constraint.defcost == self.top:
                constraint.defcost = top
            else:
                constraint.defcost = 0 if divisor is None else int(float(constraint.defcost) / divisor)
            for tup, cost in constraint.tuples.items():
                if cost == self.top:
                    constraint.tuples[tup] = top
                else:
                    constraint.tuples[tup] = 0 if divisor is None else int(float(cost) / divisor)
        self.top = top
    
                    
    def itersolutions(self):
        '''
        Iterates over all (intermediate) solutions found.
        
        Intermediate solutions are sound variable assignments that may not necessarily
        be gloabally optimal.
        
        :returns:    a generator of (idx, solution) tuples, where idx is the index and solution is a tuple
                     of variable value indices.
        '''
        if not is_executable(_tb2path):
            raise Exception('toulbar2 cannot be found.')
        # append the process id to the filename to make it "process safe"
        tmpfile = tempfile.NamedTemporaryFile(prefix=os.getpid(), suffix='.wcsp', delete=False)
        wcspfilename = tmpfile.name
        self.write(stream=tmpfile)
        tmpfile.close()
        cmd = '%s -s -a %s' % (_tb2path, wcspfilename)
        logger.debug('solving WCSP...')
        p = Popen(cmd, shell=True, stderr=PIPE, stdout=PIPE)
        solution = None
        while True:
            l = p.stdout.readline().strip()
            if not l: break
            m = re.match(r'(\d+)\s+solution:([\s\d]+)', l) 
            if m is not None:
                num = m.group(1)
                solution = list(map(int, m.group(2).strip().split()))
                yield (num, solution)
        p.wait()        
        logger.debug('toulbar2 process returned {}'.format(str(p.returncode)))
        try:
            os.remove(wcspfilename)
        except OSError:
            logger.warning('could not remove temporary file {}'.format(wcspfilename))
        if p.returncode != 0:
            raise Exception('toulbar2 returned a non-zero exit code: {}'.format(p.returncode))


    def solve(self):
        '''
        Uses toulbar2 inference. Returns the best solution, i.e. a tuple
        of variable assignments.
        '''
        if not is_executable(_tb2path):
            raise Exception('toulbar2 cannot be found.')
        # append the process id to the filename to make it "process safe"
        tmpfile = tempfile.NamedTemporaryFile(prefix='{}-{}'.format(os.getpid(), _thread.get_ident()), suffix='.wcsp', delete=False)
        wcspfilename = tmpfile.name
        self.write(stream=tmpfile)
        tmpfile.close()
        cmd = '"%s" -s %s' % (_tb2path, wcspfilename)
        logger.debug('solving WCSP...')
        p = Popen(cmd, shell=True, stderr=PIPE, stdout=PIPE)
        solution = None
        nextLineIsSolution = False
        cost = None
        while True:
            l = p.stdout.readline()
            if not l: break
            if l.startswith(b'New solution'):
                cost = int(l.split()[2])
                nextLineIsSolution = True
                continue
            if nextLineIsSolution:
                solution = list(map(int, l.split()))
                nextLineIsSolution = False
        p.wait()
        logger.debug('toulbar2 process returned {}'.format(str(p.returncode)))
        try:
            os.remove(wcspfilename)
        except OSError:
            logger.warning('could not remove temporary file {}'.format(wcspfilename))
        if p.returncode != 0:
            raise Exception('toulbar2 returned a non-zero exit code: {}'.format(p.returncode))
        return solution, cost


# main function for debugging only
if __name__ == '__main__':
    wcsp = WCSP()
    wcsp.read(open('/home/nyga/code/test/nqueens.wcsp', 'rb'))
    for i, s in wcsp.itersolutions():
        print(i, s)
    print('best solution:', wcsp.solve())
