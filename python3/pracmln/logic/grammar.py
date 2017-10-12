# -*- coding: utf-8 -*-
# FIRST-ORDER LOGIC -- PARSING AND GRAMMAR
#  
# (C) 2013 by Daniel Nyga (nyga@cs.uni-bremen.de)
# (C) 2007-2012 by Dominik Jain
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

from pyparsing import *
import re


class TreeBuilder(object):
    """
    The parsing tree.
    """
    
    def __init__(self, logic):
        self.logic = logic
        self.reset()
    
    def trigger(self, a, loc, toks, op):
        if op == 'litgroup':
            negated = False
            if toks[0] == '!' or toks[0] == '*':
                if toks[0] == '*':
                    negated = 2
                else:
                    negated = True
                toks = toks[1]
            else:
                toks = toks[0]
            self.stack.append(self.logic.litgroup(negated, toks[:-1], toks[-1], self.logic.mln))
        if op == 'lit':
            negated = False
            if toks[0] == '!' or toks[0] == '*':
                if toks[0] == '*':
                    negated = 2
                else:
                    negated = True
                toks = toks[1]
            else:
                toks = toks[0]
            self.stack.append(self.logic.lit(negated, toks[0], toks[1], self.logic.mln))
        elif op == '!':
            if len(toks) == 1:
                formula = self.logic.negation(self.stack[-1:], self.logic.mln)
                self.stack = self.stack[:-1]
                self.stack.append(formula)
        elif op == '=':
            if len(toks) == 2:
                self.stack.append(self.logic.equality(list(toks), False, self.logic.mln))
        elif op == '!=':
            if len(toks) == 2:
                self.stack.append(self.logic.equality(list(toks), True, self.logic.mln))
        elif op == '^':
            if len(toks) > 1:
                formula = self.logic.conjunction(self.stack[-len(toks):], self.logic.mln)
                self.stack = self.stack[:-len(toks)]
                self.stack.append(formula)
        elif op == 'v':
            if len(toks) > 1:
                formula = self.logic.disjunction(self.stack[-len(toks):], self.logic.mln)
                self.stack = self.stack[:-len(toks)]

                self.stack.append(formula)
        elif op == '=>':
            if len(toks) == 2:
                children = self.stack[-2:]
                self.stack = self.stack[:-2]
                self.stack.append(self.logic.implication(children, self.logic.mln))
        elif op == '<=>':
            if len(toks) == 2:
                children = self.stack[-2:]
                self.stack = self.stack[:-2]
                self.stack.append(self.logic.biimplication(children, self.logic.mln))
        elif op == 'ex':
            if len(toks) == 2:
                formula = self.stack.pop()
                variables = list(map(str, toks[0]))
                self.stack.append(self.logic.exist(variables, formula, self.logic.mln))
        elif op == 'count':
            if len(toks) in (3,4):                
                pred, pred_params = toks[0]
                if len(toks) == 3:
                    fixed_params, op, count = [], toks[1], int(toks[2])
                else:
                    fixed_params, op, count = list(toks[1]), toks[2], int(toks[3])
                self.stack.append(self.logic.count_constraint(pred, pred_params, fixed_params, op, count))
        return self.stack[-1]
        
    def reset(self):
        self.stack = []
                
    def getConstraint(self):
        if len(self.stack) > 1:
            raise Exception("Not a valid formula - reduces to more than one element %s" % str(self.stack))
        if len(self.stack) == 0:
            raise Exception("Constraint could not be parsed")
#         if not isinstance(self.stack[0], Logic.Constraint):
#             raise Exception("Not an instance of Constraint!")
        return self.stack[0]


# ======================================================================================
# Grammar implementations
# ======================================================================================

class Grammar(object):
    """
    Abstract super class for all logic grammars.
    """
    
    
    def __deepcopy__(self, memo):
        return self
    
    def parse_formula(self, s):
        self.tree.reset()
        self.formula.parseString(s)
        constr = self.tree.getConstraint()
        return constr
    
    def parse_atom(self, string):
        """
        Parses a predicate such as p(A,B) and returns a tuple where the first item 
        is the predicate name and the second is a list of parameters, e.g. ("p", ["A", "B"])
        """
        m = re.match(r'(\w+)\((.*?)\)$', string)
        if m is not None:
            return (m.group(1), list(map(str.strip, m.group(2).split(","))))
        raise Exception("Could not parse predicate '%s'" % string)
    
    def parse_predicate(self, s):
        return self.predDecl.parseString(s)[0]
    
    def isvar(self, identifier):
        raise Exception('%s does not implement isvar().' % str(type(self)))
    
    def isconstant(self, identifier):
        return not self.isVar(identifier)
    
    def istemplvar(self, s):
        return s[0] == '+' and self.isvar(s[1:])
    
    def parse_domain(self, s):
        """
        Parses a domain declaration and returns a tuple (domain name, list of constants)
        Returns None if it cannot be parsed.
        """
        m = re.match(r'(\w+)\s*=\s*{(.*?)}', s)
        if m == None:
            return None
#             raise Exception("Could not parse the domain declaration '%s'" % line)
        return (m.group(1), list(map(str.strip, m.group(2).split(','))))
    
    def parse_literal(self, s):
        """
        Parses a literal such as !p(A,B) or p(A,B)=False and returns a tuple 
        where the first item is whether the literal is true, the second is the 
        predicate name and the third is a list of parameters, e.g. (False, "p", ["A", "B"])
        """
        # try regular MLN syntax
        self.tree.reset()
        try:
            lit = self.literal.parseString(s)
        except ParseException:
            raise Exception('unable to parse string', s)
        lit = self.tree.getConstraint()
        return (not lit.negated, lit.predname, lit.args)
#         m = re.match(r'(!?)(\w+)\((.*?)\)$', s)
#         if m is not None:
#             return (m.group(1) != "!", m.group(2), map(str.strip, m.group(3).split(",")))
#         raise Exception("Could not parse literal '%s'" % s)

    
class StandardGrammar(Grammar):
    """
    The standard MLN logic syntax.
    """
    
    def __init__(self, logic):
        identifierCharacter = alphanums + '_' + '-' + "'"
        lcCharacter = alphas.lower()
        ucCharacter = alphas.upper()
        lcName = Word(lcCharacter, alphanums + '_')
        
        openRB = Literal("(").suppress()
        closeRB = Literal(")").suppress()
        
        domName = Combine(Optional(Literal(':')) + lcName + Optional(Literal('!') | Literal('?')))
        
        constant = Word(identifierCharacter) | Word(nums) | Combine(Literal('"') + Word(printables.replace('"', '')) + Literal('"'))
        variable = Word(lcCharacter, identifierCharacter)
        
        atomArgs = Group(delimitedList(constant | Combine(Optional("+") + variable)))
        predDeclArgs = Group(delimitedList(domName))
        
        predName = Word(identifierCharacter)
        
        atom = Group(predName + openRB + atomArgs + closeRB)
        literal = Optional(Literal("!") | Literal("*")) + atom
        gndAtomArgs = Group(delimitedList(constant))
        gndLiteral = Optional(Literal("!")) + Group(predName + openRB + gndAtomArgs + closeRB)
        predDecl = Group(predName + openRB + predDeclArgs + closeRB) + StringEnd()
        
        varList = Group(delimitedList(variable))
        count_constraint = Literal("count(").suppress() + atom + Optional(Literal("|").suppress() + varList) + Literal(")").suppress() + (Literal("=") | Literal(">=") | Literal("<=")) + Word(nums)
        
        formula = Forward()
        exist = Literal("EXIST ").suppress() + Group(delimitedList(variable)) + openRB + Group(formula) + closeRB
        equality = (constant|variable) + Literal("=").suppress() + (constant|variable)
        inequality = (constant|variable) + Literal('=/=').suppress() + (constant|variable)
        negation = Literal("!").suppress() + openRB + Group(formula) + closeRB
        item = literal | exist | equality | openRB + formula + closeRB | negation
        disjunction = Group(item) + ZeroOrMore(Literal("v").suppress() + Group(item))
        conjunction = Group(disjunction) + ZeroOrMore(Literal("^").suppress() + Group(disjunction))
        implication = Group(conjunction) + Optional(Literal("=>").suppress() + Group(conjunction))
        biimplication = Group(implication) + Optional(Literal("<=>").suppress() + Group(implication))
        constraint = biimplication | count_constraint
        formula << constraint
    
        def lit_parse_action(a, b, c): tree.trigger(a,b,c,'lit')
        def gndlit_parse_action(a, b, c): tree.trigger(a,b,c,'gndlit')
        def neg_parse_action(a, b, c): tree.trigger(a,b,c,'!')
        def disjunction_parse_action(a, b, c): tree.trigger(a,b,c,'v')
        def conjunction_parse_action(a, b, c): tree.trigger(a,b,c,'^')
        def exist_parse_action(a, b, c): tree.trigger(a,b,c,"ex")
        def implication_parse_action(a, b, c): tree.trigger(a,b,c,"=>")
        def biimplication_parse_action(a, b, c): tree.trigger(a,b,c,"<=>")
        def equality_parse_action(a, b, c): tree.trigger(a,b,c,"=")
        def inequality_parse_action(a, b, c): tree.trigger(a,b,c,"!=")
        def count_constraint_parse_action(a, b, c): tree.trigger(a,b,c,'count')
        

        tree = TreeBuilder(logic)
        literal.setParseAction(lit_parse_action)
        gndLiteral.setParseAction(gndlit_parse_action)
        negation.setParseAction(neg_parse_action)
        disjunction.setParseAction(disjunction_parse_action)
        conjunction.setParseAction(conjunction_parse_action)
        exist.setParseAction(exist_parse_action)
        implication.setParseAction(implication_parse_action)
        biimplication.setParseAction(biimplication_parse_action)
        equality.setParseAction(equality_parse_action)
        inequality.setParseAction(inequality_parse_action)
        count_constraint.setParseAction(count_constraint_parse_action)
        
        self.tree = tree
        self.formula = formula + StringEnd()
        self.predDecl = predDecl
        self.literal = literal
        
    def isvar(self, identifier):
        return identifier[0].islower() or identifier[0] == '+'
            

class PRACGrammar(Grammar):
    """
    The specialized PRAC MLN grammar supporting infix not-equals and
    arbitrary constants. Variables need to start with '?'
    """
    
    def __init__(self, logic):
        # grammar
        
        identifierCharacter = alphanums + 'ÄÖÜäöü' + '_' + '-' + "'" + '.' + ':' + ';' + '$' + '~' + '\\' + '!' + '/'
        lcCharacter = alphas.lower()
        ucCharacter = alphas.upper()
        lcName = Word(lcCharacter, alphanums + '_')
        qMark = '?'

        openRB = Literal('(').suppress()
        closeRB = Literal(')').suppress()
        openSB = Literal('[').suppress()
        closeSB = Literal(']').suppress()

        domName = Combine(Optional(Literal(':')) + lcName + Optional(Literal('!') | Literal('?')))
        constant = Word(identifierCharacter) | Word(nums) | Combine(Literal('"') + Word((printables + " ").replace('"', '')) + Literal('"')) #QuotedString(quoteChar = '"', escChar = '\\')
        variable = Word(qMark, identifierCharacter)

        atomArgs = Group(delimitedList(constant | Combine(Optional("+") + variable)))
        predDeclArgs = Group(delimitedList(domName))

        predName = Word(identifierCharacter)

        # predGroup = delimitedList(predName, delim='|')
        predGroup = predName + OneOrMore(Literal("|").suppress() + predName)

        atom = Group(predName + openRB + atomArgs + closeRB)
        groupatom = Group(predGroup + openRB + atomArgs + closeRB)
        literal = Optional(Literal("!") | Literal("*")) + atom
        litgroup = Optional(Literal("!") | Literal("*")) + groupatom

        predDecl = Group(predName + openRB + predDeclArgs + closeRB + StringEnd())

        formula = Forward()
        exist = Literal("EXIST ").suppress() + Group(delimitedList(variable)) + openRB + Group(formula) + closeRB
        equality = (constant|variable) + Literal("=").suppress() + (constant|variable)
        inequality = (constant|variable) + Literal('=/=').suppress() + (constant|variable)
        negation = Literal("!").suppress() + openRB + Group(formula) + closeRB

        item = litgroup | literal | exist | inequality | equality | openRB + formula + closeRB | negation
        conjunction = Group(item) + ZeroOrMore(Literal("^").suppress() + Group(item))
        disjunction = Group(conjunction) + ZeroOrMore(Literal("v").suppress() + Group(conjunction))
        implication = Group(disjunction) + Optional(Literal("=>").suppress() + Group(disjunction))
        biimplication = Group(implication) + Optional(Literal("<=>").suppress() + Group(implication))
        formula << biimplication

        def lit_group_parse_action(a, b, c):
            try:
                return tree.trigger(a, b, c, 'litgroup')
            except Exception as e:
                print(e)

        def lit_parse_action(a, b, c): return tree.trigger(a,b,c,'lit')
        def neg_parse_action(a, b, c): return tree.trigger(a,b,c,'!')
        def disjunction_parse_action(a, b, c): tree.trigger(a,b,c,'v')
        def conjunction_parse_action(a, b, c): tree.trigger(a,b,c,'^')
        def exist_parse_action(a, b, c): return tree.trigger(a,b,c,"ex")
        def implication_parse_action(a, b, c): tree.trigger(a,b,c,"=>")
        def biimplication_parse_action(a, b, c): tree.trigger(a,b,c,"<=>")
        def equality_parse_action(a, b, c): return tree.trigger(a,b,c,"=")
        def inequality_parse_action(a, b, c): return tree.trigger(a,b,c,"!=")
        def count_constraint_parse_action(a, b, c): tree.trigger(a,b,c,'count')

        tree = TreeBuilder(logic)
        litgroup.setParseAction(lit_group_parse_action)
        literal.setParseAction(lit_parse_action)
        negation.setParseAction(neg_parse_action)
        disjunction.setParseAction(disjunction_parse_action)
        conjunction.setParseAction(conjunction_parse_action)
        exist.setParseAction(exist_parse_action)
        implication.setParseAction(implication_parse_action)
        biimplication.setParseAction(biimplication_parse_action)
        equality.setParseAction(equality_parse_action)
        inequality.setParseAction(inequality_parse_action)

        self.equality = equality
        self.tree = tree
        self.formula = formula + StringEnd()
        self.predDecl = predDecl
        self.literal = literal
        
    def isvar(self, identifier):
        """
        Variables must start with a question mark (or the + operator, 
        anything else is considered a constant.
        """
        return identifier[0] == '?' or identifier[0] == "+"


if __name__ == '__main__':

    # f = '(a(x) ^ b(u) v !(c(h) v (r =/= k) ^ !(d(i) ^ !e(x) ^ g(x)))) => EXIST ?a,?b (f(x) ^ b(c))'
    from pracmln.mln.base import MLN
    from pracmln.mln.database import Database
    mln = MLN(grammar='PRACGrammar')
    # mln << 'foo(x, y)'
    mln << 'bar(x)'
    # mln << 'numberEats(k,n)'
    # mln << 'eats(p,m)'
    # mln << 'rel(x,y)'
    mln << 'a(s)'
    mln << 'b(s)'
    mln << 'c(s)'
    # mln << 'd(s)'
    # mln << 'e(s)'
    # mln << 'g(s)'
    # mln << 'f(s)'

    
    f = 'a|b|c(s) => (bar(y) <=> bar(x))'
    # f = 'a|b|c(s)'
    print('mln:')
    mln.write()
    print('---------------------------------------------------')
    f = mln.logic.grammar.parse_formula(f)
    print(f, '===================================================================================')
    f.print_structure()
    print(list(f.literals()))
    # print mln.logic.parse_formula('bar(x)') in f.literals()
    print('f:', f)

    mln << 'coreference(a,b)'
    mln << 'distance(d,e,f)'
    mln.formula(f)

    # f = '!a|b|c(s) => (bar(y) <=> bar(x))'
    # f= '!(FORALL s (has_sense(?w1,s))) => coreference(?w1,?w2)'
    f = 'a|b|c(s) ^ bar(y) ^ bar(x)'
    # print 'mln:'
    f = mln.logic.grammar.parse_formula(f)
    mln.write()
    # print f, '==================================================================================='
    # f.print_structure()
    # print 'repr of f', repr(f)
    # print 'list f.literals', list(f.literals())
    # print 'parse_formula', mln.logic.parse_formula('bar(x)') in f.literals()
    # print 'f', f

    cnf = f.cnf()
    # print 'structure:'
    cnf.print_structure()
    # print 'cnf:',cnf
    mln.formula(cnf)


    db = Database(mln)
    matmln = mln.materialize(db)
    matmln.write()
#     test = ['!a(k)',
#             'a(c) ^ b(g)',
#             'b(x) v !a(l) ^ b(x)',
#             '!(a(g)) => ((!(f(x) v b(a))))',
#             "f(h) v (g(?h) <=> !f(?k) ^ d(e))",
#             'f(t) ^ ?x = y'
#             ]
#     for t in test:
#         print t
#         mln.logic.grammar.tree.reset()
#         mln.logic.grammar.parse_formula(t).print_structure()
#         print t




# main app for testing purposes only
# if __name__=='__main__':
# 
#     gr = CFG.fromstring("""
#     ATOM -> 
#     """)

#     f = [r'((a(x) ^ b(x, y, z)) v !(coo(a,"x,^)(\"",?u) v (?r =/= k) ^ !(d(x,i) ^ !e(x) ^ g(x)))) => E. a,b (f(x))']
#     esc = esc_seq(f)
#     print esc
#     b = brackets(esc)
#     print b
#     w, _ = split_tree(b, r'E\.\s*(\w*?)\s+', keepsep=True)
#     print w
#     w, _ = split_tree(w, r',', keepsep=False)
#     print w
#     print_tree(w)
#     a = literals(f)
#     print a
#     print_tree(brackets(f))

# 
# # main app for testing purposes only
# if __name__=='__main__':
#     from fol import FirstOrderLogic
#     from fuzzy import FuzzyLogic
#     from pracmln import MLN
# 
#     test = 'NF'
#     mln = MLN(grammar='PRACGrammar')
#     mln << 'foo(x, y)'
#     mln << 'numberEats(k,n)'
#     mln << 'eats(p,m)'
#     mln << 'rel(x,y)'
#     mln << 'a(s)'
#     mln << 'b(s)'
#     mln << 'c(s)'
#     mln << 'd(s)'
#     mln << 'e(s)'
#     mln << 'g(s)'
#     mln << 'f(s)'
#     
#     test = ['!a(k)',
#             'a(c) ^ b(g)',
#             'b(x) v !a(l) ^ b(x)',
#             '!(a(g)) => ((!(f(x) v b(a))))',
#             "f(h) v (g(?h) <=> !f(?k) ^ d(e))",
# #             'EXIST ?x (g(j) ^ b(x))',
#             'f(t) ^ ?x = y'
# #         "9 v 2 ^ 3",
# #         "(9 v 2) ^ 3",
# #         "9 =>  2 v 3 ^ 6",
# #         "!(9 v 2) ^ 3 => 2 <=> 2",
# #         "(9! + -2) * 3^2^2",
# #         "M*X + B",
# #         "M*(X + B)",
# #         "1+2*-3^4*5+-+-6",
# ]
#     for t in test:
#         print t
#         mln.logic.grammar.tree.reset()
#         t = [t]
#         for typ in (mln.logic.grammar.literal, mln.logic.grammar.equality):
#             for i, e in enumerate(list(t)):
#                 t[i] = replace_all(e, typ)
#         print t
#                 
# #         mln.logic.grammar.parse_formula(t).print_structure()
# #         print  type(formula.parseString(t)[0])
# #         print map(str, mln.logic.grammar.tree.stack)
# #         mln.logic.grammar.tree.stack[0].print_structure()
#         print 
# #     literal = Word(nums).setParseAction(lambda t: str(t[0]))#int(t[0]))
# #      = Word(alphas,exact=1)
# #     operand = mln.logic.grammar.literal
#     
#     negop = Literal('!')
#     eqop = Literal('=')
#     neqop = Literal('=/=')
#     conjop = Literal('^')
#     disjop = Literal('v')
#     implop = Word('=>')
#     bimplop = Word('<=>')
#     
#     def conj(t):
#         out('making conjunction:', t)
#         return str(t)
# #     conjop.setParseAction(conj)
#     
# #     tree = TreeBuilder(mln.logic)
#     
# #     formula = operatorPrecedence( mln.logic.grammar.formula,
# #         [(negop, 1, opAssoc.RIGHT),
# # #          (eqop, 2, opAssoc.LEFT),
# #          (conjop, 2, opAssoc.LEFT),
# #          (disjop, 2, opAssoc.LEFT),
# #          (implop, 2, opAssoc.LEFT),
# #          (bimplop, 2, opAssoc.LEFT),]
# #         )
#     
# 
#     exit()
#     
#     if test == 'parsing':
#         tests = ["numberEats(o,2) <=> EXIST p, p2 (eats(o,p) ^ eats(o,p2) ^ !(o=p) ^ !(o=p2) ^ !(p=p2) ^ !(EXIST q (eats(o,q) ^ !(p=q) ^ !(p2=q))))",
#                  "EXIST y (rel(x,y) ^ EXIST y2 (!(y2=y) ^ rel(x,y2)) ^ !(EXIST y3 (!(y3=y) ^ !(y3=y2) ^ rel(x,y3))))",
# #                 '(EXIST ?w (action_role(?w, +?r)))',
# #                     'class(?s1, ?c1) ^ class(?s2, ?c2) ^ ?s1=/=?s2'
# #                 'EXIST ?w (action_role(?w, +?r) ^ is_a(?w, +?c))'
#                 "((a(x) ^ b(x)) v (c(x) ^ !(d(x) ^ e(x) ^ g(x)))) => f(x)"
#                  ]#,"foo(x) <=> !(EXIST p (foo(p)))", "numberEats(o,1) <=> !(EXIST p (eats(o,p) ^ !(o=p)))", "!a(c,d) => c=d", "c(b) v !(a(b) ^ b(c))"]
# #         tests = ["((!a(x) => b(x)) ^ (b(x) => a(x))) v !(b(x)=>c(x))"]
# #         tests = ["(EXIST y1 (rel(x,y1) ^ EXIST y2 (rel(x,y2) ^ !(y1=y2) ^ !(EXIST y3 (rel(?x,y3) ^ !(y1=y3) ^ !(y2=y3))))))"]
# #         tests = ["EXIST ?x (a(?x))"]
# #         tests = ['!foo(?x, ?y) ^ ?x =/= ?y']
#         print mln.logic.parse_literal('foo("bla!", c)')
#         print mln.logic.parse_predicate('foo(ar,bar2!)')
#         for test in tests:
#             print "trying to parse %s..." % test
#             mln.logic.parse_formula(test).print_structure()
# #             f = logic.grammar.parseFormula(test).toCNF()
# #             print "got this: %s" % str(f)
# #             f.printStructure()
#     elif test == 'NF':
#         f = "a(x) <=> b(x)"
#         f = "((a(x) ^ b(x)) v (c(x) ^ !(d(x) ^ e(x) ^ g(x)))) => f(x)"
#         f = "(a(x) v (b(x) ^ c(x))) => f(x)"
# #         f = "(a(x) ^ b(x)) <=> (c(x) ^ d(x))"
#         #f = "(a(x) ^ b(x)) v (c(x) ^ d(x))"        
#         #f = "(a(x) ^ b(x)) v (c(x) ^ d(x)) v (e(x) ^ f(x))"
#         #f = "(a(x) ^ b(x)) v (c(x) ^ d(x)) v (e(x) ^ f(x)) v (g(x) ^ h(x))"
#         #f = "(a(x) ^ b(x) ^ e(x)) v (c(x) ^ d(x) ^ f(x))"
#         #f = "(a(x) ^ b(x) ^ g(x)) v (c(x) ^ d(x) ^ h(x)) v (e(x) ^ f(x) ^ i(x))"
#         #f = "(a(x) ^ !b(x) ^ !c(x)) v (!a(x) ^ b(x) ^ !c(x)) v (!a(x) ^ !b(x) ^ c(x))"
#         #f = "(a(x) ^ b(x) ^ !c(x)) v (a(x) ^ !b(x) ^ c(x)) v (!a(x) ^ b(x) ^ c(x))"
#         #f = "(a(x) ^ !b(x)) v (!a(x) ^ b(x))"
#         #f = "(a(x) ^ b(x) ^ !c(x)) v (a(x) ^ !b(x) ^ c(x)) v (!a(x) ^ b(x) ^ c(x))"
#         #f = "(a(x) ^ b(x) ^ !c(x) ^ !d(x)) v (a(x) ^ !b(x) ^ c(x) ^ !d(x)) v (!a(x) ^ b(x) ^ c(x) ^ !d(x)) v (a(x) ^ !b(x) ^ !c(x) ^ d(x)) v (!a(x) ^ b(x) ^ !c(x) ^ d(x)) v (!a(x) ^ !b(x) ^ c(x) ^ d(x))"
#         #f = "consumesAny(P,Coffee) <=> ((consumedBy(C3,P) ^ goodsT(C3,Coffee)) v (consumedBy(C2,P) ^ goodsT(C2,Coffee)) v (consumedBy(C1,P) ^ goodsT(C1,Coffee)) v (consumedBy(C4,P) ^ goodsT(C4,Coffee)))"
#         #f = "consumesAny(P,Coffee) <=> ((consumedBy(C3,P) ^ goodsT(C3,Coffee)) v (consumedBy(C2,P) ^ goodsT(C2,Coffee)) v (consumedBy(C1,P) ^ goodsT(C1,Coffee)))"
#         f = mln.logic.parse_formula(f)
#         f = f.nnf()
#         f.print_structure()
#     elif test == 'count':
#         c = "count(directs(a,m)|m) >= 4"
#         c = "count(foo(a,Const)) = 2"
#         #c = count_constraint.parseString(c)
#         c = mln.logic.parseFormula(c).cnf()
#         print str(c)
#         pass
#     
#     
