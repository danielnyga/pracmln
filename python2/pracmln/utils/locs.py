import os

home = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', '..'))
if os.path.basename(home).startswith('python'):
    home = os.path.realpath(os.path.join(home, '..'))
trdparty = os.path.join(home, '3rdparty')
examples = os.path.join(home, 'examples')
