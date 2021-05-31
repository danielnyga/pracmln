
Tools for Statistical Relation Learning
=======================================

Overview
^^^^^^^^

After the installation, all of these tools will be located in the 
``/path/to/pracmln/apps`` directory (which, if you've set up your 
environment correctly, is within your system ``PATH``).

Markov Logic Networks
~~~~~~~~~~~~~~~~~~~~~

* ``mlnquery`` - the :doc:`mlnquerytool`, a graphical inference tool
* ``mlnlearn`` - the :doc:`mlnlearningtool`, a graphical learning tool

Evaluation
~~~~~~~~~~

* Command-line tools (invoke for usage instructions):
  * ``xval`` - tool for conducting automated cross-validation with MLNs.

Graphical Tools and Editors
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Two graphical tools, whose usage is hopefully self-explanatory, are 
part of the package: There's an inference tool (mlnquery.py) 
and a parameter learning tool (mlnlearn.py). Simply invoke 
them using the Python interpreter. (On Windows, do not use 
pythonw.exe to run them because the console output is an integral 
part of these tools.)::

    mlnquery
    mlnlearn

General Usage
~~~~~~~~~~~~~

Both tools work with ``.mln`` and ``.db`` files in a `pracmln` project file.
A project file is a container in the `zip` format that has the file
extension ``.pracmln``. The structure of the container is as follows ::

  project-name.pracmln
      query.conf
      learn.conf
      mlns/
         ...
      dbs/
         ...
  
It consists of two ``.conf`` files that hold the settings of your
inferences and learning procedures (e.g. which algorithms to use
with wich parameters). All ``.mln`` files that can be used within
the project must go into the ``mlns`` subdirectory, whereas all
``.db`` files must be located in the ``dbs`` directory.

By default, all output files will also be written to the current project container.
 
The tools are designed to be invoked from a console. Simply change 
to the directory in which the files you want to work with are 
located and then invoke the tool you want to use, e.g. ::

    $ mlnquery

The tool will remember this directory for the 
next session and will automatically start in that directory. The
memorized directory from the last session can be overridden by a 
command-line argument, so ::

    $ mlnquery .
    
will always start in current working directory regardless of the directory
of the previous session.

The general workflow is then as follows: You select the files you 
want to work with, edit them as needed or even create new files 
directly from within the GUI. Then you set the further options 
(e.g. the number of inference steps to take) and click on the 
button at the very bottom to start the procedure.

Once you start the actual algorithm, the tool window itself will be 
hidden as long as the job is running, while the output of the 
algorithm is written to the console for you to follow. At the 
beginning, the tools list the main input parameters for your 
convenience, and, once the task is completed, the query tool 
additionally outputs the inference results to the console.

MLN Project Paths
~~~~~~~~~~~~~~~~~

Files located in a `.pracmln` project can be accessed my means  of
the :class:`pracmln.mlnpath` class. An `MLN Path` has the following form: ::

  <path-to-project>:<file-in-project>
  
where ``<path-to-project>`` is a regular relative or absolute file path
to a `.pracmln` project file and ``<file-in-project>`` is the name
of the file in the project. For example, consider that there is a 
project file ``my-project.pracmln`` in the user's home directory and we wish to access the
file ``learnt.mln`` within that project. Then, this file can be
accessed by the line ::
 
  from pracmln.utils.project import mlnpath
  p = mlnpath('/home/nyga/my-project.pracmln:learnt.mln')
  print p.content
  
``mlnpath`` returns an object of the type :class:`pracmln.mlnpath`,
which has the following members:

.. autoclass:: pracmln.mlnpath
    :members: content, path, file, project, exists, projectloc


Integrated Editors
^^^^^^^^^^^^^^^^^^

For every learning/inference task, you must specify which MLN syntax
and logic calculus is to be used:

.. figure:: _static/img/logic-grammar-selection.png

   Selection of the MLN syntax (grammar) and logic calculus.

The dropdown menus in the `MLN` and `DB` sections of the GUIs display
all MLN or DB files in the project. In order to inspect or edit
a file, just select them from the respective dropdown menu:

.. figure:: _static/img/mln-selection.png

   File selection in the GUI tools.

If you modify a file, it will be flagged as "dirty", which is indicated
by an asterisk in front of its file name. New, empty files can be added
to the project by hitting the "New" button, existing files can be
imported from the file system via the "Import..." button. Files
can also be renamed by editing their file name in the text box and hitting
the "Save" button or removed from the project with "Delete".

The tools feature integrated editors for .db and .mln files. If you 
modify a file in an internal editor, it will automatically be saved 
as soon as you invoke the learning or inference method (i.e. when 
you press the button at the very bottom) or whenever you press the 
save button to the right of the dropdown menu. If you want to save 
to a different filename, you may do so by changing the filename in 
the text input directly below the editor (which is activated as 
soon as the editor content changes) and then clicking on the save 
button. Session Management

The tools will save all the settings you made and all files when you 
hit the "save project" button. So that you can easily resume a 
session (all the information is saved to a configuration file). 
Moreover, the query tool will save context-specific information:

.. note::
    The query tool remembers the query you last made for each 
    evidence database, so when you reselect a database, the query 
    you last made with that database is automatically restored. The 
    model extension that you selected is also associated with the 
    training database (because model extensions typically serve to 
    augment the evidence, e.g. the specification of additional 
    formulas to specify virtual evidence). The additional 
    parameters you specify are saved specific to the inference 
    engine. 


Parameters
~~~~~~~~~~

There are a couple parameters that both the query tool and the learning
tool have in common, which can be set with the respective checkboxes:

* **use all CPUs** will pass a parameter instructing all algorithms 
  to distribute computation tasks over all CPUs available on the machine
  where possible. This parameter will be mapped to the ``multicore=True`` argument for
  algorithms.
  
* **use Profiler** will automatically start the learning or inference
  in the python profiler and display runtime information after the
  algorithms have finished. This is useful for code optimization if
  you intend to implement your own learning or reasoning methods.
  
* **verbose** will tell the algorithms to display nicely formatted
  progress information during runtime, a summary of all parameters passed
  to the algorithms, the final learnt model or nicely formatted inference results.

* **Add. params** Additional parameters to pass to the inference or learning method.
  For every method, you can specify a comma-separated list 
  of assignments of parameters of the infer method you are 
  calling. For example, with ``debug='DEBUG'`` one can set the
  internal log level to ``DEBUG``. 
  
For a more detailed overview of the parameters, see 
:doc:`inferencemethods` and :doc:`learningmethods`.
    
    
