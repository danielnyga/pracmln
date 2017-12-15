#!/usr/bin/python2.5
 # Until Python 2.6

from dnutils import logs

from pracmln.utils import locs


"""
Converts LaTeX math to png images.
Run latexmath2png.py --help for usage instructions.
"""

"""
Author:
    Kamil Kisiel <kamil@kamilkisiel.net>
    URL: http://www.kamilkisiel.net

Revision History:
    2007/04/20 - Initial version

TODO:
    - Make handling of bad input more graceful?
---

Some ideas borrowed from Kjell Fauske's article at http://fauskes.net/nb/htmleqII/

Licensed under the MIT License:

Copyright (c) 2007 Kamil Kisiel <kamil@kamilkisiel.net>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS 
IN THE SOFTWARE.
"""

import os
import tempfile
from PIL import Image
import base64

logger = logs.getlogger(__name__, logs.DEBUG)

# Default packages to use when generating output
default_packages = [
        'amsmath',
        'amsthm',
        'amssymb',
        'bm'
        ]


def __build_preamble(packages, declarations):
    preamble = '\documentclass{article}\n'
    for p in packages:
        preamble += "\\usepackage{{{}}}\n".format(p)

    for d in declarations:
        preamble += '{}\n'.format(d)

    preamble += "\pagestyle{empty}\n\\begin{document}\n"
    return preamble


def __write_output(infile, outdir, workdir='.', filename='', size=1, svg=True):
    try:
        # Generate the DVI file. NOTE: no output in stdout, as it is piped into /dev/null!
        latexcmd = 'latex -halt-on-error -output-directory {} {} >/dev/null'.format(workdir, infile)
        rc = os.system(latexcmd)

        # Something bad happened, abort
        if rc != 0:
            raise Exception('latex error')

        # Convert the DVI file to PNG's
        dvifile = infile.replace('.tex', '.dvi')
        outfilename = os.path.join(outdir, filename)

        if svg:
            dvicmd = "dvisvgm -v 0 -o {}.svg --no-fonts {}".format(outfilename, dvifile)
        else:
            dvicmd = "dvipng -q* -T tight -x {} -z 9 -bg Transparent -o {}.png {} >/dev/null".format(size * 1000, outfilename, dvifile)
        rc = os.system(dvicmd)
        if rc != 0:
            raise Exception('{} error'.format('dvisvgm error' if svg else'dvipng'))
    finally:
        # Cleanup temporaries
        basefile = infile.replace('.tex', '')
        tempext = ['.aux', '.dvi', '.log']
        for te in tempext:
            tempfile = basefile + te
            if os.path.exists(tempfile):
                os.remove(tempfile)


def math2png(content, outdir, packages=default_packages, declarations=[], filename='', size=1, svg=True):
    """
    Generate png images from $$...$$ style math environment equations.

    Parameters:
        content      - A string containing latex math environment formulas
        outdir       - Output directory for PNG images
        packages     - Optional list of packages to include in the LaTeX preamble
        declarations - Optional list of declarations to add to the LaTeX preamble
        filename     - Optional filename for output files
        size         - Scale factor for output
    """
    outfilename = '/tmp/default.tex'
    # Set the working directory
    workdir = tempfile.gettempdir()

    # Get a temporary file
    fd, texfile = tempfile.mkstemp('.tex', 'eq', workdir, True)
    try:
        content = content.replace('$', r'\$')

        # Create the TeX document and save to tempfile
        fileContent = '{}$${}$$\n\end{{document}}'.format(__build_preamble(packages, declarations), content)

        with os.fdopen(fd, 'w+') as f:
            f.write(fileContent)

        __write_output(texfile, outdir, workdir=workdir, filename=filename, size=size, svg=svg)
        outfilename = os.path.join(outdir, '{}.{}'.format(filename, 'svg' if svg else 'png'))

    except:
        logger.error('Unable to create image. A reason you encounter '
                     'this error might be that you are either missing latex '
                     'packages for generating .dvi files or {} for '
                     'generating the {} image from the .dvi file.'.format('dvisvgm' if svg else 'dvipng', 'svg' if svg else 'png'))
        outfilename = os.path.join(locs.etc, 'default.{}'.format('svg' if svg else 'png'))
    finally:
        if svg:
            with open(outfilename, 'r') as outfile:
                filecontent = outfile.read()
                ratio = 1
        else:
            # determine image size
            im = Image.open(outfilename)
            width, height = im.size
            ratio = float(width)/float(height)

            # create base64 encoded file content
            png = open(outfilename)
            filecontent = base64.b64encode(png.read())

        # cleanup and delete temporary files
        if os.path.exists(texfile) and locs.etc not in outfilename:
            os.remove(texfile)
        if os.path.exists(outfilename) and locs.etc not in outfilename:
            os.remove(outfilename)
        return filecontent, ratio