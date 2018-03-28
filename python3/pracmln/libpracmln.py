import os

import shutil

from pracmln.utils import locs


envSetup = '''
export LD_LIBRARY_PATH="{0}/lib:${{LD_LIBRARY_PATH}}"
export LIBRARY_PATH="{0}/lib:${{LIBRARY_PATH}}"
export CPATH="{0}/include:${{CPATH}}"
export CMAKE_LIBRARY_PATH="{0}/lib:${{CMAKE_LIBRARY_PATH}}"
export CMAKE_INCLUDE_PATH="{0}/include:${{CMAKE_INCLUDE_PATH}}"'''

def createcpplibs():

    lib_home = os.path.join(locs.app_data, 'libpracmln')

    oldwd = os.getcwd()
    basePath = os.path.join(os.getcwd(), 'libpracmln')
    buildPath = os.path.join(basePath, 'build')
    installPath = os.path.join(basePath, 'install')

    if os.path.exists(basePath):
        shutil.rmtree(basePath, True)
    if os.path.exists(buildPath):
        shutil.rmtree(buildPath, True)
    if os.path.exists(installPath):
        shutil.rmtree(installPath, True)

    os.mkdir(basePath)
    os.mkdir(buildPath)
    os.chdir(buildPath)

    os.environ["PYTHONDIST"] = "3.5"

    ret = os.system("cmake {}".format(lib_home)+" -DCMAKE_INSTALL_PREFIX="+installPath)
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
