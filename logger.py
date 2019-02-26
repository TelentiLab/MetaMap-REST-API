import logging
import os

LOGGING_LEVEL = os.getenv('LOGGING_LEVEL', logging.INFO)

# configure logger
logging.basicConfig(format='%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s', level=LOGGING_LEVEL)
logger = logging.getLogger('MetaMaPY')
logger.info(f'LOGGING_LEVEL={LOGGING_LEVEL}')
