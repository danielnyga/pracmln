#!/usr/bin/python
# -*- coding: utf-8 -*-

# MLN Parameter Learning Tool
#
# (C) 2012-2015 by Daniel Nyga
#     2006-2007 by Dominik Jain
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

import argparse
import fnmatch
import io
import pstats
import tkinter.messagebox
import traceback
from cProfile import Profile
from tkinter import *
from tkinter.filedialog import asksaveasfilename

from dnutils import logs, out, ifnone
from tabulate import tabulate

from pracmln import MLN
from pracmln.mln.base import parse_mln
from pracmln.mln.database import Database, parse_db
from pracmln.mln.learning.common import DiscriminativeLearner
from pracmln.mln.methods import LearningMethods
from pracmln.mln.util import headline, StopWatch
from pracmln.utils import config, locs
from pracmln.utils.config import global_config_filename
from pracmln.utils.project import MLNProject, PRACMLNConfig
from pracmln.utils.widgets import *
import logging #import used in eval, do not remove


logger = logs.getlogger(__name__)

QUERY_PREDS = 0
EVIDENCE_PREDS = 1
DEFAULTNAME = 'unknown{}'
DEFAULT_CONFIG = os.path.join(locs.user_data, global_config_filename)
WINDOWTITLE = 'PRACMLN Learning Tool - {}' + os.path.sep + '{}'
WINDOWTITLEEDITED = 'PRACMLN Learning Tool - {}' + os.path.sep + '*{}'


class MLNLearn(object):
    '''
    Wrapper class for learning using a PRACMLN configuration.
    
    :param config: Instance of a :class:`pracmln.PRACMLNConfig` class
                   representing a serialized configuration. Any parameter
                   in the config object can be overwritten by a respective
                   entry in the ``params`` dict.
                   
    :example:
    
        >>> conf = PRACMLNConfig('path/to/config/file')
        # overrides the MLN and database to be used.
        >>> learn = MLNLearn(conf, mln=newmln, db=newdb)
    
    .. seealso::
        :class:`pracmln.PRACMLNConfig`
    
    '''
    def __init__(self, config=None, **params):
        self.configfile = None
        if config is None:
            self._config = {}
        elif isinstance(config, PRACMLNConfig):
            self._config = config.config
            self.configfile = config
        self._config.update(params)


    @property
    def mln(self):
        '''
        The :class:`pracmln.MLN` instance to be used for learning.
        '''
        return self._config.get('mln')


    @property
    def db(self):
        '''
        The :class:`pracmln.Database` instance to be used for learning.
        '''
        return self._config.get('db')


    @property
    def output_filename(self):
        '''
        The name of the file the learnt MLN is to be saved to.
        '''
        return self._config.get('output_filename')


    @property
    def params(self):
        '''
        A dictionary of additional parameters that are specific to a
        particular learning algorithm.
        '''
        return eval("dict(%s)" % self._config.get('params', ''))


    @property
    def method(self):
        '''
        The string identifier of the learning method to use. Defaults to
        ``'BPLL'``.
        '''
        return LearningMethods.clazz(self._config.get('method', 'BPLL'))


    @property
    def pattern(self):
        '''
        A Unix file pattern determining the database files for learning.
        '''
        return self._config.get('pattern', '')


    @property
    def use_prior(self):
        '''
        Boolean specifying whether or not to use a prio distribution for
        parameter learning. Defaults to ``False``
        '''
        return self._config.get('use_prior', False)


    @property
    def prior_mean(self):
        '''
        The mean of the gaussian prior on the weights. Defaults to ``0.0``.
        '''
        return float(self._config.get('prior_mean', 0.0))


    @property
    def prior_stdev(self):
        '''
        The standard deviation of the prior on the weights. Defaults to
        ``5.0``.
        '''
        return float(self._config.get('prior_stdev', 5.0))


    @property
    def incremental(self):
        '''
        Specifies whether or incremental learning shall be enabled.
        Defaults to ``False``.
        
        .. note::
            This parameter is currently unused.
            
        '''
        return self._config.get('incremental', False)


    @property
    def shuffle(self):
        '''
        Specifies whether or not learning databases shall be shuffled before
        learning.
        
        .. note::
            This parameter is currently unused.
        '''
        self._config.get('shuffle', False)
        return True


    @property
    def use_initial_weights(self):
        '''
        Specifies whether or not the weights of the formulas prior to learning
        shall be used as an initial guess for the optimizer. Default is
        ``False``.
        '''
        return self._config.get('use_initial_weights', False)


    @property
    def qpreds(self):
        '''
        A list of predicate names specifying the query predicates in
        discriminative learning.
        
        .. note::
            This parameters only affects discriminative learning methods and
            is mutually exclusive with the :attr:`pracmln.MLNLearn.epreds`
            parameter.
        '''
        return self._config.get('qpreds', '').split(',')


    @property
    def epreds(self):
        '''
        A list of predicate names specifying the evidence predicates in
        discriminative learning.
        
        .. note::
            This parameters only affects discriminative learning methods and
            is mutually exclusive with the :attr:`pracmln.MLNLearn.qpreds`
            parameter.
        '''
        return self._config.get('epreds', '').split(',')


    @property
    def discr_preds(self):
        '''
        Specifies whether the query predicates or the evidence predicates
        shall be used. In either case, the respective other case will be
        automatically determined, i.e. if a list of query predicates is
        specified and ``disc_preds`` is ``pracmln.QUERY_PREDS``, then all
        other predicates will represent the evidence predicates and vice
        versa. Possible values are ``pracmln.QUERY_PREDS`` and
        ``pracmln.EVIDENCE_PREDS``.
        '''
        return self._config.get('discr_preds', QUERY_PREDS)


    @property
    def logic(self):
        '''
        String identifying the logical calculus to be used in the MLN. Must be
        either ``'FirstOrderLogic'``
        or ``'FuzzyLogic'``.
        
        .. note::
            It is discouraged to use the ``FuzzyLogic`` calculus for learning
            MLNs. Default is ``'FirstOrderLogic'``.
        '''
        return self._config.get('logic', 'FirstOrderLogic')


    @property
    def grammar(self):
        '''
        String identifying the MLN syntax to be used. Allowed values are
        ``'StandardGrammar'`` and ``'PRACGrammar'``. Default is
        ``'PRACGrammar'``.
        '''
        return self._config.get('grammar', 'PRACGrammar')


    @property
    def multicore(self):
        '''
        Specifies if all cores of the CPU are to be used for learning.
        Default is ``False``.
        '''
        return self._config.get('multicore', False)


    @property
    def profile(self):
        '''
        Specifies whether or not the Python profiler shall be used. This is
        convenient for debugging and optimizing your code in case you have
        developed own algorithms. Default is ``False``.
        '''
        return self._config.get('profile', False)


    @property
    def verbose(self):
        '''
        If ``True``, prints some useful output, status and progress
        information to the console. Default is ``False``.
        '''
        return self._config.get('verbose', False)


    @property
    def ignore_unknown_preds(self):
        '''
        By default, if an atom occurs in a database that is not declared in
        the attached MLN, `pracmln` will raise a
        :class:`NoSuchPredicateException`. If ``ignore_unknown_preds`` is
        ``True``, undeclared predicates will just be ignored.
        '''
        return self._config.get('ignore_unknown_preds', False)


    @property
    def ignore_zero_weight_formulas(self):
        '''
        When formulas in MLNs get more complex, there might be the chance that
        some of the formulas retain a weight of zero (because of strong
        independence assumptions in the Learner, for instance). Since such
        formulas have no effect on the semantics of an MLN but on the runtime
        of inference, they can be omitted in the final learnt MLN by settings
        ``ignore_zero_weight_formulas`` to ``True``.
        '''
        return self._config.get('ignore_zero_weight_formulas', False)


    @property
    def save(self):
        '''
        Specifies whether or not the learnt MLN shall be saved to a file.
        
        .. seealso::
            :attr:`pracmln.MLNLearn.output_filename`
        '''
        return self._config.get('save', False)


    def run(self):
        '''
        Run the MLN learning with the given parameters.
        '''
        # load the MLN
        if isinstance(self.mln, MLN):
            mln = self.mln
        else:
            raise Exception('No MLN specified')

        # load the training databases
        if type(self.db) is list and all(
                [isinstance(e, Database) for e in self.db]):
            dbs = self.db
        elif isinstance(self.db, Database):
            dbs = [self.db]
        elif isinstance(self.db, str):
            db = self.db
            if db is None or not db:
                raise Exception('no trainig data given!')
            dbpaths = [os.path.join(self.directory, 'db', db)]
            dbs = []
            for p in dbpaths:
                dbs.extend(Database.load(mln, p, self.ignore_unknown_preds))
        else:
            raise Exception(
                'Unexpected type of training databases: %s' % type(self.db))
        if self.verbose:
            print(('loaded %d database(s).' % len(dbs)))

        watch = StopWatch()

        if self.verbose:
            confg = dict(self._config)
            confg.update(eval("dict(%s)" % self.params))
            if type(confg.get('db', None)) is list:
                confg['db'] = '%d Databases' % len(confg['db'])
            print((tabulate(
                sorted(list(confg.items()), key=lambda key_v: str(key_v[0])),
                headers=('Parameter:', 'Value:'))))

        params = dict([(k, getattr(self, k)) for k in (
            'multicore', 'verbose', 'profile', 'ignore_zero_weight_formulas')])

        # for discriminative learning
        if issubclass(self.method, DiscriminativeLearner):
            if self.discr_preds == QUERY_PREDS:  # use query preds
                params['qpreds'] = self.qpreds
            elif self.discr_preds == EVIDENCE_PREDS:  # use evidence preds
                params['epreds'] = self.epreds

        # gaussian prior settings            
        if self.use_prior:
            params['prior_mean'] = self.prior_mean
            params['prior_stdev'] = self.prior_stdev
        # expand the parameters
        params.update(self.params)

        if self.profile:
            prof = Profile()
            print('starting profiler...')
            prof.enable()
        else:
            prof = None
        # set the debug level
        olddebug = logger.level
        logger.level = eval('logs.%s' % params.get('debug', 'WARNING').upper())
        mlnlearnt = None
        try:
            # run the learner
            mlnlearnt = mln.learn(dbs, self.method, **params)
            if self.verbose:
                print()
                print(headline('LEARNT MARKOV LOGIC NETWORK'))
                print()
                mlnlearnt.write()
        except SystemExit:
            print('Cancelled...')
        finally:
            if self.profile:
                prof.disable()
                print(headline('PROFILER STATISTICS'))
                ps = pstats.Stats(prof, stream=sys.stdout).sort_stats(
                    'cumulative')
                ps.print_stats()
            # reset the debug level
            logger.level = olddebug
        print()
        watch.finish()
        watch.printSteps()
        return mlnlearnt


class MLNLearnGUI:
    def __init__(self, master, gconf, directory=None):
        self.master = master

        self.initialized = False

        self.master.bind('<Return>', self.learn)
        self.master.bind('<Escape>', lambda a: self.master.quit())
        self.master.protocol('WM_DELETE_WINDOW', self.quit)

        # logo = Label(self.master, image=img)
        # logo.pack(side = "right", anchor='ne')
        self.dir = os.path.abspath(ifnone(directory, ifnone(gconf['prev_learnwts_path'], os.getcwd())))

        self.frame = Frame(master)
        self.frame.pack(fill=BOTH, expand=1)
        self.frame.columnconfigure(1, weight=1)

        row = 0
        # pracmln project options
        Label(self.frame, text='PRACMLN Project: ').grid(row=row, column=0,
                                                         sticky='ES')
        project_container = Frame(self.frame)
        project_container.grid(row=row, column=1, sticky="NEWS")

        # new proj file
        self.btn_newproj = Button(project_container, text='New Project...',
                                  command=self.new_project)
        self.btn_newproj.grid(row=0, column=1, sticky="WS")

        # open proj file
        self.btn_openproj = Button(project_container, text='Open Project...',
                                   command=self.ask_load_project)
        self.btn_openproj.grid(row=0, column=2, sticky="WS")

        # save proj file
        self.btn_saveproj = Button(project_container, text='Save Project',
                                   command=self.noask_save_project)
        self.btn_saveproj.grid(row=0, column=3, sticky="WS")

        # save proj file as...
        self.btn_saveproj = Button(project_container,
                                   text='Save Project as...',
                                   command=self.ask_save_project)
        self.btn_saveproj.grid(row=0, column=4, sticky="WS")

        # grammar selection
        row += 1
        Label(self.frame, text='Grammar: ').grid(row=row, column=0, sticky='E')
        grammars = ['StandardGrammar', 'PRACGrammar']
        self.selected_grammar = StringVar(master)
        self.selected_grammar.trace('w', self.settings_setdirty)
        l = OptionMenu(*(self.frame, self.selected_grammar) + tuple(grammars))
        l.grid(row=row, column=1, sticky='NWE')

        # logic selection
        row += 1
        Label(self.frame, text='Logic: ').grid(row=row, column=0, sticky='E')
        logics = ['FirstOrderLogic', 'FuzzyLogic']
        self.selected_logic = StringVar(master)
        self.selected_logic.trace('w', self.settings_setdirty)
        l = OptionMenu(*(self.frame, self.selected_logic) + tuple(logics))
        l.grid(row=row, column=1, sticky='NWE')

        # mln section
        row += 1
        Label(self.frame, text="MLN: ").grid(row=row, column=0, sticky='NE')
        self.mln_container = FileEditBar(self.frame, directory=self.dir,
                                         filesettings={'extension': '.mln', 'ftypes': [('MLN files', '.mln')]},
                                         defaultname='*unknown{}',
                                         importhook=self.import_mln,
                                         deletehook=self.delete_mln,
                                         projecthook=self.save_proj,
                                         filecontenthook=self.mlnfilecontent,
                                         fileslisthook=self.mlnfiles,
                                         selectfilehook=self.set_outputfilename,
                                         updatehook=self.update_mln,
                                         onchangehook=self.project_setdirty)
        self.mln_container.grid(row=row, column=1, sticky="NEWS")
        self.mln_container.editor.bind("<FocusIn>", self._got_focus)
        self.mln_container.columnconfigure(1, weight=2)
        self.frame.rowconfigure(row, weight=1)

        # method selection
        row += 1
        Label(self.frame, text="Method: ").grid(row=row, column=0, sticky=E)
        self.selected_method = StringVar(master)
        methodnames = sorted(LearningMethods.names())
        self.list_methods = OptionMenu(*(self.frame, self.selected_method) + tuple(methodnames))
        self.list_methods.grid(row=row, column=1, sticky="NWE")
        self.selected_method.trace("w", self.select_method)

        # additional parametrization
        row += 1
        frame = Frame(self.frame)
        frame.grid(row=row, column=1, sticky="NEW")

        # use prior
        self.use_prior = IntVar()
        self.cb_use_prior = Checkbutton(frame, text="use prior with mean of ",
                                        variable=self.use_prior,
                                        command=self.onchange_useprior)
        self.cb_use_prior.pack(side=LEFT)

        # set prior 
        self.priorMean = StringVar(master)
        self.en_prior_mean = Entry(frame, textvariable=self.priorMean, width=5)
        self.en_prior_mean.pack(side=LEFT)
        self.priorMean.trace('w', self.settings_setdirty)
        Label(frame, text="and std dev of").pack(side=LEFT)

        # std. dev.
        self.priorStdDev = StringVar(master)
        self.en_stdev = Entry(frame, textvariable=self.priorStdDev, width=5)
        self.priorStdDev.trace('w', self.settings_setdirty)
        self.en_stdev.pack(side=LEFT)

        # use initial weights in MLN 
        self.use_initial_weights = IntVar()
        self.cb_use_initial_weights = Checkbutton(frame,
                                                  text="use initial weights",
                                                  variable=self.use_initial_weights,
                                                  command=self.settings_setdirty)
        self.cb_use_initial_weights.pack(side=LEFT)

        # use incremental learning
        self.incremental = IntVar()
        self.cb_incremental = Checkbutton(frame, text="learn incrementally",
                                          variable=self.incremental,
                                          command=self.onchange_incremental)
        self.cb_incremental.pack(side=LEFT)

        # shuffle databases
        self.shuffle = IntVar()
        self.cb_shuffle = Checkbutton(frame, text="shuffle databases",
                                      variable=self.shuffle, state='disabled')
        self.cb_shuffle.pack(side=LEFT)

        # discriminative learning settings
        row += 1
        self.discrPredicates = IntVar()
        self.discrPredicates.trace('w', self.change_discr_preds)
        self.discrPredicates.set(1)
        frame = Frame(self.frame)
        frame.grid(row=row, column=1, sticky="NEWS")
        self.rbQueryPreds = Radiobutton(frame, text="Query preds:",
                                        variable=self.discrPredicates,
                                        value=QUERY_PREDS)
        self.rbQueryPreds.grid(row=0, column=0, sticky="NE")

        self.queryPreds = StringVar(master)
        frame.columnconfigure(1, weight=1)
        self.entry_nePreds = Entry(frame, textvariable=self.queryPreds)
        self.entry_nePreds.grid(row=0, column=1, sticky="NEW")

        self.rbEvidencePreds = Radiobutton(frame, text='Evidence preds',
                                           variable=self.discrPredicates,
                                           value=EVIDENCE_PREDS)
        self.rbEvidencePreds.grid(row=0, column=2, sticky='NEWS')

        self.evidencePreds = StringVar(master)
        self.entryEvidencePreds = Entry(frame, textvariable=self.evidencePreds)
        self.entryEvidencePreds.grid(row=0, column=3, sticky='NEWS')

        # db section
        row += 1
        Label(self.frame, text="Evidence: ").grid(row=row, column=0, sticky='NE')
        self.db_container = FileEditBar(self.frame, directory=self.dir,
                                        filesettings={'extension': '.db', 'ftypes': [('Database files', '.db')]},
                                        defaultname='*unknown{}',
                                        importhook=self.import_db,
                                        deletehook=self.delete_db,
                                        projecthook=self.save_proj,
                                        filecontenthook=self.dbfilecontent,
                                        fileslisthook=self.dbfiles,
                                        selectfilehook=self.set_outputfilename,
                                        updatehook=self.update_db,
                                        onchangehook=self.project_setdirty)
        self.db_container.grid(row=row, column=1, sticky="NEWS")
        self.db_container.editor.bind("<FocusIn>", self._got_focus)
        self.db_container.columnconfigure(1, weight=2)
        self.frame.rowconfigure(row, weight=1)

        # file patterns
        row += 1
        frame = Frame(self.frame)
        frame.grid(row=row, column=1, sticky="NEW")
        col = 0
        Label(frame, text="OR file pattern:").grid(row=0, column=col, sticky="W")
        # - pattern entry
        col += 1
        frame.columnconfigure(col, weight=1)
        self.pattern = StringVar(master)
        self.pattern.trace('w', self.onchange_pattern)
        self.entry_pattern = Entry(frame, textvariable=self.pattern)
        self.entry_pattern.grid(row=0, column=col, sticky="NEW")

        # add. parameters
        row += 1
        Label(self.frame, text="Add. Params: ").grid(row=row, column=0, sticky="E")
        self.params = StringVar(master)
        Entry(self.frame, textvariable=self.params).grid(row=row, column=1, sticky="NEW")

        # options
        row += 1
        Label(self.frame, text="Options: ").grid(row=row, column=0, sticky="E")
        option_container = Frame(self.frame)
        option_container.grid(row=row, column=1, sticky="NEWS")

        # multicore
        self.multicore = IntVar()
        self.cb_multicore = Checkbutton(option_container, text="Use all CPUs",
                                        variable=self.multicore,
                                        command=self.settings_setdirty)
        self.cb_multicore.grid(row=0, column=1, sticky=E)

        # profiling
        self.profile = IntVar()
        self.cb_profile = Checkbutton(option_container, text='Use Profiler',
                                      variable=self.profile,
                                      command=self.settings_setdirty)
        self.cb_profile.grid(row=0, column=3, sticky=W)

        # verbose
        self.verbose = IntVar()
        self.cb_verbose = Checkbutton(option_container, text='verbose',
                                      variable=self.verbose, 
                                      command=self.settings_setdirty)
        self.cb_verbose.grid(row=0, column=4, sticky=W)

        self.ignore_zero_weight_formulas = IntVar()
        self.cb_ignore_zero_weight_formulas = Checkbutton(option_container, text='remove 0-weight formulas',
                                                          variable=self.ignore_zero_weight_formulas, command=self.settings_setdirty)
        self.cb_ignore_zero_weight_formulas.grid(row=0, column=5, sticky=W)

        # ignore unknown preds
        self.ignore_unknown_preds = IntVar(master)
        self.ignore_unknown_preds.trace('w', self.settings_setdirty)
        self.cb_ignore_unknown_preds = \
            Checkbutton(option_container, text='ignore unkown predicates', variable=self.ignore_unknown_preds)
        self.cb_ignore_unknown_preds.grid(row=0, column=6, sticky="W")

        row += 1
        output_cont = Frame(self.frame)
        output_cont.grid(row=row, column=1, sticky='NEWS')
        output_cont.columnconfigure(0, weight=1)

        Label(self.frame, text="Output: ").grid(row=row, column=0, sticky="E")
        self.output_filename = StringVar(master)
        self.entry_output_filename = Entry(output_cont, textvariable=self.output_filename)
        self.entry_output_filename.grid(row=0, column=0, sticky="EW")

        self.save = IntVar(self.master)
        self.cb_save = Checkbutton(output_cont, text='save', variable=self.save)
        self.cb_save.grid(row=0, column=1, sticky='W')

        row += 1
        learn_button = Button(self.frame, text=" >> Start Learning << ", command=self.learn)
        learn_button.grid(row=row, column=1, sticky="EW")

        self.settings_dirty = IntVar()
        self.project_dirty = IntVar()

        self.gconf = gconf
        self.project = None
        self.project_dir = os.path.abspath(ifnone(directory, ifnone(gconf['prev_learnwts_path'], os.getcwd())))
        if gconf['prev_learnwts_project': self.project_dir] is not None:
            self.load_project(os.path.join(self.project_dir, gconf['prev_learnwts_project':self.project_dir]))
        else:
            self.new_project()
        self.config = self.project.learnconf
        self.project.addlistener(self.project_setdirty)

        self.mln_container.dirty = False
        self.db_container.dirty = False
        self.project_setdirty(dirty=False)

        self.master.geometry(gconf['window_loc_learn'])

        self.initialized = True

    def _got_focus(self, *_):
        if self.master.focus_get() == self.mln_container.editor:
            if not self.project.mlns and not self.mln_container.file_buffer:
                self.mln_container.new_file()
        elif self.master.focus_get() == self.db_container.editor:
            if not self.project.dbs and not self.db_container.file_buffer:
                self.db_container.new_file()

    def quit(self):
        if self.settings_dirty.get() or self.project_dirty.get():
            savechanges = tkinter.messagebox.askyesnocancel("Save changes", "You have unsaved project changes. Do you want to save them before quitting?")
            if savechanges is None:
                return
            elif savechanges:
                self.noask_save_project()
            self.master.destroy()
        else:
            # write gui settings and destroy
            self.write_gconfig()
            self.master.destroy()


    ####################### PROJECT FUNCTIONS #################################

    def new_project(self):
        self.project = MLNProject()
        self.project.addlistener(self.project_setdirty)
        self.project.name = DEFAULTNAME.format('.pracmln')
        self.reset_gui()
        self.set_config(self.project.learnconf)
        self.mln_container.update_file_choices()
        self.db_container.update_file_choices()
        self.settings_setdirty()


    def project_setdirty(self, dirty=False, *_):
        self.project_dirty.set(
            dirty or self.mln_container.dirty or self.db_container.dirty)
        self.changewindowtitle()


    def settings_setdirty(self, *_):
        self.settings_dirty.set(1)
        self.changewindowtitle()


    def changewindowtitle(self):
        title = (WINDOWTITLEEDITED if (self.settings_dirty.get() or self.project_dirty.get()) else WINDOWTITLE).format(self.project_dir, self.project.name)
        self.master.title(title)


    def ask_load_project(self):
        filename = askopenfilename(initialdir=self.dir, filetypes=[('PRACMLN project files', '.pracmln')], defaultextension=".pracmln")
        if filename and os.path.exists(filename):
            self.load_project(filename)
        else:
            logger.info('No file selected.')
            return


    def load_project(self, filename):
        if filename and os.path.exists(filename):
            projdir, _ = ntpath.split(filename)
            self.dir = os.path.abspath(projdir)
            self.project_dir = os.path.abspath(projdir)
            self.project = MLNProject.open(filename)
            self.project.addlistener(self.project_setdirty)
            self.reset_gui()
            self.set_config(self.project.learnconf.config)
            self.mln_container.update_file_choices()
            self.db_container.update_file_choices()
            if len(self.project.mlns) > 0:
                self.mln_container.selected_file.set(self.project.learnconf['mln'] or list(self.project.mlns.keys())[0])
            self.mln_container.dirty = False
            if len(self.project.dbs) > 0:
                self.db_container.selected_file.set(self.project.learnconf['db'] or list(self.project.dbs.keys())[0])
            self.db_container.dirty = False
            self.write_gconfig(savegeometry=False)
            self.settings_dirty.set(0)
            self.project_setdirty(dirty=False)
            self.changewindowtitle()
        else:
            logger.error(
                'File {} does not exist. Creating new project...'.format(
                    filename))
            self.new_project()


    def noask_save_project(self):
        if self.project.name and not self.project.name == DEFAULTNAME .format('.pracmln'):
            self.save_project(
                os.path.join(self.project_dir, self.project.name))
        else:
            self.ask_save_project()


    def ask_save_project(self):
        fullfilename = asksaveasfilename(initialdir=self.project_dir,
                                         confirmoverwrite=True,
                                         filetypes=[('PRACMLN project files', '.pracmln')],
                                         defaultextension=".pracmln")
        self.save_project(fullfilename)


    def save_project(self, fullfilename):
        if fullfilename:
            fpath, fname = ntpath.split(fullfilename)
            fname = fname.split('.')[0]
            self.project.name = fname
            self.dir = os.path.abspath(fpath)
            self.project_dir = os.path.abspath(fpath)

            self.mln_container.save_all_files()
            self.db_container.save_all_files()

            self.update_config()
            self.project.save(dirpath=self.project_dir)
            self.write_gconfig()

            self.load_project(fullfilename)
            self.settings_dirty.set(0)


    def save_proj(self):
        self.project.save(dirpath=self.project_dir)
        self.write_gconfig()
        self.project_setdirty(dirty=False)

    ####################### MLN FUNCTIONS #####################################

    def import_mln(self, name, content):
        self.project.add_mln(name, content)


    def delete_mln(self, fname):
        if fname in self.project.mlns:
            self.project.rm_mln(fname)
        fnamestr = fname.strip('*')
        if fnamestr in self.project.mlns:
            self.project.rm_mln(fnamestr)


    def update_mln(self, old=None, new=None, content=None, askoverwrite=True):
        if old is None:
            old = self.mln_container.selected_file.get()
        if new is None:
            new = self.mln_container.selected_file.get().strip('*')
        if content is None:
            content = self.mln_container.editor.get("1.0", END).strip()

        if old == new and askoverwrite:
            savechanges = tkinter.messagebox.askyesno("Save changes",
                                                "A file '{}' already exists. "
                                                "Overwrite?".format(new))
            if savechanges:
                self.project.mlns[old] = content
            else:
                logger.error('no name specified!')
                return -1
        elif old == new and not askoverwrite:
            self.project.mlns[old] = content
        else:
            if new in self.project.mlns:
                if askoverwrite:
                    savechanges = tkinter.messagebox.askyesno("Save changes", "A file '{}' already exists. Overwrite?".format(new))
                    if savechanges:
                        self.project.mlns[new] = content
                    else:
                        logger.error('no name specified!')
                        return -1
            else:
                self.project.mlns[new] = content
        return 1


    def mlnfiles(self):
        return list(self.project.mlns.keys())


    def mlnfilecontent(self, filename):
        return self.project.mlns.get(filename, '').strip()


    # /MLN FUNCTIONS ###################################

    ####################### DB FUNCTIONS #####################################

    def import_db(self, name, content):
        self.project.add_db(name, content)


    def delete_db(self, fname):
        if fname in self.project.dbs:
            self.project.rm_db(fname)
        fnamestr = fname.strip('*')
        if fnamestr in self.project.dbs:
            self.project.rm_db(fnamestr)


    def update_db(self, old=None, new=None, content=None, askoverwrite=True):
        if old is None:
            old = self.db_container.selected_file.get()
        if new is None:
            new = self.db_container.selected_file.get().strip('*')
        if content is None:
            content = self.db_container.editor.get("1.0", END).strip()

        if old == new and askoverwrite:
            savechanges = tkinter.messagebox.askyesno("Save changes", "A file '{}' already exists. Overwrite?".format(new))
            if savechanges:
                self.project.dbs[old] = content
            else:
                logger.error('no name specified!')
                return -1
        elif old == new and not askoverwrite:
            self.project.dbs[old] = content
        else:
            if new in self.project.dbs:
                if askoverwrite:
                    savechanges = tkinter.messagebox.askyesno("Save changes", "A file '{}' already exists. Overwrite?".format(new))
                    if savechanges:
                        self.project.dbs[new] = content
                    else:
                        logger.error('no name specified!')
                        return -1
            else:
                self.project.dbs[new] = content
        return 1


    def dbfiles(self):
        return list(self.project.dbs.keys())


    def dbfilecontent(self, filename):
        return self.project.dbs.get(filename, '').strip()


    # /DB FUNCTIONS #####################################

    # GENERAL FUNCTIONS #################################

    def onchange_incremental(self):
        if self.incremental.get() == 1:
            self.cb_shuffle.configure(state="normal")
        else:
            self.cb_shuffle.configure(state="disabled")
            self.cb_shuffle.deselect()
        self.settings_setdirty()


    def onchange_pattern(self, *_):
        self.db_container.editor.disable(self.pattern.get())
        self.db_container.list_files.config(
            state=DISABLED if self.pattern.get() else NORMAL)
        self.settings_setdirty()


    def onchange_useprior(self, *_):
        self.en_prior_mean.configure(
            state=NORMAL if self.use_prior.get() else DISABLED)
        self.en_stdev.configure(
            state=NORMAL if self.use_prior.get() else DISABLED)
        self.settings_setdirty()


    def isfile(self, f):
        return os.path.exists(os.path.join(self.dir, f))


    def set_outputfilename(self):
        mln = self.mln_container.selected_file.get() or 'unknown.mln'
        db = self.db_container.selected_file.get() or 'unknown.db'
        if self.selected_method.get():
            method = LearningMethods.clazz(self.selected_method.get())
            methodid = LearningMethods.id(method)
            filename = config.learnwts_output_filename(mln, methodid.lower(), db)
            self.output_filename.set(filename)


    def select_method(self, *_):
        self.change_discr_preds()
        self.set_outputfilename()
        self.settings_setdirty()


    def change_discr_preds(self, *_):
        methodname = self.selected_method.get()
        if methodname:
            method = LearningMethods.clazz(methodname)
            state = NORMAL if issubclass(method, DiscriminativeLearner) else DISABLED
            self.entry_nePreds.configure(state=state if self.discrPredicates.get() == 0 else DISABLED)
            self.entryEvidencePreds.configure(state=state if self.discrPredicates.get() == 1 else DISABLED)
            self.rbEvidencePreds.configure(state=state)
            self.rbQueryPreds.configure(state=state)


    def reset_gui(self):
        self.set_config({})
        self.db_container.clear()
        self.mln_container.clear()


    def set_config(self, newconf):
        self.config = newconf
        self.selected_grammar.set(ifnone(newconf.get('grammar'), 'PRACGrammar'))
        self.selected_logic.set(ifnone(newconf.get('logic'), 'FirstOrderLogic'))
        self.mln_container.selected_file.set(ifnone(newconf.get('mln'), ''))
        self.db_container.selected_file.set(ifnone(newconf.get('db'), ""))
        self.selected_method.set(ifnone(newconf.get("method"), LearningMethods.name('BPLL'), transform=LearningMethods.name))
        self.pattern.set(ifnone(newconf.get('pattern'), ''))
        self.multicore.set(ifnone(newconf.get('multicore'), 0))
        self.use_prior.set(ifnone(newconf.get('use_prior'), 0))
        self.priorMean.set(ifnone(newconf.get('prior_mean'), 0))
        self.priorStdDev.set(ifnone(newconf.get('prior_stdev'), 5))
        self.incremental.set(ifnone(newconf.get('incremental'), 0))
        self.shuffle.set(ifnone(newconf.get('shuffle'), 0))
        self.use_initial_weights.set(ifnone(newconf.get('use_initial_weights'), 0))
        self.profile.set(ifnone(newconf.get('profile'), 0))
        self.params.set(ifnone(newconf.get('params'), ''))
        self.verbose.set(ifnone(newconf.get('verbose'), 1))
        self.ignore_unknown_preds.set(ifnone(newconf.get('ignore_unknown_preds'), 0))
        self.output_filename.set(ifnone(newconf.get('output_filename'), ''))
        self.queryPreds.set(ifnone(newconf.get('qpreds'), ''))
        self.evidencePreds.set(ifnone(newconf.get('epreds'), ''))
        self.discrPredicates.set(ifnone(newconf.get('discr_preds'), 0))
        self.ignore_zero_weight_formulas.set(ifnone(newconf.get('ignore_zero_weight_formulas'), 0))
        self.save.set(ifnone(newconf.get('save'), 0))


    def get_training_db_paths(self, pattern):
        '''
        determine training databases(s)
        '''
        local = False
        dbs = []
        if pattern is not None and pattern.strip():
            fpath, pat = ntpath.split(pattern)
            if not os.path.exists(fpath):
                logger.debug('{} does not exist. Searching for pattern {} in project {}...'.format(fpath, pat, self.project.name))
                local = True
                dbs = [db for db in self.project.dbs if fnmatch.fnmatch(db, pattern)]
                if len(dbs) == 0:
                    raise Exception("The pattern '{}' matches no files in your project {}".format(pat, self.project.name))
            else:
                local = False
                patternpath = os.path.join(self.dir, pattern)

                d, mask = os.path.split(os.path.abspath(patternpath))
                for fname in os.listdir(d):
                    print(fname)
                    if fnmatch.fnmatch(fname, mask):
                        dbs.append(os.path.join(d, fname))
                if len(dbs) == 0:
                    raise Exception("The pattern '%s' matches no files in %s" % (pat, fpath))
            logger.debug(
                'loading training databases from pattern %s:' % pattern)
            for p in dbs: logger.debug('  %s' % p)
        if not dbs:
            raise Exception("No training data given; A training database must be selected or a pattern must be specified")
        else:
            return local, dbs


    def update_config(self):
        out('update_config')

        self.config = PRACMLNConfig()
        self.config['mln'] = self.mln_container.selected_file.get().strip().lstrip('*')
        self.config["db"] = self.db_container.selected_file.get().strip().lstrip('*')
        self.config["output_filename"] = self.output_filename.get()
        self.config["params"] = self.params.get().strip()
        self.config["method"] = LearningMethods.id(self.selected_method.get().strip())
        self.config["pattern"] = self.pattern.get()
        self.config["use_prior"] = int(self.use_prior.get())
        self.config["prior_mean"] = self.priorMean.get()
        self.config["prior_stdev"] = self.priorStdDev.get()
        self.config["incremental"] = int(self.incremental.get())
        self.config["shuffle"] = int(self.shuffle.get())
        self.config["use_initial_weights"] = int(self.use_initial_weights.get())
        self.config["qpreds"] = self.queryPreds.get().strip()
        self.config["epreds"] = self.evidencePreds.get().strip()
        self.config["discr_preds"] = self.discrPredicates.get()
        self.config['logic'] = self.selected_logic.get()
        self.config['grammar'] = self.selected_grammar.get()
        self.config['multicore'] = self.multicore.get()
        self.config['profile'] = self.profile.get()
        self.config['verbose'] = self.verbose.get()
        self.config['ignore_unknown_preds'] = self.ignore_unknown_preds.get()
        self.config['ignore_zero_weight_formulas'] = self.ignore_zero_weight_formulas.get()
        self.config['save'] = self.save.get()
        self.config["output_filename"] = self.output_filename.get().strip()
        self.project.learnconf = PRACMLNConfig()
        self.project.learnconf.update(self.config.config.copy())


    def write_gconfig(self, savegeometry=True):
        self.gconf['prev_learnwts_path'] = self.project_dir
        self.gconf['prev_learnwts_project': self.project_dir] = self.project.name

        # save geometry
        if savegeometry:
            self.gconf['window_loc_learn'] = self.master.geometry()
        self.gconf.dump()


    def learn(self, savegeometry=True, options=None, *_):
        if options is None:
            options = {}
        mln_content = self.mln_container.editor.get("1.0", END).strip()
        db_content = self.db_container.editor.get("1.0", END).strip()

        # create conf from current gui settings
        self.update_config()

        # write gui settings
        self.write_gconfig(savegeometry=savegeometry)

        # hide gui
        self.master.withdraw()

        try:
            print((headline('PRAC LEARNING TOOL')))
            print()

            if options.get('mlnarg') is not None:
                mlnobj = MLN(mlnfile=os.path.abspath(options.get('mlnarg')),
                             logic=self.config.get('logic', 'FirstOrderLogic'),
                             grammar=self.config.get('grammar', 'PRACGrammar'))
            else:
                mlnobj = parse_mln(mln_content, searchpaths=[self.project_dir],
                                   projectpath=os.path.join(self.project_dir, self.project.name),
                                   logic=self.config.get('logic', 'FirstOrderLogic'),
                                   grammar=self.config.get('grammar', 'PRACGrammar'))

            if options.get('dbarg') is not None:
                dbobj = Database.load(mlnobj, dbfiles=[options.get('dbarg')], ignore_unknown_preds=self.config.get('ignore_unknown_preds', True))
            else:
                if self.config.get('pattern'):
                    local, dblist = self.get_training_db_paths(self.config.get('pattern').strip())
                    dbobj = []
                    # build database list from project dbs
                    if local:
                        for dbname in dblist:
                            dbobj.extend(parse_db(mlnobj, self.project.dbs[dbname].strip(),
                                         ignore_unknown_preds=self.config.get('ignore_unknown_preds', True),
                                         projectpath=os.path.join(self.dir, self.project.name)))
                        out(dbobj)
                    # build database list from filesystem dbs
                    else:
                        for dbpath in dblist:
                            dbobj.extend(Database.load(mlnobj, dbpath, ignore_unknown_preds= self.config.get('ignore_unknown_preds', True)))
                # build single db from currently selected db
                else:
                    dbobj = parse_db(mlnobj, db_content, projectpath=os.path.join(self.dir, self.project.name), dirs=[self.dir])

            learning = MLNLearn(config=self.config, mln=mlnobj, db=dbobj)
            result = learning.run()

            # write to file if run from commandline, otherwise save result
            # to project results
            if options.get('outputfile') is not None:
                output = io.StringIO()
                result.write(output)
                with open(os.path.abspath(options.get('outputfile')), 'w') as f:
                    f.write(output.getvalue())
                logger.info('saved result to {}'.format(os.path.abspath(options.get('outputfile'))))
            elif self.save.get():
                output = io.StringIO()
                result.write(output)
                self.project.add_mln(self.output_filename.get(), output.getvalue())
                self.mln_container.update_file_choices()
                self.project.save(dirpath=self.project_dir)
                logger.info('saved result to file mln/{} in project {}'.format(self.output_filename.get(), self.project.name))
            else:
                logger.debug("No output file given - results have not been saved.")
        except:
            traceback.print_exc()

        # restore gui
        sys.stdout.flush()
        self.master.deiconify()


def main():
    logger.level = logs.DEBUG

    usage = 'PRACMLN Learning Tool'

    parser = argparse.ArgumentParser(description=usage)
    parser.add_argument("--run", action="store_true", dest="run", default=False, help="run last configuration without showing gui")
    parser.add_argument("-d", "--dir", dest="directory", action='store', help="the directory to start the tool from", metavar="FILE", type=str)
    parser.add_argument("-i", "--mln-filename", dest="mlnarg", action='store', help="input MLN filename", metavar="FILE", type=str)
    parser.add_argument("-t", "--db-filename", dest="dbarg", action='store', help="training database filename", metavar="FILE", type=str)
    parser.add_argument("-o", "--output-file", dest="outputfile", action='store', help="output MLN filename", metavar="FILE", type=str)

    args = parser.parse_args()
    opts_ = vars(args)

    # run learning task/GUI
    root = Tk()
    conf = PRACMLNConfig(DEFAULT_CONFIG)
    app = MLNLearnGUI(root, conf, directory=os.path.abspath(args.directory) if args.directory is not None else None)

    if args.run:
        logger.debug('running mlnlearn without gui')
        app.learn(savegeometry=False, options=opts_)
    else:
        root.mainloop()


if __name__ == '__main__':
    main()
