#!/usr/bin/python2.5
 # Until Python 2.6



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
import sys
import tempfile
import getopt
from PIL import Image
import base64

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
            dvicmd = "dvisvgm -o {}.svg --no-fonts {} >/dev/null".format(outfilename, dvifile)
        else:
            dvicmd = "dvipng -q* -T tight -x {} -z 9 -bg Transparent "\
                    "-o {}.png {} >/dev/null".format(size * 1000, outfilename, dvifile)
        rc = os.system(dvicmd)
        if rc != 0:
            raise Exception('{} error'.format('dvisvgm error' if svg else'dvipng'))
    finally:
        # Cleanup temporaries
        basefile = infile.replace('.tex', '')
        tempext = [ '.aux', '.dvi', '.log' ]
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
    try:
        # Set the working directory
        workdir = tempfile.gettempdir()

        # Get a temporary file
        fd, texfile = tempfile.mkstemp('.tex', 'eq', workdir, True)

        content = content.replace('$', r'\$')

        # Create the TeX document and save to tempfile
        fileContent = '{}$${}$$\n\end{{document}}'.format(__build_preamble(packages, declarations), content)

        with os.fdopen(fd, 'w+') as f:
            f.write(fileContent)

        __write_output(texfile, outdir, workdir=workdir, filename=filename, size=size, svg=svg)
    finally:
        outfilename = os.path.join(outdir, '{}.{}'.format(filename, 'svg' if svg else 'png'))


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
        if os.path.exists(texfile):
            os.remove(texfile)
        if os.path.exists(outfilename):
            os.remove(outfilename)

        return (filecontent, ratio)


def usage():
    print('''
Usage: {} [OPTION] ... [FILE] ...
Converts LaTeX math input to PNG.

Options are:
    -h, --help              Display this help information
    --outdir=OUTDIR         PNG file output directory 
                            Default: the current working directory
    --packages=PACKAGES     Comma separated list of packages to use
                            Default: amsmath,amsthm,amssymb,bm
    --declarations=DECLS    Comma separated list of declarations to use
                            Default: ''
    --filename=filename         filename output file names with filename
                            Default: no filename
    --scale=SCALE           Scale the output by a factor of SCALE. 
                            Default: 1 = 100%%

Reads equations from the specified FILEs or standard input if none is given. One
equation is allowed per line of text and each equation is rendered to a separate
PNG image numbered sequentially from 1, with an optional filename.
    '''.format(os.path.split(sys.argv[0])[1]))

def main():
    try:
        shortopts = [ 'h', ]
        longopts = [
                'help',
                'outdir=',
                'packages=',
                'filename=',
                ]
        opts, args = getopt.getopt(sys.argv[1:], shortopts, longopts)
    except getopt.GetoptError as err:
        scriptname = os.path.split(sys.argv[0])[1]
        print("{}: {}".format(scriptname, err))
        print("Try `{} --help` for more information.".format(scriptname))
        sys.exit(2)

    packages = []
    declarations = []
    filename = ''
    outdir = os.getcwd()
    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
            sys.exit()
        if o in ("--packages"):
            packages = a.split(',')
        if o in ("--declarations"):
            declarations = a.split(',')
        if o in ("--filename"):
            filename = a
        if o in ("--outdir"):
            outdir = os.path.abspath(a)

    input = ''
    if args:
        # If filenames were provided on the command line, read their equations
        for a in args:
            fd = os.open(a, os.O_RDONLY)
            with os.fdopen(fd, 'r') as f:
                cur = [i.strip('\n') for i in f.readlines()]
                input.extend(cur)
    else:
        # Otherwise read from stdin
        input = [i.strip('\n') for i in sys.stdin.readlines()]

    # Engage!
    math2png(input, outdir, packages, declarations, filename)

if __name__ == '__main__':
    main()
