import logging

from .server import start

log_format = "%(asctime)s [%(levelname)-7s] [%(name)-15s] %(message)s"
logging.basicConfig(level=logging.DEBUG, format=log_format)

start()
