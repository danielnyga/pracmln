import traceback
from multiprocessing import Pool
import sys
import signal
import os
from pracmln.mln.errors import OutOfMemoryError
import psutil

class CtrlCException(Exception): pass

class with_tracing(object):
    '''
    Wrapper class for functions intended to be executed in parallel
    on multiple cores. This facilitates debugging with multiprocessing.
    '''
    
    def __init__(self, func):
        self.func = func
        
    def __call__(self, *args, **kwargs):
        signal.signal(signal.SIGINT, signal_handler)
        try:
            result = self.func(*args,**kwargs)
            return result
        except CtrlCException: pass
#             traceback.print_exc()
#             sys.exit(0)
        except Exception, e:
            traceback.print_exc()
            raise e
        

def signal_handler(signal, frame):
    sys.stderr.write('Terminating process %s.\n' % os.getpid())
    raise CtrlCException()
    sys.exit(0)

class _methodcaller:
    '''
    Convenience class for calling a method of an object in a worker pool  
    '''
    
    
    def __init__(self, method, sideeffects=False):
        self.method = method
        self.sideeffects = sideeffects
        
    def __call__(self, args):
        checkmem()
        if type(args) is list or type(args) is tuple:
            inst = args[0]
            args = args[1:]
        else:
            inst = args
            args = []
        if self.sideeffects:
            ret = getattr(inst, self.method)(*args)
            return ret, inst.__dict__
        return getattr(inst, self.method)(*args)
    

def checkmem():
    if float(psutil.phymem_usage().percent) > 75.:
        raise OutOfMemoryError('Aborting due to excessive memory consumption.')

def make_memsafe():
    if sys.platform.startswith('linux'):
        import resource
        import psutil
        for rsrc in (resource.RLIMIT_AS, resource.RLIMIT_DATA):
            freemem = psutil.virtmem_usage().free
            hard = int(round(freemem *.8))
            soft = hard
            resource.setrlimit(rsrc, (soft, hard)) #limit to 80% of available memory
    

# exmaple how to be used
if __name__ == '__main__':
    def f(x):
        return x*x
    pool = Pool(processes=4)              # start 4 worker processes
    print pool.map(with_tracing(f), range(10))          # prints "[0, 1, 4,..., 81]"
    
    
   
            
