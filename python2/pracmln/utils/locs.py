import os

import appdirs
from pracmln._version import APPNAME, APPAUTHOR

root = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', '..'))
user_data = appdirs.user_data_dir(APPNAME, APPAUTHOR)

if os.path.basename(root).startswith('python'):
    root = os.path.realpath(os.path.join(root, '..'))
    app_data = root
else:
    app_data = appdirs.site_data_dir(APPNAME, APPAUTHOR)
    if not os.path.exists(app_data):
        app_data = user_data

trdparty = os.path.join(app_data, '3rdparty')
examples = os.path.join(app_data, 'examples')
etc = os.path.join(app_data, 'etc')
