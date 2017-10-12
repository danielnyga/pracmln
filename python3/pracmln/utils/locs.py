import os

_home = __file__.split(os.path.sep)[:-3]
home = os.path.sep.join(_home)
trdparty = os.path.join(home, '3rdparty')
