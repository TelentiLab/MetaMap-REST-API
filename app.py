import logging
import os
import traceback

from flask import Flask
from flask_restful import Resource, Api, reqparse
from metamapy import MetaMaPY
from query_cache import QueryCache

app = Flask(__name__)
api = Api(app)
MAX_PROCESSES = int(os.getenv('MAX_PROCESSES', 1))
CACHE_SIZE = int(os.getenv('CACHE_SIZE', 30))
LOGGING_LEVEL = os.getenv('LOGGING_LEVEL', logging.INFO)

# configure logger
logging.basicConfig(format='%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s', level=LOGGING_LEVEL)
logger = logging.getLogger('MetaMaPY')
logger.info('app starts.')
logger.info(f'MAX_PROCESSES={MAX_PROCESSES}')
logger.info(f'CACHE_SIZE={CACHE_SIZE}')
logger.info(f'LOGGING_LEVEL={LOGGING_LEVEL}')

_cache = QueryCache(CACHE_SIZE)


class Terms(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('text', type=str, required=True, help="missing argument 'text' in request body.")
    parser.add_argument('keyword', type=str, required=True, help="missing argument 'keyword' in request body.")

    def post(self):
        data = self.parser.parse_args()
        key = data['keyword']
        text = data['text']
        logger.info(f'request received for {key}.')
        try:
            metamapy = MetaMaPY(MAX_PROCESSES)
            if key in _cache:  # try to use cache first
                logger.info(f'{key} hits cache.')
                return {'terms': _cache.get(key)}, 200

            logger.info(f'{key} misses cache.')
            res = metamapy.run(text)  # run MetaMap if cache misses
            _cache.memorize(key, res)
            return {'terms': res}, 200
        except:
            logger.error(f'Error occurs while responding request for {key}.')
            traceback.print_exc()
            return {
                       'message': f'An error has occurred while querying MetaMap for {key}, please contact developer.'
                   }, 500


api.add_resource(Terms, '/metamap')

if __name__ == '__main__':
    app.run(debug=True)
