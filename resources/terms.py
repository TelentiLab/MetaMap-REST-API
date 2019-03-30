import os
import time
import traceback
from concurrent.futures.process import ProcessPoolExecutor
from flask_restful import Resource, reqparse
from libs.omim import get_omim
from libs.pubmed import get_pubmed
from libs.metamapy import MetaMaPY
from query_cache import QueryCache
from logger import logger

ERROR_MISSING_ARGS = 'missing argument `{}` in request body.'
MAX_PROCESSES = int(os.getenv('MAX_PROCESSES', 1))
logger.info(f'MAX_PROCESSES={MAX_PROCESSES}')
_cache = QueryCache()


class Article(Resource):
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
    def post(cls):
        data = cls.parser.parse_args(strict=True)
        article_list = data['articles']
        logger.debug(f'request received for {len(article_list)} articles.')
        try:
            metamapy = MetaMaPY(MAX_PROCESSES)
            res = metamapy.run(article_list)  # run MetaMap
            return {'terms': res}, 200
        except:
            logger.error(f'Error occurs while responding request for articles.')
            logger.error(traceback.format_exc())
            return {'message': f'An error has occurred, please contact developer.'}, 500


class Keyword(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('use_cache', type=bool)

    def post(self, keyword: str):
        data = self.parser.parse_args()
        use_cache = data['use_cache']
        print(use_cache)
        if use_cache is None:
            use_cache = True  # default to use cache
        logger.debug(f'Request received for {keyword}.')
        logger.debug(f'use_cache={use_cache}.')
        try:
            if use_cache:
                res = _cache.get(keyword)  # try to use cache first
                if res:  # hit
                    logger.info(f'{keyword} hits cache.')
                    return {
                               'keyword': keyword,
                               'terms': res,
                           }, 200
                # miss
                logger.info(f'{keyword} misses cache.')

            pre_fetch = time.time()
            with ProcessPoolExecutor(max_workers=2) as pool:
                future_omim = pool.submit(get_omim, keyword)
                future_pubmed = pool.submit(get_pubmed, keyword)
            post_fetch = time.time()
            logger.info(f'Querying OMIM and Pubmed took {post_fetch - pre_fetch}s.')
            pubmed_result = future_pubmed.result()
            omim_result = future_omim.result()

            articles = pubmed_result if pubmed_result else []
            if omim_result:
                articles.append(omim_result)

            metamapy = MetaMaPY(MAX_PROCESSES)
            res = metamapy.run(articles)  # run MetaMap if cache misses
            _cache.memorize(keyword, res)
            return {
                       'keyword': keyword,
                       'terms': res,
                   }, 200
        except:
            logger.error(f'Error occurs while responding request for {keyword}.')
            logger.error(traceback.format_exc())
            return {
                       'message': f'An error has occurred while querying MetaMap for {keyword}, please contact developer.'
                   }, 500
