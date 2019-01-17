import logging
from typing import List

logger = logging.getLogger('MetaMaPY')


class QueryCache:
    def __init__(self, max_size: int):
        self.max_size = max_size
        self._cache = {}    # a dict that uses keyword as key and the result list as value
        self._lru = []   # head is LRU(Least Recently Used) and tail is MRU
        logger.info(f'QueryCache created with max_size={self.max_size}')

    def __contains__(self, key: str) -> bool:
        """
        Check if the data has been cached using its key
        :param key: key of the data
        :return: True if it's cached, False otherwise
        """
        return key in self._lru

    def memorize(self, key: str, value: List) -> None:
        """
        Add a key value pair to cache.
        If cache exceeds the size, remove the LRU element
        If it already exists, update the lru
        :param key: the key of the data to cache
        :param value: the value of the data to cache
        """
        if len(self._lru) < self.max_size:   # cache has space
            if key in self:
                self._lru.remove(key)    # remove previous position in LRU cache
                logger.debug(f'updating LRU cache.')
        else:   # cache is full
            logger.debug(f'cache is full.')
            self.forget()
        self._lru.append(key)  # append to tail of LRU
        self._cache[key] = value     # add to cache
        logger.debug(f'{key} cached.')

    def forget(self):
        """
        if cache is not empty, remove LRU element from both lru and cache
        """
        if len(self._lru):
            logger.debug(f'removing LRU element from cache.')
            key = self._lru[0]
            self._lru.remove(key)
            self._cache.pop(key, None)
            logger.debug(f'{key} removed.')

    def get(self, key: str) -> List:
        if key in self:
            # update LRU
            self._lru.remove(key)
            self._lru.append(key)
            logger.debug(f'{key} hits cache.')
        return self._cache.get(key, None)