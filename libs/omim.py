import os
import requests
from typing import Union, Dict
from requests.exceptions import Timeout

from logger import logger


OMIM_URL = 'https://api.omim.org/api/entry/search?search=av_db_snp:{}&include=allelicVariantList&format=json'
_OMIM_API_KEY = os.getenv('OMIM_KEY')
if not _OMIM_API_KEY:
    raise EnvironmentError('Must specify OMIM_KEY in environment.')

try:
    timeout = float(os.getenv('OMIM_TIMEOUT', 3.5))
    logger.info(f'OMIM timeout set to {timeout}')
except TypeError:
    raise EnvironmentError('Expect OMIM_TIMEOUT to evaluate to a number.')

_headers = {
    'apiKey': _OMIM_API_KEY,
}


def get_omim(rsid: str) -> Union[None, Dict]:
    try:
        res = requests.get(OMIM_URL.format(rsid), headers=_headers, timeout=timeout)
    except Timeout:
        logger.error(f'OMIM request timeout. (>{timeout}s)')
        return None
    else:
        if res.status_code == 200:
            logger.debug('OMIM request succeeded.')
            res_json = res.json()
            logger.debug(res_json)
            try:
                allelic_variants = res_json['omim']['searchResponse']['entryList'][0]['entry']['allelicVariantList']
                for each in allelic_variants:
                    variant = each['allelicVariant']
                    if rsid == variant['dbSnps']:
                        return {
                            'source': 'omim',
                            'id': f'{variant["mimNumber"]}#{variant["number"]:04d}',  # format to be 4 digits (e.g 0001)
                            'text': variant['text'],
                        }
            except IndexError or KeyError:
                logger.debug('OMIM no result.')
        else:
            logger.debug('OMIM request failed.')
            logger.debug(res.text)
        return None  # no result or failed
