"""Sphinx ReadTheDocs theme.

From https://github.com/ryan-roemer/sphinx-bootstrap-theme.

"""
import os

VERSION = (0, 1, 8)

__version__ = ".".join(str(v) for v in VERSION)
__version_full__ = __version__

print "loading prac_theme"

def get_html_theme_path():
    """Return list of HTML theme paths."""
    cur_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    print cur_dir
    return cur_dir
