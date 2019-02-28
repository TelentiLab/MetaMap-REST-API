import os
import traceback
from flask_restful import Resource, reqparse
from libs.omim import get_omim
from metamapy import MetaMaPY
from query_cache import QueryCache
from logger import logger

ERROR_MISSING_ARGS = 'missing argument `{}` in request body.'
MAX_PROCESSES = int(os.getenv('MAX_PROCESSES', 1))
logger.info(f'MAX_PROCESSES={MAX_PROCESSES}')
_cache = QueryCache()


class Variant(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('articles', type=dict, action='append', required=True,
                        help=ERROR_MISSING_ARGS.format('articles'))

    nested_parser = reqparse.RequestParser()
    nested_parser.add_argument('source', type=str, required=True, location='articles',
                               help=ERROR_MISSING_ARGS.format('source'))
    nested_parser.add_argument('id', type=str, required=True, location='articles', help=ERROR_MISSING_ARGS.format('id'))
    nested_parser.add_argument('text', type=str, required=True, location='articles',
                               help=ERROR_MISSING_ARGS.format('text'))

    @classmethod
    def post(cls, rsid: str):
        data = cls.parser.parse_args(strict=True)
        article_list = data['articles']
        logger.debug(f'request received for {rsid}.')
        try:
            res = _cache.get(rsid)  # try to use cache first
            if res:  # hit
                logger.info(f'{rsid} hits cache.')
                return {
                           'rsid': rsid,
                           'terms': res,
                       }, 200

            # miss
            logger.info(f'{rsid} misses cache.')
            metamapy = MetaMaPY(MAX_PROCESSES)
            omim = get_omim(rsid)
            if omim:
                article_list.append(omim)
            res = metamapy.run(article_list)  # run MetaMap if cache misses
            _cache.memorize(rsid, res)
            return {
                       'rsid': rsid,
                       'terms': res,
                   }, 200
        except:
            logger.error(f'Error occurs while responding request for {rsid}.')
            logger.error(traceback.format_exc())
            return {
                       'message': f'An error has occurred while querying MetaMap for {rsid}, please contact developer.'
                   }, 500
