"""
_version
Version information for pracmln.
"""
import sys

__all__ = [
    'VERSION_MAJOR',
    'VERSION_MINOR',
    'VERSION_PATCH',
    'VERSION_STRING',
    'APPNAME',
    'APPAUTHOR',
    '__version__',
    '__basedir__'
]

APPNAME = 'pracmln'
APPAUTHOR = 'danielnyga'

VERSION_MAJOR = 1
VERSION_MINOR = 2
VERSION_PATCH = 3

VERSION_STRING_FULL = '%s.%s.%s' % (VERSION_MAJOR, VERSION_MINOR, VERSION_PATCH)
VERSION_STRING_SHORT = '%s.%s' % (VERSION_MAJOR, VERSION_MINOR)

__version__ = VERSION_STRING_FULL

if sys.version_info[0] == 2:
    __basedir__ = 'python2'
elif sys.version_info[0] == 3:
    __basedir__ = 'python3'
else:
    raise Exception('Unsupported Python version: %s' % sys.version_info[0])
