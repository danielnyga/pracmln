import logging
import sys
from pracmln.praclog.logformat import RainbowLoggingHandler

from logging import DEBUG
from logging import INFO
from logging import WARNING
from logging import ERROR
from logging import CRITICAL

def logger(name, level=WARNING):
    _logger = logging.getLogger(name)
    _logger.setLevel(level=level)
    return _logger

root_logger = logging.getLogger()


def level(l=None):
    if l is None: return root_logger.getEffectiveLevel()
    root_logger.setLevel(l)

handler = RainbowLoggingHandler(sys.stdout)
# formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
# handler.setFormatter(formatter)
root_logger.addHandler(handler)

