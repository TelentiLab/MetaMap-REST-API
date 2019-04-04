import os
import time
import re
from utils.logger import logger
from typing import List, Dict
from concurrent.futures import ProcessPoolExecutor


class MetaMaPY:
    _METAMAP_PATH = os.getenv('METAMAP_PATH', 'metamap')
    _PROJECT_PATH = os.getenv('PROJECT_PATH', './')
    _METAMAP_SEM_TYPES = os.getenv('METAMAP_SEM_TYPES', None)
    _METAMAP_DATA_SOURCES = os.getenv('METAMAP_DATA_SOURCES', None)
    logger.debug(f'setting metamap path: {_METAMAP_PATH}')
    logger.debug(f'setting project path: {_PROJECT_PATH}')
    logger.debug(f'configuring metamap sem_types: {_METAMAP_SEM_TYPES}')
    logger.debug(f'configuring metamap data_sources: {_METAMAP_DATA_SOURCES}')

    def __init__(self, max_processes: int):
        self.max_processes = max_processes

    @classmethod
    def remove_non_ascii(cls, s: str) -> str:
        """
        get rid of non-ASCII characters
        :param s: a string to format
        :return: a string of ascii characters only
        """
        return "".join(c for c in s if ord(c) < 128)

    @classmethod
    def _run_command(cls, command_line: str) -> str:
        """
        execute a bash command
        :param command_line: the command to execute
        :return: terminal output
        """
        logger.debug(f'executing command: $ {command_line}')
        output = os.popen(command_line).read()
        if 'command not found' in output:
            logger.error(output)
            raise EnvironmentError(output)
        return output

    @classmethod
    def _start_tagger_server(cls):
        """
        Check if metamap is installed first. Then check if tagger server is running, if not, try starting it.
        :return:
        """
        try:
            cls._run_command(f'{os.path.join(cls._METAMAP_PATH, "metamap")} --help')
        except EnvironmentError:
            logger.error('metamap not installed')
            raise RuntimeError('command metamap is not found, please make sure you have installed metamap.')
        else:
            tagger_processes = cls._run_command(f'ps -ef | grep taggerServer | grep -c -v grep').strip()
            if tagger_processes == '1':
                logger.info('tagger server already started')
            elif tagger_processes == '0':
                logger.info('starting tagger server...')
                output = cls._run_command(f'{os.path.join(cls._METAMAP_PATH, "skrmedpostctl")} start')
                logger.debug(output)
                if 'started' not in output:
                    raise RuntimeError('Failed to start tagger server.')
            else:
                logger.info(f'{tagger_processes} tagger processes found:')
                logger.debug(cls._run_command(f'ps -ef | grep taggerServer | grep -v grep'))
                raise RuntimeError('An unknown error has occurred while starting metamap tagger server.')

    @classmethod
    def _run_metamap(cls, in_file: str, out_file: str, sem_types: List[str] = None,
                     data_sources: List[str] = None) -> None:
        """
        run MetaMap with given options.

        :param in_file: path to input file
        :param out_file: path to output file
        :param sem_types: the semantic types to restrict to, use default in common case
        :param data_sources: the sources to restrict to, use default in common case
        :return: None
        """
        options = ''
        if sem_types:
            options = f" -J {','.join(sem_types)}"
        if data_sources:
            options = f"{options} -R {','.join(data_sources)}"

        commands = f"{os.path.join(cls._METAMAP_PATH, 'metamap')} -I -p -K -8 --silent --conj{options} {in_file} {out_file}"
        cls._run_command(commands)
        logger.debug('a metamap process has finished.')

    @classmethod
    def _parse_result(cls, result_files: List[str]) -> List[Dict]:
        res = []
        res_dict = {}
        for each in result_files:   # each format: path/to/project/out/input_source_id.temp.res
            source_name, source_id = os.path.basename(each).split('.')[0].split('_')[-2:]
            with open(each) as file:
                for line in file:
                    if re.search("^Processing", line) or re.search("^Meta Mapping", line):
                        continue    # skip unrelated lines

                    try:    # MetaMap entry found
                        cui = re.search(r"C\d{7}", line).group(0)
                        category = re.search(r"\[.*\]", line).group(0)[1:-1]
                    except AttributeError:
                        logger.error(f'cannot find cui/category for line: {line}')
                    else:
                        # retrieve term name
                        preferred_name = re.search(r"\(.*\)", line)
                        if preferred_name:
                            name = preferred_name.group(0)[1:-1]  # get rid of the parenthesis
                        else:
                            name = line.split(':', 2)[1].replace(f'[{category}]', '').strip()

                        # check if it's a new term or a found term
                        if cui in res_dict.keys():
                            res_dict[cui]['count'] += 1
                        else:
                            res_dict[cui] = {
                                'term': name,
                                'category': category,
                                'count': 1,
                                'sources': {}
                            }

                        # update the source info
                        if source_name not in res_dict[cui]['sources'].keys():
                            res_dict[cui]['sources'][source_name] = []
                        if source_id not in res_dict[cui]['sources'][source_name]:
                            res_dict[cui]['sources'][source_name].append(source_id)
        for k, v in res_dict.items():
            v['CUI'] = k    # add cui as a key
            res.append(v)
        res.sort(key=lambda x: x['count'], reverse=True)
        logger.debug(f'parsing finished, result: {res}')
        return res

    def run(self, articles: List[Dict]) -> List[Dict]:
        self._start_tagger_server()
        logger.debug(f'running metamap on input text: {articles}')
        start_time = time.time()
        if not os.path.exists(f'{self._PROJECT_PATH}/out'):
            logger.debug('creating output folder.')
            os.makedirs(f'{self._PROJECT_PATH}/out')

        # step 1: write each article to a separate file
        logger.debug('start pre-parsing.')
        filenames = []
        for article in articles:
            ascii_text = self.remove_non_ascii(article['text'])
            filename = f'{self._PROJECT_PATH}/out/input_{article["source"]}_{article["id"]}.tmp'
            filenames.append(filename)
            with open(filename, 'w') as file:   # create a list of temp files
                file.write(ascii_text)
                file.write('\n')  # metamap needs a new line at EOF

        logger.debug(f'{len(filenames)} temp files created.')
        pre_parse = time.time()

        # step 2: run metamap on those files using as much processors as possible in parallel
        logger.debug('pre-parsing finished, start MetaMap')
        temp_results = []
        with ProcessPoolExecutor(max_workers=self.max_processes) as pool:
            logger.info(f'dispatching jobs to {self.max_processes} cores')
            sem_types = self._METAMAP_SEM_TYPES.split(',') if self._METAMAP_SEM_TYPES else None
            data_sources = self._METAMAP_DATA_SOURCES.split(',') if self._METAMAP_DATA_SOURCES else None
            for name in filenames:
                temp_result = f'{name}.res'
                temp_results.append(temp_result)
                pool.submit(self._run_metamap, name, temp_result, sem_types, data_sources)

        metamap_time = time.time()

        # step 3: parse metamap results
        logger.debug('MetaMap finished, start parsing result')
        terms = self._parse_result(temp_results)
        logger.debug('removing temp files.')
        command = f'rm {self._PROJECT_PATH}/out/*.tmp*'  # remove all tmp files
        self._run_command(command)
        post_parse = time.time()

        logger.info(f'pre-parse time: {pre_parse - start_time}')
        logger.info(f'metamap time: {metamap_time - pre_parse}')
        logger.info(f'result parse time: {post_parse - metamap_time}')
        logger.info(f'total time: {post_parse - start_time}')
        logger.info(f'{len(terms)} terms found')
        return terms
