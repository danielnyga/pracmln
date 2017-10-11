# 
# First-Order Logic -- Satisfiability Reasoning
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


def DPLL(clauses):
    """
    Implementation of the Davis-Putnam-Logemann-Loveland (DPLL) algorithm for 
    proving satisfiability of a sentence in CNF in propositional logic.
    Returns True iff clauses is satisfiable, or False otherwise.
    - clauses:     A Set of clauses, i.e. a list of sets of literals. Literals
                   are strings, a literal is considered having negative polarity
                   if it starts with "!".
    """
    # check for empty clauses first and collect unit clauses
    unitClauses = set()
    pureLiterals = set()
    polarities = {}
    atoms = set()
    satisfiable = True
#     print 'enter with', clauses
    for clause in clauses:
        if len(clause) == 0:
#             print 'empty clause => backtracking'
            return False
        elif len(clause) == 1:
            for l in clause: break
            unitClauses.add(l)
        for lit in clause:
            (pol, atom) = (False, lit[1:]) if lit[0] == '!' else (True, lit)
            if not atom in polarities:
                pureLiterals.add(lit)
            pureLit = polarities.get(atom, pol) == pol
            satisfiable = satisfiable and pureLit
            polarities[atom] = pol
            if not pureLit:
                try: pureLiterals.remove(lit[1:] if lit[0] == '!' else '!%s' % lit)
                except: pass
#     print 'pureLits:', pureLiterals
    if satisfiable: return True
    # do unit propagation
    newClauses = []
    for clause in clauses:
        skipClause = False
        newClause = set(clause)
        for uc in unitClauses:
#             print 'UP %s / %s ->' % (uc, str(newClause)),
            if set([uc]) == newClause: 
                skipClause = True
#                 print 'True'
                break
            (ucPol, ucAtom) = (False, uc[1:]) if uc[0] == '!' else (True, uc)
            for l in set(newClause):
                (pol, atom) = (False, l[1:]) if l[0] == '!' else (True, l)
                if atom == ucAtom:
                    if pol == ucPol: 
                        skipClause = True
#                         print 'True'
                        break
                    else: newClause.remove(l)
                else: newClause.add(l)
            if skipClause: break
#             print newClause
        if skipClause: continue
        newClauses.append(newClause)
#     print newClauses, 'after UP'
    # do pure literal elimination
    for lit in pureLiterals:
        for clause in newClauses:
            if lit in clause:
                newClauses.remove(clause)
#     print newClauses, 'after PLE'
    
    atom = None
    if len(newClauses) == 0:
        return True
    for c in newClauses:
        for l in c:
            atom =  l[1:] if l[0] == '!' else l
            break
    if atom is None: return False
    return DPLL(newClauses + [set([atom])]) or DPLL(newClauses + [set(['!%s' % atom])])


if __name__ == '__main__':

    # this is the unicorn example from the AI class
    c1 = set(['!M', 'U'])
    c2 = set(['M', '!U'])
    c3 = set(['M', 'S'])
    c4 = set(['!U', 'H'])
    c5 = set(['!S', 'H'])
    c6 = set(['!H', 'G'])
    c7 = set(['!M'])
#     c7 = set(['!G'])
    cnf = [c1, c2, c3, c4, c5, c6, c7]
    print(DPLL(cnf))
                
            
            
    
        
    
    
    