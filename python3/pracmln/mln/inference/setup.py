from distutils.core import setup
#from distutils.extension import Extension
from Cython.Build import cythonize

#'''
#ext_modules=[
#    Extension("exact",       ["exact.pyx"]),
#    Extension("mcmc",         ["mcmc.pyx"]),
#]
#'''

setup(
    ext_modules=cythonize( ['*.pyx'] )
)
