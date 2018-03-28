#!/usr/bin/python
# -*- coding: utf-8 -*-

# MLN Query Tool
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
import argparse
import os
import sys
import ntpath
import traceback
from tkinter import Frame, BOTH, Label, Button, OptionMenu, IntVar, Checkbutton, \
    W, E, Entry, messagebox, END, DISABLED, NORMAL, Tk
from tkinter.filedialog import askopenfilename, asksaveasfilename, StringVar

from dnutils import logs, ifnone, out

from pracmln import ALL
from pracmln.utils.project import MLNProject, PRACMLNConfig, mlnpath
from pracmln.mln.methods import InferenceMethods
from pracmln.utils.widgets import FileEditBar
from pracmln.utils import config, locs
from pracmln.mln.util import parse_queries, headline, StopWatch
from pracmln.utils.config import global_config_filename
from pracmln.mln.base import parse_mln, MLN
from pracmln.mln.database import parse_db, Database
from tabulate import tabulate
from cProfile import Profile
import pstats
import io

import logging #import used in eval, do not remove


logger = logs.getlogger(__name__)

GUI_SETTINGS = ['window_loc', 'db', 'method', 'use_emln', 'save',
                'output_filename', 'grammar', 'queries', 'emln']
ALLOWED_EXTENSIONS = [('PRACMLN project files', '.pracmln'),
                      ('MLN files', '.mln'), ('MLN extension files', '.emln'),
                      ('Database files', '.db')]
DEFAULTNAME = 'unknown{}'
DEFAULT_CONFIG = os.path.join(locs.user_data, global_config_filename)
WINDOWTITLE = 'PRACMLN Query Tool - {}' + os.path.sep + '{}'
WINDOWTITLEEDITED = 'PRACMLN Query Tool - {}' + os.path.sep + '*{}'


class MLNQuery(object):

    def __init__(self, config=None, verbose=None, **params):
        '''
        Class for performing MLN inference
        :param config:  the configuration file for the inference
        :param verbose: boolean value whether verbosity logs will be
                        printed or not
        :param params:  dictionary of additional settings
        '''
        self.configfile = None
        if config is None:
            self._config = {}
        elif isinstance(config, PRACMLNConfig):
            self._config = config.config
            self.configfile = config
        if verbose is not None:
            self._verbose = verbose
        else:
            self._verbose = self._config.get('verbose', False)
        self._config.update(params)


    @property
    def mln(self):
        return self._config.get('mln')


    @property
    def db(self):
        return self._config.get('db')


    @property
    def output_filename(self):
        return self._config.get('output_filename')


    @property
    def params(self):
        return eval("dict(%s)" % self._config.get('params', ''))


    @property
    def method(self):
        return InferenceMethods.clazz(self._config.get('method', 'MC-SAT'))


    @property
    def queries(self):
        q = self._config.get('queries', ALL)
        if isinstance(q, str):
            return parse_queries(self.mln, q)
        return q


    @property
    def emln(self):
        return self._config.get('emln', None)


    @property
    def cw(self):
        return self._config.get('cw', False)


    @property
    def cw_preds(self):
        preds = self._config.get('cw_preds', '')
        if type(preds) is str:
            preds = preds.split(',')
        return list(map(str.strip, preds))


    @property
    def use_emln(self):
        return self._config.get('use_emln', False)


    @property
    def logic(self):
        return self._config.get('logic', 'FirstOrderLogic')


    @property
    def grammar(self):
        return self._config.get('grammar', 'PRACGrammar')


    @property
    def multicore(self):
        return self._config.get('multicore', False)


    @property
    def profile(self):
        return self._config.get('profile', False)


    @property
    def verbose(self):
        return self._verbose

    @property
    def ignore_unknown_preds(self):
        return self._config.get('ignore_unknown_preds', False)


    @property
    def save(self):
        return self._config.get('save', False)


    def run(self):
        watch = StopWatch()
        watch.tag('inference', self.verbose)
        # load the MLN
        if isinstance(self.mln, MLN):
            mln = self.mln
        else:
            raise Exception('No MLN specified')

        if self.use_emln and self.emln is not None:
            mlnstrio = io.StringIO()
            mln.write(mlnstrio)
            mlnstr = mlnstrio.getvalue()
            mlnstrio.close()
            emln = self.emln
            mln = parse_mln(mlnstr + emln, grammar=self.grammar,
                            logic=self.logic)

        # load the database
        if isinstance(self.db, Database):
            db = self.db
        elif isinstance(self.db, list) and len(self.db) == 1:
            db = self.db[0]
        elif isinstance(self.db, list) and len(self.db) == 0:
            db = Database(mln)
        elif isinstance(self.db, list):
            raise Exception(
                'Got {} dbs. Can only handle one for inference.'.format(
                    len(self.db)))
        else:
            raise Exception('DB of invalid format {}'.format(type(self.db)))

        # expand the
        #  parameters
        params = dict(self._config)
        if 'params' in params:
            params.update(eval("dict(%s)" % params['params']))
            del params['params']
        params['verbose'] = self.verbose
        if self.verbose:
            print((tabulate(sorted(list(params.items()), key=lambda k_v: str(k_v[0])), headers=('Parameter:', 'Value:'))))
        if type(db) is list and len(db) > 1:
            raise Exception('Inference can only handle one database at a time')
        elif type(db) is list:
            db = db[0]
        params['cw_preds'] = [x for x in self.cw_preds if bool(x)]
        # extract and remove all non-algorithm
        for s in GUI_SETTINGS:
            if s in params: del params[s]

        if self.profile:
            prof = Profile()
            print('starting profiler...')
            prof.enable()
        # set the debug level
        olddebug = logger.level
        logger.level = (eval('logs.%s' % params.get('debug', 'WARNING').upper()))
        result = None
        try:
            mln_ = mln.materialize(db)
            mrf = mln_.ground(db)
            inference = self.method(mrf, self.queries, **params)
            if self.verbose:
                print()
                print((headline('EVIDENCE VARIABLES')))
                print()
                mrf.print_evidence_vars()

            result = inference.run()
            if self.verbose:
                print()
                print((headline('INFERENCE RESULTS')))
                print()
                inference.write()
            if self.verbose:
                print()
                inference.write_elapsed_time()
        except SystemExit:
            traceback.print_exc()
            print('Cancelled...')
        finally:
            if self.profile:
                prof.disable()
                print((headline('PROFILER STATISTICS')))
                ps = pstats.Stats(prof, stream=sys.stdout).sort_stats('cumulative')
                ps.print_stats()
            # reset the debug level
            logger.level = olddebug
        if self.verbose:
            print()
            watch.finish()
            watch.printSteps()
        return result


class MLNQueryGUI(object):
    def __init__(self, master, gconf, directory=None):
        self.master = master

        self.initialized = False

        self.master.bind('<Return>', self.infer)
        self.master.bind('<Escape>', lambda a: self.master.quit())
        self.master.protocol('WM_DELETE_WINDOW', self.quit)

        self.dir = os.path.abspath(ifnone(directory, ifnone(gconf['prev_query_path'], os.getcwd())))

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
        self.btn_newproj = Button(project_container, text='New Project...', command=self.new_project)
        self.btn_newproj.grid(row=0, column=1, sticky="WS")

        # open proj file
        self.btn_openproj = Button(project_container, text='Open Project...', command=self.ask_load_project)
        self.btn_openproj.grid(row=0, column=2, sticky="WS")

        # save proj file
        self.btn_updateproj = Button(project_container, text='Save Project...', command=self.noask_save_project)
        self.btn_updateproj.grid(row=0, column=3, sticky="WS")

        # save proj file as...
        self.btn_saveproj = Button(project_container, text='Save Project as...', command=self.ask_save_project)
        self.btn_saveproj.grid(row=0, column=4, sticky="WS")

        # grammar selection
        row += 1
        Label(self.frame, text='Grammar: ').grid(row=row, column=0, sticky='E')
        grammars = ['StandardGrammar', 'PRACGrammar']
        self.selected_grammar = StringVar()
        self.selected_grammar.trace('w', self.settings_setdirty)
        l = OptionMenu(*(self.frame, self.selected_grammar) + tuple(grammars))
        l.grid(row=row, column=1, sticky='NWE')

        # logic selection
        row += 1
        Label(self.frame, text='Logic: ').grid(row=row, column=0, sticky='E')
        logics = ['FirstOrderLogic', 'FuzzyLogic']
        self.selected_logic = StringVar()
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
                                         updatehook=self.update_mln,
                                         onchangehook=self.project_setdirty)
        self.mln_container.editor.bind("<FocusIn>", self._got_focus)
        self.mln_container.grid(row=row, column=1, sticky="NEWS")
        self.mln_container.columnconfigure(1, weight=2)
        self.frame.rowconfigure(row, weight=1)

        row += 1
        self.use_emln = IntVar()
        self.use_emln.set(0)
        self.cb_use_emln = Checkbutton(self.frame, text="use model extension",
                                       variable=self.use_emln,
                                       command=self.onchange_use_emln)
        self.cb_use_emln.grid(row=row, column=1, sticky="W")

        # mln extension section
        row += 1
        self.emlncontainerrow = row
        self.emln_label = Label(self.frame, text="EMLN: ")
        self.emln_label.grid(row=self.emlncontainerrow, column=0, sticky='NE')
        self.emln_container = FileEditBar(self.frame,
                                          directory=self.dir,
                                          filesettings={'extension': '.emln', 'ftypes': [('MLN extension files','.emln')]},
                                          defaultname='*unknown{}',
                                          importhook=self.import_emln,
                                          deletehook=self.delete_emln,
                                          projecthook=self.save_proj,
                                          filecontenthook=self.emlnfilecontent,
                                          fileslisthook=self.emlnfiles,
                                          updatehook=self.update_emln,
                                          onchangehook=self.project_setdirty)
        self.emln_container.grid(row=self.emlncontainerrow, column=1, sticky="NEWS")
        self.emln_container.editor.bind("<FocusIn>", self._got_focus)
        self.emln_container.columnconfigure(1, weight=2)
        self.onchange_use_emln(dirty=False)
        self.frame.rowconfigure(row, weight=1)

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
                                        updatehook=self.update_db,
                                        onchangehook=self.project_setdirty)
        self.db_container.grid(row=row, column=1, sticky="NEWS")
        self.db_container.editor.bind("<FocusIn>", self._got_focus)
        self.db_container.columnconfigure(1, weight=2)
        self.frame.rowconfigure(row, weight=1)

        # inference method selection
        row += 1
        self.list_methods_row = row
        Label(self.frame, text="Method: ").grid(row=row, column=0, sticky=E)
        self.selected_method = StringVar()
        self.selected_method.trace('w', self.select_method)
        methodnames = sorted(InferenceMethods.names())
        self.list_methods = OptionMenu(*(self.frame, self.selected_method) + tuple(methodnames))
        self.list_methods.grid(row=self.list_methods_row, column=1, sticky="NWE")

        # options
        row += 1
        option_container = Frame(self.frame)
        option_container.grid(row=row, column=1, sticky="NEWS")

        # Multiprocessing
        self.multicore = IntVar()
        self.cb_multicore = Checkbutton(option_container, text="Use all CPUs",
                                        variable=self.multicore,
                                        command=self.settings_setdirty)
        self.cb_multicore.grid(row=0, column=2, sticky=W)

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

        # options
        self.ignore_unknown_preds = IntVar()
        self.cb_ignore_unknown_preds = Checkbutton(option_container,
                                                   text='ignore unkown predicates',
                                                   variable=self.ignore_unknown_preds,
                                                   command=self.settings_setdirty)
        self.cb_ignore_unknown_preds.grid(row=0, column=5, sticky="W")

        # queries
        row += 1
        Label(self.frame, text="Queries: ").grid(row=row, column=0, sticky=E)
        self.query = StringVar()
        self.query.trace('w', self.settings_setdirty)
        Entry(self.frame, textvariable=self.query).grid(row=row, column=1, sticky="NEW")

        # additional parameters
        row += 1
        Label(self.frame, text="Add. params: ").grid(row=row, column=0, sticky="NE")
        self.params = StringVar()
        self.params.trace('w', self.settings_setdirty)
        self.entry_params = Entry(self.frame, textvariable=self.params)
        self.entry_params.grid(row=row, column=1, sticky="NEW")

        # closed-world predicates
        row += 1
        Label(self.frame, text="CW preds: ").grid(row=row, column=0, sticky="E")

        cw_container = Frame(self.frame)
        cw_container.grid(row=row, column=1, sticky='NEWS')
        cw_container.columnconfigure(0, weight=1)

        self.cwPreds = StringVar()
        self.cwPreds.trace('w', self.settings_setdirty)
        self.entry_cw = Entry(cw_container, textvariable=self.cwPreds)
        self.entry_cw.grid(row=0, column=0, sticky="NEWS")

        self.closed_world = IntVar()
        self.cb_closed_world = Checkbutton(cw_container, text="CW Assumption",
                                           variable=self.closed_world,
                                           command=self.onchange_cw)
        self.cb_closed_world.grid(row=0, column=1, sticky='W')

        # output filename
        row += 1
        output_cont = Frame(self.frame)
        output_cont.grid(row=row, column=1, sticky='NEWS')
        output_cont.columnconfigure(0, weight=1)

        # - filename
        Label(self.frame, text="Output: ").grid(row=row, column=0, sticky="NE")
        self.output_filename = StringVar()
        self.entry_output_filename = Entry(output_cont, textvariable=self.output_filename)
        self.entry_output_filename.grid(row=0, column=0, sticky="NEW")

        # - save option
        self.save = IntVar()
        self.cb_save = Checkbutton(output_cont, text="save", variable=self.save)
        self.cb_save.grid(row=0, column=1, sticky=W)

        # start button
        row += 1
        start_button = Button(self.frame, text=">> Start Inference <<", command=self.infer)
        start_button.grid(row=row, column=1, sticky="NEW")

        self.settings_dirty = IntVar()
        self.project_dirty = IntVar()

        self.gconf = gconf
        self.project = None
        self.project_dir = os.path.abspath(ifnone(directory, ifnone(gconf['prev_query_path'], os.getcwd())))
        if gconf['prev_query_project': self.project_dir] is not None:
            self.load_project(os.path.join(self.project_dir, gconf['prev_query_project':self.project_dir]))
        else:
            self.new_project()

        self.config = self.project.queryconf
        self.project.addlistener(self.project_setdirty)

        self.mln_container.dirty = False
        self.emln_container.dirty = False
        self.db_container.dirty = False
        self.project_setdirty(dirty=False)

        self.master.geometry(gconf['window_loc_query'])

        self.initialized = True

    def _got_focus(self, *_):
        if self.master.focus_get() == self.mln_container.editor:
            if not self.project.mlns and not self.mln_container.file_buffer:
                self.mln_container.new_file()
        elif self.master.focus_get() == self.db_container.editor:
            if not self.project.dbs and not self.db_container.file_buffer:
                self.db_container.new_file()
        elif self.master.focus_get() == self.emln_container.editor:
            if not self.project.emlns and not self.emln_container.file_buffer:
                self.emln_container.new_file()

    def quit(self):
        if self.settings_dirty.get() or self.project_dirty.get():
            savechanges = messagebox.askyesnocancel("Save changes", "You have unsaved project changes. Do you want to save them before quitting?")
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
        self.set_config(self.project.queryconf)
        self.mln_container.update_file_choices()
        self.emln_container.update_file_choices()
        self.db_container.update_file_choices()
        self.project_setdirty(dirty=True)


    def project_setdirty(self, dirty=False, *args):
        self.project_dirty.set(dirty or self.mln_container.dirty or self.db_container.dirty or
            self.emln_container.dirty)
        self.changewindowtitle()


    def settings_setdirty(self, *args):
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
            self.set_config(self.project.queryconf.config)
            self.mln_container.update_file_choices()
            self.db_container.update_file_choices()
            if len(self.project.mlns) > 0:
                self.mln_container.selected_file.set(self.project.queryconf['mln'] or list(self.project.mlns.keys())[0])
            self.mln_container.dirty = False
            if len(self.project.emlns) > 0:
                self.emln_container.selected_file.set(self.project.queryconf['emln'] or list(self.project.emlns.keys())[0])
            self.emln_container.dirty = False
            if len(self.project.dbs) > 0:
                self.db_container.selected_file.set(self.project.queryconf['db'] or list(self.project.dbs.keys())[0])
            self.db_container.dirty = False
            self.write_gconfig(savegeometry=False)
            self.settings_dirty.set(0)
            self.project_setdirty(dirty=False)
            self.changewindowtitle()
        else:
            logger.error('File {} does not exist. Creating new project...'.format(filename))
            self.new_project()


    def noask_save_project(self):
        if self.project.name and not self.project.name == DEFAULTNAME.format('.pracmln'):
            self.save_project(os.path.join(self.project_dir, self.project.name))
        else:
            self.ask_save_project()


    def ask_save_project(self):
        fullfilename = asksaveasfilename(initialdir=self.project_dir,
                                         confirmoverwrite=True,
                                         filetypes=[('PRACMLN project files','.pracmln')],
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
            self.emln_container.save_all_files()
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
            savechanges = messagebox.askyesno("Save changes", "A file '{}' already exists. Overwrite?".format(new))
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
                    savechanges = messagebox.askyesno("Save changes", "A file '{}' already exists. Overwrite?".format(new))
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

    # /MLN FUNCTIONS #####################################


    ####################### EMLN FUNCTIONS #####################################

    def import_emln(self, name, content):
        self.project.add_emln(name, content)


    def delete_emln(self, fname):
        if fname in self.project.emlns:
            self.project.rm_emln(fname)
        fnamestr = fname.strip('*')
        if fnamestr in self.project.emlns:
            self.project.rm_emln(fnamestr)


    def update_emln(self, old=None, new=None, content=None, askoverwrite=True):
        if old is None:
            old = self.emln_container.selected_file.get()
        if new is None:
            new = self.emln_container.selected_file.get().strip('*')
        if content is None:
            content = self.emln_container.editor.get("1.0", END).strip()

        if old == new and askoverwrite:
            savechanges = messagebox.askyesno("Save changes", "A file '{}' already exists. Overwrite?".format(new))
            if savechanges:
                self.project.emlns[old] = content
            else:
                logger.error('no name specified!')
                return -1
        elif old == new and not askoverwrite:
            self.project.emlns[old] = content
        else:
            if new in self.project.emlns:
                if askoverwrite:
                    savechanges = messagebox.askyesno("Save changes", "A file '{}' already exists. Overwrite?".format(new))
                    if savechanges:
                        self.project.emlns[new] = content
                    else:
                        logger.error('no name specified!')
                        return -1
            else:
                self.project.emlns[new] = content
        return 1


    def emlnfiles(self):
        return list(self.project.emlns.keys())


    def emlnfilecontent(self, filename):
        return self.project.emlns.get(filename, '').strip()

    # /EMLN FUNCTIONS #####################################

    # DB FUNCTIONS #####################################
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
            savechanges = messagebox.askyesno("Save changes", "A file '{}' already exists. Overwrite?".format(new))
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
                    savechanges = messagebox.askyesno("Save changes", "A file '{}' already exists. Overwrite?".format(new))
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

    def select_method(self, *args):
        self.set_outputfilename()
        self.settings_setdirty()


    def onchange_use_emln(self, dirty=True, *args):
        if not self.use_emln.get():
            self.emln_label.grid_forget()
            self.emln_container.grid_forget()
        else:
            self.emln_label.grid(row=self.emlncontainerrow, column=0, sticky="NE")
            self.emln_container.grid(row=self.emlncontainerrow, column=1, sticky="NWES")
        if dirty:
            self.settings_setdirty()


    def onchange_cw(self, *args):
        if self.closed_world.get():
            self.entry_cw.configure(state=DISABLED)
        else:
            self.entry_cw.configure(state=NORMAL)
        self.settings_setdirty()


    def reset_gui(self):
        self.set_config({})
        self.db_container.clear()
        self.emln_container.clear()
        self.mln_container.clear()


    def set_config(self, newconf):
        self.config = newconf
        self.selected_grammar.set(ifnone(newconf.get('grammar'), 'PRACGrammar'))
        self.selected_logic.set(ifnone(newconf.get('logic'), 'FirstOrderLogic'))
        self.mln_container.selected_file.set(ifnone(newconf.get('mln'), ''))
        if self.use_emln.get():
            self.emln_container.selected_file.set(ifnone(newconf.get('mln'), ''))
        self.db_container.selected_file.set(ifnone(newconf.get('db'), ""))
        self.selected_method.set(ifnone(newconf.get("method"), InferenceMethods.name('MCSAT'), transform=InferenceMethods.name))
        self.multicore.set(ifnone(newconf.get('multicore'), 0))
        self.profile.set(ifnone(newconf.get('profile'), 0))
        self.params.set(ifnone(newconf.get('params'), ''))
        self.use_emln.set(ifnone(newconf.get('use_emln'), 0))
        self.verbose.set(ifnone(newconf.get('verbose'), 1))
        self.ignore_unknown_preds.set(ifnone(newconf.get('ignore_unknown_preds'), 0))
        self.output_filename.set(ifnone(newconf.get('output_filename'), ''))
        self.cwPreds.set(ifnone(newconf.get('cw_preds'), ''))
        self.closed_world.set(ifnone(newconf.get('cw'), 0))
        self.save.set(ifnone(newconf.get('save'), 0))
        self.query.set(ifnone(newconf.get('queries'), ''))
        self.onchange_cw()


    def set_outputfilename(self):
        if not hasattr(self, "output_filename") or not hasattr(self, "db_filename") or not hasattr(self, "mln_filename"):
            return
        mln = self.mln_container.selected_file.get()
        db = self.db_container.selected_file.get()
        if "" in (mln, db):
            return
        if self.selected_method.get():
            method = InferenceMethods.clazz(self.selected_method.get())
            methodid = InferenceMethods.id(method)
            filename = config.query_output_filename(mln, methodid, db)
            self.output_filename.set(filename)


    def update_config(self):

        self.config = PRACMLNConfig()
        self.config["use_emln"] = self.use_emln.get()
        self.config['mln'] = self.mln_container.selected_file.get().strip().lstrip('*')
        self.config['emln'] = self.emln_container.selected_file.get().strip().lstrip('*')
        self.config["db"] = self.db_container.selected_file.get().strip().lstrip('*')
        self.config["method"] = InferenceMethods.id(self.selected_method.get().strip())
        self.config["params"] = self.params.get().strip()
        self.config["queries"] = self.query.get()
        self.config["output_filename"] = self.output_filename.get().strip()
        self.config["cw"] = self.closed_world.get()
        self.config["cw_preds"] = self.cwPreds.get()
        self.config['profile'] = self.profile.get()
        self.config['logic'] = self.selected_logic.get()
        self.config['grammar'] = self.selected_grammar.get()
        self.config['multicore'] = self.multicore.get()
        self.config['save'] = self.save.get()
        self.config['ignore_unknown_preds'] = self.ignore_unknown_preds.get()
        self.config['verbose'] = self.verbose.get()
        self.config['window_loc'] = self.master.winfo_geometry()
        self.config['dir'] = self.dir
        self.project.queryconf = PRACMLNConfig()
        self.project.queryconf.update(self.config.config.copy())


    def write_gconfig(self, savegeometry=True):
        self.gconf['prev_query_path'] = self.dir
        self.gconf['prev_query_project': self.dir] = self.project.name

        # save geometry
        if savegeometry:
            self.gconf['window_loc_query'] = self.master.geometry()
        self.gconf.dump()


    def infer(self, savegeometry=True, options={}, *args):
        mln_content = self.mln_container.editor.get("1.0", END).strip()
        db_content = self.db_container.editor.get("1.0", END).strip()

        # create conf from current gui settings
        self.update_config()

        # write gui settings
        self.write_gconfig(savegeometry=savegeometry)

        # hide gui
        self.master.withdraw()

        try:
            print((headline('PRACMLN QUERY TOOL')))
            print()

            if options.get('mlnarg') is not None:
                mlnobj = MLN(mlnfile=os.path.abspath(options.get('mlnarg')),
                             logic=self.config.get('logic', 'FirstOrderLogic'),
                             grammar=self.config.get('grammar', 'PRACGrammar'))
            else:
                mlnobj = parse_mln(mln_content, searchpaths=[self.dir],
                                   projectpath=os.path.join(self.dir, self.project.name),
                                   logic=self.config.get('logic', 'FirstOrderLogic'),
                                   grammar=self.config.get('grammar', 'PRACGrammar'))

            if options.get('emlnarg') is not None:
                emln_content = mlnpath(options.get('emlnarg')).content
            else:
                emln_content = self.emln_container.editor.get("1.0", END).strip()

            if options.get('dbarg') is not None:
                dbobj = Database.load(mlnobj, dbfiles=[options.get('dbarg')], ignore_unknown_preds=self.config.get('ignore_unknown_preds', True))
            else:
                out(self.config.get('ignore_unknown_preds', True))
                dbobj = parse_db(mlnobj, db_content, ignore_unknown_preds=self.config.get('ignore_unknown_preds', True))

            if options.get('queryarg') is not None:
                self.config["queries"] = options.get('queryarg')

            infer = MLNQuery(config=self.config, mln=mlnobj, db=dbobj, emln=emln_content)
            result = infer.run()


            # write to file if run from commandline, otherwise save result to project results
            if options.get('outputfile') is not None:
                output = io.StringIO()
                result.write(output)
                with open(os.path.abspath(options.get('outputfile')), 'w') as f:
                    f.write(output.getvalue())
                logger.info('saved result to {}'.format(os.path.abspath(options.get('outputfile'))))
            elif self.save.get():
                output = io.StringIO()
                result.write(output)
                fname = self.output_filename.get()
                self.project.add_result(fname, output.getvalue())
                self.project.save(dirpath=self.dir)
                logger.info('saved result to file results/{} in project {}'.format(fname, self.project.name))
            else:
                logger.debug('No output file given - results have not been saved.')
        except:
            traceback.print_exc()

        # restore main window
        sys.stdout.flush()
        self.master.deiconify()


def main():
    logger.level = logs.DEBUG

    usage = 'PRACMLN Query Tool'

    parser = argparse.ArgumentParser(description=usage)
    parser.add_argument("-i", "--mln", dest="mlnarg", help="the MLN model file to use")
    parser.add_argument("-d", "--dir", dest="directory", action='store', help="the directory to start the tool from", metavar="FILE", type=str)
    parser.add_argument("-x", "--emln", dest="emlnarg", help="the MLN model extension file to use")
    parser.add_argument("-q", "--queries", dest="queryarg", help="queries (comma-separated)")
    parser.add_argument("-e", "--evidence", dest="dbarg", help="the evidence database file")
    parser.add_argument("-r", "--results-file", dest="outputfile", help="the results file to save")
    parser.add_argument("--run", action="store_true", dest="run", default=False, help="run with last settings (without showing GUI)")

    args = parser.parse_args()
    opts_ = vars(args)

    root = Tk()
    conf = PRACMLNConfig(DEFAULT_CONFIG)
    app = MLNQueryGUI(root, conf, directory=os.path.abspath(args.directory) if args.directory else None)

    if args.run:
        logger.debug('running mlnlearn without gui')
        app.infer(savegeometry=False, options=opts_)
    else:
        root.mainloop()


if __name__ == '__main__':
    main()