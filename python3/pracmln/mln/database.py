#
# Markov Logic Networks -- Databases
#
# (C) 2006-2015 by Daniel Nyga, (nyga@cs.tum.edu)
#                  Dominik Jain (jain@cs.tum.edu)
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
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE."""
from dnutils import ifnone, logs
from dnutils.console import barstr

from .util import stripComments, mergedom
from ..logic.common import Logic
from ..logic.fol import FirstOrderLogic
from .errors import NoSuchPredicateError
import os
from io import StringIO
import sys
from .util import colorize
from .errors import MLNParsingError
import traceback
from collections import defaultdict
import re
from ..utils.project import mlnpath


logger = logs.getlogger(__name__)


class Database(object):
    """
    Represents an MLN Database, which consists of a set of ground atoms, each assigned a truth value.
    
    
    :member mln:            the respective :class:`mln.base.MLN` object that this Database is associated with
    :member domains:        dict mapping the variable domains specific to this data base (i.e. without
                            values from the MLN domains which are not present in the DB) to the set possible values.
    :member evidence:       dictionary mapping ground atom strings to truth values.
    :param mln:             the :class:`mln.base.MLN` instance that the database shall be associated with.
    :param evidence:        a dictionary mapping ground atoms to their truth values.
    :param dbfile:          if specified, a database is loaded from the given file path.
    :param ignore_unknown_preds: see :func:`mln.database.parse_db`
    """
    
    def __init__(self, mln, evidence=None, dbfile=None, ignore_unknown_preds=False):
        self.mln = mln
        self._domains = defaultdict(list)
        self._evidence = {}
        if dbfile is not None:
            Database.load(mln, dbfile, db=self, ignore_unknown_preds=ignore_unknown_preds)
        if evidence is not None:
            for atom, truth in evidence.items():
                self.add(atom, truth)
        

    @property
    def domains(self):
        return self._domains
    
    @domains.setter
    def domains(self, doms):
        self._domains = doms
        
    @property
    def evidence(self):
        return dict(self._evidence)
    
    def _atomstr(self, gndatom):
        """
        Converts gndatom into a valid ground atom string representation. 
        """
        if type(gndatom) is str:
            _, predname, args = self.mln.logic.parse_literal(gndatom)
            atomstr = str(self.mln.logic.gnd_atom(predname, args, self.mln))
        elif isinstance(gndatom, Logic.GroundAtom):
            atomstr = str(gndatom)
        elif isinstance(gndatom, Logic.GroundLit):
            atomstr = str(gndatom.gndatom)
            predname = gndatom.gndatom.predname
            args = gndatom.gndatom.params
        elif isinstance(gndatom, Logic.Lit):
            atomstr = str(self.mln.logic.gnd_atom(gndatom.predname, gndatom.args, self.mln))
        return atomstr
            
    
    def truth(self, gndatom):
        """
        Returns the evidence truth value of the given ground atom.
        
        :param gndatom:    a ground atom string
        :returns:          the truth value of the ground atom, or None if it is not specified.
        """
        atomstr = self._atomstr(gndatom)
        return self._evidence.get(atomstr)
    
    
    def domain(self, domain):
        """
        Returns the list of domain values of the given domain, or None if no domain
        with the given name exists. If domain is dict, the domain values will be
        updated and the domain will be created, if necessary.
        
        :param domain:     the name of the domain to be returned.
        """
        if type(domain) is dict:
            for domname, values in domain.items():
                if type(values) is not list: values = [values]
                dom = self.domain(domname)
                if dom is None:
                    dom = []
                    self._domains[domname] = dom
                for value in values: 
                    if value not in dom: dom.append(value)
        elif domain is not None:
            return self._domains.get(domain)
        else:
            return self._domains
    
    
    def copy(self, mln=None):
        """
        Returns a copy this Database. If mln is specified, asserts
        this database for the given MLN.
        
        :param mln:            if `mln` is specified, the new MLN will be associated with `mln`,
                               if not, it will be associated with `self.mln`.
        """
        if mln is None:
            mln = self.mln
        db = Database(mln)
        for atom, truth in self.gndatoms():
            try: db.add(atom, truth)
            except NoSuchPredicateError: pass
        return db
    
    
    def union(self, dbs, mln=None):
        """
        Returns a new database consisting of the union of all databases
        given in the arguments. If mln is specified, the new database will
        be attached to that one, otherwise the mln of this database will
        be used.
        """
        db_ = Database(mln if mln is not None else self.mln)
        if type(dbs) is list:
            dbs = [e for d in dbs for e in list(d)] + list(self)
        if type(dbs) is Database:
            dbs = list(dbs) + list(self)
		
        for atom, truth in dbs:
            try: db_ << (atom, truth)
            except NoSuchPredicateError: pass
        return db_
    

    def gndatoms(self, prednames=None):
        """
        Iterates over all ground atoms in this database that match any of
        the given predicate names. If no predicate name is specified, it
        yields all ground atoms in the database.
        
        :param prednames:    a list of predicate names that this iteration should be filtered by.
        :returns:            a generator of (atom, truth) tuples.
        """
        for atom, truth in self:
            if prednames is not None:
                _, predname, _ = self.mln.logic.parse_literal(atom)
                if not predname in prednames: continue
            yield atom, truth


    def add(self, gndlit, truth=1):
        """
        Adds the fact represented by the ground atom, which might be
        a GroundLit object or a string.
        
        :param gndlit:     the ground literal to be added to the database.
                           Can be either a string or a :class:`logic.common.Logic.GroundLit` instance.
        :param truth:      the truth value of this ground literal. 0 stands for false, 1 for true.
                           In case of soft or fuzzy evidence, any truth value in [0,1] is allowed.
        """
        if isinstance(gndlit, str):
            true, predname, args = self.mln.logic.parse_literal(str(gndlit))
            atom_str = str(self.mln.logic.gnd_atom(predname, args, self.mln))
        elif isinstance(gndlit, Logic.GroundLit):
            atom_str = str(gndlit.gndatom)
            true = not gndlit.negated
            predname = gndlit.gndatom.predname
            args = gndlit.gndatom.args
        else:
            raise Exception('gndlit has an illegal type: %s' % type(gndlit))
        if truth in (True, False):
            truth = {True: 1, False: 0}[truth]
        truth = truth if true else 1 - truth
        truth = eval('%.6f' % truth)
        
        pred = self.mln.predicate(predname)
        if pred is None:
            raise NoSuchPredicateError('No such predicate: %s' % predname)
        
        if len(pred.argdoms) != len(args):
            raise Exception('Invalid number of arguments: %s' % str(gndlit))
        
        if not all([not self.mln.logic.isvar(a) for a in args]):
            raise Exception('No variables are allowed in databases. Only ground atoms: %s' % atom_str)
        
        # update the domains
        for domname, arg in zip(pred.argdoms, args):
            self.domain({domname: arg})

        self._evidence[atom_str] = truth
        return self
              
                
    def ishard(self):
        """
        Determines whether or not this database contains exclusively
        hard evidences.
        """
        return any([x != 1 and x != 0 for x in self._evidence])
    
                
    def tofile(self, filename):
        """
        Writes this database into the file with the given filename.
        """
        f = open(filename, 'w+')
        self.write(f)
        f.close()
                
                
    def write(self, stream=sys.stdout, color=None, bars=True):
        """
        Writes this database into the stream in the MLN Database format.
        The stream must provide a `write()` method as file objects do.
        """
        if color is None:
            if stream != sys.stdout: 
                color = False
            else: color = True
        for atom in sorted(self._evidence):
            truth = self._evidence[atom]
            pred, params = self.mln.logic.parse_atom(atom)
            pred = str(pred)
            params = list(map(str, params))
            if bars:
                bar = barstr(30, truth, color='magenta' if color else None)
            else:
                bar = ''
            if color:
                strout = '%s  %s\n' % (bar if bars else  colorize('%.6f' % truth, (None, 'magenta', False), True), 
                                       FirstOrderLogic.Lit(False, pred, params, self.mln).cstr(color))
            else:
                strout = '%s  %s\n' % (bar if bars else  '%.6f' % truth, FirstOrderLogic.Lit(False, pred, params, self.mln).cstr(color))
            stream.write(strout)
            
                
    def retract(self, gndatom):
        """
        Removes the evidence of the given ground atom in this database.
        
        Also cleans up the domains if an atom is removed that makes use of 
        a domain value that is not used by any other evidence atom.
        
        :param gndatom:     a string representation of the ground atom to be
                            removed from the database or a :class:`logic.common.Logic.GroundAtom` instance.
        """
        if type(gndatom) is str:
            _, predname, args = self.mln.logic.parse_literal(gndatom)
            atom_str = str(self.mln.logic.gnd_atom(predname, args, self.mln))
        elif isinstance(gndatom, Logic.GroundAtom):
            atom_str = str(gndatom.gndatom)
            args = gndatom.args
        else:
            raise Exception('gndatom has an illegal type: %s' % str(type(gndatom)))
        if atom_str not in self: return
        del self._evidence[atom_str]
        doms = self.mln.predicate(predname).argdoms
        dontremove = set()
        for atom, _ in self:
            _, predname_, args_ = self.mln.logic.parse_literal(atom)
            doms_ = self.mln.predicate(predname_).argdoms
            for arg, arg_, dom, dom_ in zip(args, args_, doms, doms_):
                if arg == arg_ and dom == dom_: dontremove.add((dom, arg))
        for (dom, arg) in zip(doms, args):
            if (dom, arg) not in dontremove:
                if arg in self._domains[dom]:
                    self._domains[dom].remove(arg)
                if not self.domain(dom): del self._domains[dom]
                
                
    def retractall(self, predname):
        """
        Retracts all evidence atoms of the given predicate name in this database. 
        """
        for a, _ in dict(self._evidence).items():
            _, pred, _ = self.mln.logic.parse_literal(a)
            if pred == predname: del self[a] 


    def rmval(self, domain, value):
        """
        Removes the value ``value`` from the domain ``domain`` of this database.
        
        This removal is complete, i.e. it also retracts all atoms in this database
        that the respective value is participating in as an argument.
        
        :param domain:    (str) the domain from which the value is to be removed.
        :param value:     (str) the value to be removed.
        """
        for atom in list(self.evidence):
            _, predname, args = self.mln.logic.parse_literal(atom)
            for dom, val in zip(self.mln.predicate(predname).argdoms, args):
                if dom == domain and val == value:
                    del self._evidence[atom]
        self.domains[domain].remove(value)

        
    def __iter__(self):
        for atom, truth in self._evidence.items():
            yield atom, truth
                
                
    def __add__(self, other):
        return self.union(other, mln=self.mln)
    
    
    def __iadd__(self, other):
        return self.union(other, mln=self.mln)
    
    
    def __setitem__(self, atom, truth):
        self.add(atom, truth)
    
    
    def __getitem__(self, atom):
        return self.evidence.get(atom)
    
    
    def __lshift__(self, arg):
        if type(arg) is tuple:
            if len(arg) != 2: raise Exception('Illegal argument arg: %s' % str(arg))
            self.add(arg[0], float(arg[1]))
        elif type(arg) == str:
            self.add(arg)
            
    
    def __rshift__(self, atom):
        self.retract(atom)
    
    
    def __contains__(self, el):
        atomstr = self._atomstr(el)
        return atomstr in self._evidence
    
    
    def __delitem__(self, item):
        self.retract(item)
    
                
    def __len__(self):
        return len(self.evidence)
    
                
    def isempty(self):
        """
        Returns True iff there is an assertion for any ground atom in this
        database and False if the truth values all ground atoms are None
        AND all domains are empty.
        """
        return not any([x >= 0 and x <= 1 for x in list(self._evidence.values())]) and \
            len(self.domains) == 0
                
                
    def query(self, formula, thr=1):
        """
        Makes to the database a 'prolog-like' query given by the specified formula.
        
        Returns a generator of dictionaries with variable-value assignments for which the formula has
        a truth value of at least `thr`.
        
        :param formula:        the formula the database shall be queried with.
        :param thr:      the threshold for truth values.
        
        ..  warning:: 
            This is *very* inefficient, since all groundings will be instantiated; so keep the queries short.
            
        :Example:
        
        >>> for r in db.query('foo(?x, ?y)'):
        >>>     print r
        >>>
        {'?x': 'X1', '?y': 'Y1'}
        {'?x': 'X2', '?y': 'Y2'}
        
        """ 
        mrf = Database.PseudoMRF(self)
        formula = self.mln.logic.parse_formula(formula)
        for assignment in mrf.iter_true_var_assignments(formula, truth_thr=thr):
            yield assignment


    @staticmethod
    def write_dbs(dbs, stream=sys.stdout, color=None, bars=False):
        if color is None:
            if stream != sys.stdout: 
                color = False
            else: color = True
        strdbs = []
        for db in dbs:
            s = StringIO()
            db.write(s, color=color, bars=bars)
            strdbs.append(s.getvalue())
            s.close()
        stream.write('---\n'.join(strdbs))
                        
                        
    @staticmethod
    def load(mln, dbfiles, ignore_unknown_preds=False, db=None):
        """
        Reads one or multiple database files containing literals and/or domains.
        Returns one or multiple databases where domains is dictionary mapping 
        domain names to lists of constants defined in the database
        and evidence is a dictionary mapping ground atom strings to truth values
        
        :param dbfile:  a single one or a list of paths to database file.
        :param mln:     the MLN object which should be used to load the database.
        :returns:       either one single or a list of database objects.
          
        :Example:
          >>> mln = MLN()
          >>> db = Database.load(mln, './example.db')
        """
        if type(dbfiles) is not list:
            dbfiles = [dbfiles]
        dbs = []
        for dbpath in dbfiles:
            if isinstance(dbpath, str): 
                dbpath = mlnpath(dbpath)
            if isinstance(dbpath, mlnpath):
                projectpath = None
                if dbpath.project is not None:
                    projectpath = dbpath.projectloc
                dirs = [os.path.dirname(fp) for fp in dbfiles]
                dbs_ = parse_db(mln, content=dbpath.content, ignore_unknown_preds=ignore_unknown_preds, db=db, dirs=dirs, projectpath=projectpath)
                dbs.extend(dbs_)
            else:
                raise Exception('Illegal db file specifier: %s' % dbpath)
        if len(dbs) > 1 and db is not None:
            raise Exception('Cannot attach multiple databases to a single database object. Use Database.load(..., db=None).')
        else: 
            return dbs 
    
    
    class PseudoMRF(object):
        """
        can be used in order to use only a Database object to ground formulas
        (without instantiating an MRF) and determine the truth of these ground
        formulas by partly replicating the interface of an MRF object
        """
        
        def __init__(self, db):
            self.mln = db.mln
            self.domains = mergedom(self.mln.domains, db.domains)
            self.gndatoms = Database.PseudoMRF.GroundAtomGen()
            # duplicate the database to avoid side effects
            self.evidence = Database.PseudoMRF.WorldValues(db.copy())

        class GroundAtomGen(object):
            def __getitem__(self, gndAtomName):
                return Database.PseudoMRF.TextGroundAtom(gndAtomName)
            
            def get(self, key, default=None):
                return self[key]
        
        class TextGroundAtom(object):
            def __init__(self, name):
                self.name = self.idx = name
        
            def truth(self, world):
                return world[self.name]
        
            def __str__(self):
                return self.name
            
            def simplify(self, mrf):
                return self
            
        class WorldValues(object):
            def __init__(self, db):
                self.db = db
            
            def __getitem__(self, atomstr):
                return self.db._evidence.get(atomstr, 0)
            
        def iter_groundings(self, formula):
            for t in formula.iter_groundings(self):
                yield t
        
        def truth(self, gndformula):
            return gndformula.truth(self.evidence)
        
        def count_true_groundings(self, formula):
            numTotal = 0
            numTrue = 0
            for gf, _ in self.iter_groundings(formula):
                numTotal += 1
                numTrue += gf.truth(self.evidence)
            return (numTrue, numTotal)

        def gndatom(self, atom):
            return self.gndatoms.get(atom)
        
        def iter_true_var_assignments(self, formula, truth_thr=1.0):
            """
            Iterates over all groundings of formula that evaluate to true
            given this Pseudo-MRF.
            """
            for assignment in formula.iter_true_var_assignments(self, self.evidence, truth_thr=truth_thr):
                yield assignment
                

def parse_db(mln, content, ignore_unknown_preds=False, db=None, dirs=['.'], projectpath=None):
    """
    Reads one or more databases in a string representation and returns
    the respective Database objects.
    
    :param mln:                     the MLN object which should be used to load
                                    the database.
    :param content:                 the string representation of one or
                                    multiple ('---'-separated) databases
    :param ignore_unknown_preds:    by default this function raises an
                                    Exception when it encounters a predicate
                                    in the DB that has not been declared in
                                    the associated MLN.
                                    ignore_unknown_preds=True simply ignores
                                    such predicates.
    :param db:                      The Database object that shall receive
                                    the facts stored in the new DB. If None,
                                    a new `Database` object will be created.
    :return:                        a list of databases
    """
    log = logs.getlogger('db')
    content = stripComments(content)
    allow_multiple = True
    if db is None:
        allow_multiple = True
        db = Database(mln, ignore_unknown_preds=ignore_unknown_preds)
    dbs = []
    # expand domains with dbtext constants and save evidence
    for line, l in enumerate(content.split("\n")):
        l = l.strip()
        if l == '':
            continue
        # separator between independent databases
        elif l == '---' and not db.isempty():
            dbs.append(db)
            db = Database(mln)
            continue
        # domain declaration
        elif "{" in l:
            domname, constants = db.mln.logic.parse_domain(l)
            domnames = [domname for _ in constants]
        # include
        elif l.startswith('#include'):
            filename = l[len("#include "):].strip()
            m = re.match(r'"(?P<filename>.+)"', filename)
            if m is not None:
                filename = m.group('filename')
                # if the path is relative, look for the respective file 
                # relatively to all paths specified. Take the first file matching.
                if not mlnpath(filename).exists:
                    includefilename = None
                    for d in dirs:
                        mlnp = '/'.join([d, filename])
                        if mlnpath(mlnp).exists:
                            includefilename = mlnp
                            break
                    if includefilename is None:
                        raise Exception('File not found: %s' % filename)
                else:
                    includefilename = filename
            else:
                m = re.match(r'<(?P<filename>.+)>', filename)
                if m is not None:
                    filename = m.group('filename')
                else:
                    raise MLNParsingError('Malformed #include statement: %s' % line)
                if projectpath is None:
                    raise MLNParsingError('No project specified: Cannot locate import from project: %s' % filename)
                includefilename = ':'.join([projectpath, filename])
            logger.debug('Including file: "%s"' % includefilename)
            p = mlnpath(includefilename)
            dbs.extend(parse_db(content=mlnpath(includefilename).content, ignore_unknown_preds=ignore_unknown_preds, dirs=[p.resolve_path()]+dirs, 
                      projectpath=ifnone(p.project, projectpath, lambda x: '/'.join(p.path+[x])), mln=mln)) 
            continue
        # valued evidence
        elif l[0] in "0123456789":
            s = l.find(" ")
            gndatom = l[s + 1:].replace(" ", "")
            value = float(l[:s])
            if value < 0 or value > 1:
                raise Exception('Valued evidence must be in [0,1]') 
            if gndatom  in db.evidence:
                raise Exception("Duplicate soft evidence for '%s'" % gndatom)
            try:
                _, predname, constants =   mln.logic.parse_literal(gndatom) # TODO Should we allow soft evidence on non-atoms here? (This assumes atoms)
            except NoSuchPredicateError as e:
                if ignore_unknown_preds: continue
                else: raise e
            domnames = mln.predicate(predname).argdoms
            db << (gndatom, value)
        # literal
        else:
            if l[0] == "?":
                raise Exception("Unknown literals not supported (%s)" % l) # this is an Alchemy feature
            try:
                true, predname, constants = mln.logic.parse_literal(l)
            except NoSuchPredicateError as e:
                if ignore_unknown_preds: continue
                else: raise e
            except Exception as e:
                traceback.print_exc()
                raise MLNParsingError('Error parsing line %d: %s (%s)' % (line+1, l, e.message))
            if mln.predicate(predname) is None and ignore_unknown_preds:
                log.debug('Predicate "%s" is undefined.' % predname)
                continue
            elif mln.predicate(predname) is None:
                raise NoSuchPredicateError(predname)
            domnames = mln.predicate(predname).argdoms
            # save evidence
            true = 1 if true else 0
            db << ("%s(%s)" % (predname, ",".join(constants)), true)

        # expand domains
        if len(domnames) != len(constants):
            raise Exception("Ground atom %s in database %d has wrong number of parameters" % (l, len(dbs)))

        for i, c in enumerate(constants):
            db.domain({domnames[i]: c})
            
    if not db.isempty(): dbs.append(db)
    if len(dbs) > 1 and not allow_multiple:
        raise Exception('Only one single database is permitted when loading via the constructor. Use Database.load() for loading multiple DBs,')
    return dbs



def readall_dbs(mln, path):
    """
    Loads and yields all databases (*.db files) that are located in
    the given directory and returns the corresponding Database objects.
    
    :param path:     the directory path to look for .db files
    """
    for dirname, dirnames, filenames in os.walk(path): #@UnusedVariable
        for f in filenames:
            if not f.endswith('.db'):
                continue
            p = os.path.join(dirname, f)
            print(" reading database %s" % p)
            dbs = Database.load(mln, p)
            if type(dbs) == list:
                for db in dbs:
                    yield db
            else:
                yield dbs
