#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
import stat
import sys
import platform
import shutil
import imp

sys.path.append(os.path.join(os.getcwd(), 'pracmln'))
sys.path.append(os.path.join(os.getcwd(), '3rdparty', 'logutils-0.3.3'))

from pracmln.mln.util import colorize

packages = [('numpy', 'numpy', False), ('tabulate', 'tabulate', False), ('pyparsing', 'pyparsing', False), ('psutil', 'psutil', False), ('matplotlib', 'matplotlib', False)]

def check_package(pkg):
    try:
        sys.stdout.write('checking dependency %s...' % pkg[0]) 
        imp.find_module(pkg[0])
        sys.stdout.write(colorize('OK', (None, 'green', True), True))
        print
    except ImportError: 
        print
        print colorize('%s was not found. Please install by "sudo pip install %s" %s' % (pkg[0], pkg[1], '(optional)' if pkg[2] else ''), (None, 'yellow', True), True)

    
# check the package dependecies
def check_dependencies():
    for pkg in packages:
        check_package(pkg)
    
python_apps = [
    {"name": "mlnquery", "script": "$PRACMLN_HOME/pracmln/mlnquery.py"},
    {"name": "mlnlearn", "script": "$PRACMLN_HOME/pracmln/mlnlearn.py"},
    {"name": "xval", "script": "$PRACMLN_HOME/pracmln/xval.py"},
]

def adapt(name, arch):
    return name.replace("<ARCH>", arch).replace("$PRACMLN_HOME", os.path.abspath(".")).replace("/", os.path.sep)

def buildLibpracmln():
    envSetup  = 'export LD_LIBRARY_PATH="{0}/lib:${{LD_LIBRARY_PATH}}"\n'
    envSetup += 'export LIBRARY_PATH="{0}/lib:${{LIBRARY_PATH}}"\n'
    envSetup += 'export CPATH="{0}/include:${{CPATH}}"\n'
    envSetup += 'export CMAKE_LIBRARY_PATH="{0}/lib:${{CMAKE_LIBRARY_PATH}}"\n'
    envSetup += 'export CMAKE_INCLUDE_PATH="{0}/include:${{CMAKE_INCLUDE_PATH}}"\n'

    oldwd = os.getcwd()
    basePath = os.path.join(os.getcwd(), 'libpracmln')
    buildPath = os.path.join(basePath, 'build')
    installPath = os.path.join(basePath, 'install')

    if os.path.exists(buildPath):
        shutil.rmtree(buildPath, True)
    if os.path.exists(installPath):
        shutil.rmtree(installPath, True)

    os.mkdir(buildPath)
    os.chdir(buildPath)

    ret = os.system("cmake ..")
    if ret != 0:
        os.chdir(oldwd)
        return None

    ret = os.system("make")
    if ret != 0:
        os.chdir(oldwd)
        return None

    ret = os.system("make install")
    if ret != 0:
        os.chdir(oldwd)
        return None

    os.chdir(oldwd)

    return envSetup.format(installPath)
    

if __name__ == '__main__':

    archs = ["win32", "linux_amd64", "linux_i386", "macosx", "macosx64"]

    args = sys.argv[1:]

    if '--help' in args:        
        print "PRACMLNs Apps Generator\n\n"
        print "  usage: make_apps [--arch=%s] [--cppbindings]\n" % "|".join(archs)
        print
        print
        exit(0)
    
    # determine architecture
    arch = None
    bits = 64 if "64" in platform.architecture()[0] else 32
    if len(args) > 0 and args[0].startswith("--arch="):
        arch = args[0][len("--arch="):].strip()
        args = args[1:]
    elif platform.mac_ver()[0] != "":
        arch = "macosx" if bits == 32 else "macosx64"
    elif platform.win32_ver()[0] != "":
        arch = "win32"
    elif platform.dist()[0] != "":
        arch = "linux_i386" if bits == 32 else "linux_amd64"
    if arch is None:
        print "Could not automatically determine your system's architecture. Please supply the --arch argument"
        sys.exit(1)
    if arch not in archs:
        print "Unknown architecture '%s'" % arch
        sys.exit(1)

    check_dependencies()

    buildlib = False
    if "--cppbindings" in args:
        buildlib = True;
#         args = args[1:]

    print 'Removing old app folder...'
    shutil.rmtree('apps', ignore_errors=True)

    if not os.path.exists("apps"):
        os.mkdir("apps")

    print "\nCreating application files for %s..." % arch
    isWindows = "win" in arch
    isMacOSX = "macosx" in arch
    preamble = "@echo off\r\n" if isWindows else "#!/bin/sh\n"
    allargs = '%*' if isWindows else '"$@"'
    pathsep = os.path.pathsep
    
    for app in python_apps:
        filename = os.path.join("apps", "%s%s" % (app["name"], {True:".bat", False:""}[isWindows]))
        print "  %s" % filename
        f = file(filename, "w")
        f.write(preamble)
        f.write("python -O \"%s\" %s\n" % (adapt(app["script"], arch), allargs))
        f.close()
        if not isWindows: os.chmod(filename, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
    
    print

    # write shell script for environment setup
    appsDir = adapt("$PRACMLN_HOME/apps", arch)
    logutilsDir = adapt("$PRACMLN_HOME/3rdparty/logutils-0.3.3", arch)

    # make the experiments dir
    if not os.path.exists('experiments'):
        os.mkdir('experiments')

    extraExports = None
    if not "win" in arch and buildlib:
        extraExports = buildLibpracmln()

    if not "win" in arch:
        f = file("env.sh", "w")
        f.write('#!/bin/bash\n')
        f.write("export PATH=$PATH:%s\n" % appsDir)
        f.write("export PYTHONPATH=$PYTHONPATH:%s\n" % logutilsDir)
        f.write("export PRACMLN_HOME=%s\n" % adapt("$PRACMLN_HOME", arch))
        f.write("export PYTHONPATH=$PRACMLN_HOME:$PYTHONPATH\n")
        f.write("export PRACMLN_EXPERIMENTS=%s\n" % adapt(os.path.join("$PRACMLN_HOME", 'experiments'), arch))
        if extraExports:
            f.write(extraExports)
        f.close()
        print 'Now, to set up your environment type:'
        print '    source env.sh'
        print
        print 'To permantly configure your environment, add this line to your shell\'s initialization script (e.g. ~/.bashrc):'
        print '    source %s' % adapt("$PRACMLN_HOME/env.sh", arch)
        print
    else:
        pypath = ';'.join([adapt("$PRACMLN_HOME", arch), logutilsDir])
        f = file("env.bat", "w")
        f.write("@ECHO OFF\n")
        f.write('SETX PATH "%%PATH%%;%s"\r\n' % appsDir)
        f.write('SETX PRACMLN_HOME "%s"\r\n' % adapt("$PRACMLN_HOME", arch))
        f.write('SETX PYTHONPATH "%%PYTHONPATH%%;%s"\r\n' % pypath)
        f.write('SETX PRACMLN_EXPERIMENTS "%s"\r\n' % adapt(os.path.join("$PRACMLN_HOME", 'experiments'), arch))
        f.close()
        print 'To temporarily set up your environment for the current session, type:'
        print '    env.bat'
        print
        print 'To permanently configure your environment, use Windows Control Panel to set the following environment variables:'
        print '  To the PATH variable add the directory "%s"' % appsDir
        print 'Should any of these variables not exist, simply create them.'