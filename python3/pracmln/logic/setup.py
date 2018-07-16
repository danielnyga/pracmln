from distutils.core import setup
from Cython.Build import cythonize

setup(
    ext_modules=cythonize("*.pyx", compiler_directives={'profile': True})
)
