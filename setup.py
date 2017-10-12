import glob
import os

from setuptools import setup

import _version

__basedir__ = _version.__basedir__
__version__ = _version.__version__


def basedir(name):
    return os.path.join(__basedir__, name)


with open(os.path.join(os.path.dirname(__file__), __basedir__, 'requirements.txt'), 'r') as f:
    requirements = [l.strip() for l in f.readlines() if l.strip()]


def datafiles(d):
    data_files = []
    for root, dirs, files in os.walk(os.path.join(os.path.dirname(__file__), d)):
        if not files: continue
        data_files.append((root, [os.path.join(root, f) for f in files]))

    return data_files


setup(
    name='pracmln',
    packages=['pracmln', 'pracmln._version', 'pracmln.logic', 'pracmln.mln',
        'pracmln.utils', 'pracmln.wcsp', 'pracmln.mln.grounding',
        'pracmln.mln.inference', 'pracmln.mln.learning'],
    package_dir={
        'pracmln': basedir('pracmln'),
        'pracmln._version': '_version',
    },
    data_files=datafiles('examples') + datafiles('3rdparty') + datafiles('libpracmln'),
    version=__version__,
    description='A collection of convenience tools for everyday Python programming',
    author='Daniel Nyga',
    author_email='nyga@cs.uni-bremen.de',
    url='https://pracmln.org',
    download_url='https://github.com/danielnyga/pracmln/archive/%s.tar.gz' % __version__,
    keywords=['statistical relational learning', 'mln', 'Markov logic networks', 'reasoning', 'probcog'],
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 4 - Beta',

        # Indicate who your project is intended for
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Scientific/Engineering :: Artificial Intelligence ',

        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: MIT License',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
    ],
    install_requires=requirements,
    entry_points={
        'console_scripts': [
            'mlnlearn=pracmln.mlnlearn:main',
	        'mlnquery=pracmln.mlnquery:main',
	        'libpracmln-build=pracmln.libpracmln:createcpplibs',
            'pracmlntest=pracmln.test:main',
        ],
    },
)

