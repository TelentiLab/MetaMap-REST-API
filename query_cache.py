from typing import List, Union
from logger import logger
import os


class QueryCache:
    """
    MRU cache using singleton constructor
    """
    class __QueryCache:
        def __init__(self):
            _cache_size = int(os.getenv('CACHE_SIZE', 30))
            logger.info(f'CACHE_SIZE={_cache_size}')
            self.max_size = _cache_size
            self._cache = {}  # a dict that uses RSID as key and the result list as value
            self._mru = []  # head is LRU(Least Recently Used) and tail is MRU
            logger.info(f'QueryCache created with max_size={self.max_size}')

    instance = None

    def __init__(self):
        if not self.instance:
            self.instance = self.__QueryCache()
        else:
            logger.debug(f'Using QueryCache singleton with max_size={self.max_size}')

    def __getattr__(self, name):
        return getattr(self.instance, name)

    def __contains__(self, key: str) -> bool:
        """
        Check if the data has been cached using its key
        :param key: key of the data
        :return: True if it's cached, False otherwise
        """
        return key in self._mru

    def memorize(self, key: str, value: List) -> None:
        """
        Add a key value pair to cache.
        If cache exceeds the size, remove the LRU element
        If it already exists, update the _mru
        :param key: the key of the data to cache
        :param value: the value of the data to cache
        """
        if len(self._mru) < self.max_size:   # cache has space
            if key in self:
                self._mru.remove(key)    # remove previous position in MRU cache
                logger.debug(f'updating MRU cache.')
        else:   # cache is full
            logger.debug(f'cache is full.')
            self._forget()
        self._mru.append(key)  # append to tail of MRU
        self._cache[key] = value     # add to cache
        logger.debug(f'{key} cached.')

    def _forget(self):
        """
        if _cache is not empty, remove LRU element from both _mru and _cache
        """
        if len(self._mru):
            logger.debug(f'removing LRU element from cache.')
            key = self._mru[0]
            self._mru.remove(key)
            self._cache.pop(key, None)
            logger.debug(f'{key} removed from cache.')

    def get(self, key: str) -> Union[List, None]:
        """
        If the key has been cached, return the value and update MRU. If not, return None and do nothing else.
        :param key:
        :return:
        """
        if key in self:
            # update LRU
            self._mru.remove(key)
            self._mru.append(key)
            logger.debug(f'{key} hits cache.')
        return self._cache.get(key, None)
