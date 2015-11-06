import logging
from pracmln.praclog.logformat import RainbowLoggingHandler
import sys

from logging import DEBUG
from logging import INFO
from logging import WARNING
from logging import ERROR

def logger(name): return logging.getLogger(name)

root_logger = logging.getLogger()



def level(l=None):
    if l is None: return root_logger.getEffectiveLevel()
    root_logger.setLevel(l)

handler = RainbowLoggingHandler(sys.stdout)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
root_logger.addHandler(handler)

