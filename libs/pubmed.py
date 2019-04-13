import os
import requests
from typing import Union, Dict, List
from xml.etree import ElementTree
from xml.etree.ElementTree import Element
from requests.exceptions import Timeout

from utils.logger import logger

"""
Read from env for PUBMED_KEY, PUBMED_TIMEOUT and PUBMED_RET_MAX 
PUBMED_KEY is required and allow us to query PubMed at a higher rate.
PUBMED_TIMEOUT is optional, defines the request timeout for both e-search and e-fetch, defaults to 3.5s
PUBMED_RET_MAX is optional, defines the max return size (number of articles), defaults to 50
"""
PUBMED_BASE_URL = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils'
PUBMED_API_KEY = os.getenv('PUBMED_KEY')
if not PUBMED_API_KEY:
    raise EnvironmentError('Must specify PUBMED_KEY in environment.')

API_KEY_ARGS = f'api_key={PUBMED_API_KEY}'

try:
    TIMEOUT = float(os.getenv('PUBMED_TIMEOUT', 3.5))
    logger.info(f'PUBMED timeout set to {TIMEOUT}')
except TypeError:
    raise EnvironmentError('Expect PUBMED_TIMEOUT to evaluate to a number.')

try:
    PUBMED_RET_MAX = int(os.getenv('PUBMED_RET_MAX', 50))
    logger.info(f'PUBMED max return size set to {PUBMED_RET_MAX}')
except TypeError:
    raise EnvironmentError('Expect PUBMED_RET_MAX to evaluate to a number.')


def get_pubmed(term: str) -> Union[None, List]:
    """
    Use sequential requests to query PubMed (search and then fetch) using the ESearch and EFetch from E-utilities
    :param term:
    :return:
    """
    search_res = _search_pubmed(term)

    if not search_res or search_res.get('count') <= 0:
        logger.debug('PUBMED no result.')
        return None

    web_env = search_res.get('web_env')
    query_key = search_res.get('query_key')

    return _fetch_pubmed(web_env=web_env, query_key=query_key)


def _search_pubmed(term: str) -> Union[Dict, None]:
    try:
        args = f'db=pubmed&term={term}&usehistory=y&retmax={PUBMED_RET_MAX}&{API_KEY_ARGS}'
        res = requests.get(f'{PUBMED_BASE_URL}/esearch.fcgi?{args}', timeout=TIMEOUT)
    except Timeout:
        logger.error(f'PUBMED search request timeout. (>{TIMEOUT}s)')
        return None

    if res.status_code == 200:  # ESearch succeeded
        logger.debug('PUBMED search request succeeded.')
        xml = ElementTree.fromstring(res.text)
        logger.debug(xml)
        if xml.tag != 'eSearchResult':
            logger.error(f'PUBMED search result has wrong format.')
            return None

        try:  # Retrieve data fields for EFetch
            count = int(xml.find('./Count').text)
            query_key = xml.find('./QueryKey').text
            web_env = xml.find('./WebEnv').text
            return {
                'count': count,
                'query_key': query_key,
                'web_env': web_env
            }
        except AttributeError as e:
            logger.error(f'PubMed ESearch result has wrong format. {e}')
            return None
        except ValueError as e:
            logger.error(f'Failed to cast type. {e}')
            return None
    # else: no result or failed
    logger.debug('PubMed ESearch request failed.')
    logger.debug(res.text)
    return None


def _fetch_pubmed(web_env: str, query_key: str) -> List:
    result = []
    try:
        args = f'db=pubmed&WebEnv={web_env}&query_key={query_key}&retmode=xml&retmax={PUBMED_RET_MAX}&{API_KEY_ARGS}'
        res = requests.get(f'{PUBMED_BASE_URL}/efetch.fcgi?{args}', timeout=TIMEOUT)
    except Timeout:
        logger.error(f'PUBMED EFetch request timeout. (>{TIMEOUT}s)')
        return result

    if res.status_code == 200:  # ESearch succeeded
        logger.debug('PubMed search request succeeded.')
        xml: Element = ElementTree.fromstring(res.text)
        if xml is None or xml.tag != 'PubmedArticleSet':
            logger.error(f'PubMed EFetch result has wrong format.')
            return result

        a_count = 0
        for each in xml.findall('./PubmedArticle/MedlineCitation'):
            a_count += 1
            p_count = 0
            # parse pubmed ID
            pubmed_id: Element = each.find('./PMID')
            if pubmed_id is None:
                logger.error(f'Failed to parse PMID')
                continue
            pubmed_id: str = pubmed_id.text

            # parse title
            article: Element = each.find('./Article')
            if article is None:
                logger.error(f'Failed to locate Article section for article #{a_count}')
                continue

            title: Element = article.find('ArticleTitle')
            print(pubmed_id)
            print(title.text)
            paragraph_list = []
            for paragraph in article.findall('./Abstract/AbstractText'):
                p_count += 1
                paragraph_text = "".join(paragraph.itertext())  # AbstractText may have additional nested xml
                if paragraph_text:
                    paragraph_list.append(paragraph_text)

            abstract = ' '.join(paragraph_list)  # concatenate

            if title is not None or len(abstract):  # as long as title or abstract has any text
                text = f'{title.text} {abstract}'  # concatenate
                result.append({
                    'source': 'pubmed',
                    'id': pubmed_id,
                    'text': text,
                })
                logger.debug(f'article #{a_count}: {p_count} paragraphs')
            else:
                logger.error(f'Failed to parse ArticleTitle and AbstractText.')

        logger.debug(f'Fetched {a_count} articles.')
        return result

    # else: no result or failed
    logger.debug('PubMed EFetch request failed.')
    logger.debug(res.text)
    return result
