import os

import appdirs
from pracmln._version import APPNAME, APPAUTHOR

home = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', '..'))
if os.path.basename(home).startswith('python'):
    home = os.path.realpath(os.path.join(home, '..'))
trdparty = os.path.join(home, '3rdparty')
examples = os.path.join(home, 'examples')
datapathroot = appdirs.site_data_dir(APPNAME, APPAUTHOR)
datapathnonroot = appdirs.user_data_dir(APPNAME, APPAUTHOR)
