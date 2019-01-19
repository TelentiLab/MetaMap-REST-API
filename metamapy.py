import os
import time
import re
import logging
from typing import List, Dict
from concurrent.futures import ProcessPoolExecutor

logger = logging.getLogger('MetaMaPY')


class MetaMaPY:
    _METAMAP_PATH = os.getenv('METAMAP_PATH', 'metamap')
    _PROJECT_PATH = os.getenv('PROJECT_PATH', './')
    logger.debug(f'setting metamap path: {_METAMAP_PATH}')
    logger.debug(f'setting project path: {_PROJECT_PATH}')

    def __init__(self, max_processes: int):
        self.max_processes = max_processes

    @classmethod
    def split_into_sentences(cls, text: str) -> List[str]:
        """
        split the text into a list of sentences
        :param text: text input
        :return: a list of sentences (strings)
        """
        _alphabets = "([A-Za-z])"
        _prefixes = "(Mr|St|Mrs|Ms|Dr)[.]"
        _suffixes = "(Inc|Ltd|Jr|Sr|Co)"
        _starters = "(Mr|Mrs|Ms|Dr|He\s|She\s|It\s|They\s|Their\s|Our\s|We\s|But\s|However\s|That\s|This\s|Wherever)"
        _acronyms = "([A-Z][.][A-Z][.](?:[A-Z][.])?)"
        _websites = "[.](com|net|org|io|gov)"

        text = " " + text + "  "
        text = text.replace("\n", " ")
        text = re.sub(_prefixes, "\\1<prd>", text)
        text = re.sub(_websites, "<prd>\\1", text)
        if "Ph.D" in text:
            text = text.replace("Ph.D.", "Ph<prd>D<prd>")
        text = re.sub("\s" + _alphabets + "[.] ", " \\1<prd> ", text)
        text = re.sub(_acronyms + " " + _starters, "\\1<stop> \\2", text)
        text = re.sub(_alphabets + "[.]" + _alphabets + "[.]" + _alphabets + "[.]", "\\1<prd>\\2<prd>\\3<prd>", text)
        text = re.sub(_alphabets + "[.]" + _alphabets + "[.]", "\\1<prd>\\2<prd>", text)
        text = re.sub(" " + _suffixes + "[.] " + _starters, " \\1<stop> \\2", text)
        text = re.sub(" " + _suffixes + "[.]", " \\1<prd>", text)
        text = re.sub(" " + _alphabets + "[.]", " \\1<prd>", text)
        if "”" in text:
            text = text.replace(".”", "”.")
        if "\"" in text:
            text = text.replace(".\"", "\".")
        if "!" in text:
            text = text.replace("!\"", "\"!")
        if "?" in text:
            text = text.replace("?\"", "\"?")
        text = text.replace(".", ".<stop>")
        text = text.replace("?", "?<stop>")
        text = text.replace("!", "!<stop>")
        text = text.replace("<prd>", ".")
        sentences = text.split("<stop>")
        sentences = sentences[:-1]
        sentences = [s.strip() for s in sentences]
        return sentences

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
        return os.popen(command_line).read()

    @classmethod
    def _run_metamap(cls, in_file, out_file, configs=('cgab', 'genf', 'lbpr', 'lbtr', 'patf', 'dsyn', 'fndg')):
        """
        run MetaMap
        :param in_file: path to input file
        :param out_file: path to output file
        :param configs: the sts to restrict to, use default in common case
        :return: None
        """
        commands = f"{cls._METAMAP_PATH} -I -p -K -8 --conj -J {','.join(configs)} -R 'HPO' {in_file} {out_file}"
        logger.debug(cls._run_command(commands))

    @classmethod
    def _parse_result(cls, result_files: List[str]) -> List[Dict]:
        res = []
        res_dict = {}
        for each in result_files:
            with open(each) as file:
                for line in file:
                    if re.search("^Processing", line) or re.search("^Meta Mapping", line):
                        continue
                    # MetaMap entry found
                    try:
                        cui = re.search("C\d{7}", line).group(0)
                        category = re.search("\[.*\]", line).group(0)[1:-1]
                    except AttributeError:
                        logger.error(f'cannot find cui/category for line: {line}')
                    else:
                        preferred_name = re.search("\(.*\)", line)
                        if preferred_name:
                            name = preferred_name.group(0)[1:-1]  # get rid of the parenthesis
                        else:
                            name = line.split(':', 2)[1].replace(f'[{category}]', '').strip()
                        if cui in res_dict.keys():
                            res_dict[cui]['count'] += 1
                        else:
                            res_dict[cui] = {
                                'term': name,
                                'category': category,
                                'count': 1,
                            }
        for k, v in res_dict.items():
            v['CUI'] = k    # add cui as a key
            res.append(v)
        res.sort(key=lambda x: x['count'], reverse=True)
        logger.debug(f'parsing finished, result: {res}')
        return res

    def run(self, text: str) -> List[Dict]:
        start_time = time.time()
        if not os.path.exists(f'{self._PROJECT_PATH}/out'):
            logger.debug('creating output folder.')
            os.makedirs(f'{self._PROJECT_PATH}/out')

        # step 1: parse the input text, split them into several files evenly
        logger.debug('start pre-parsing.')
        ascii_text = self.remove_non_ascii(text)
        sentences = self.split_into_sentences(ascii_text)
        filenames = []
        temp_files = []

        logger.info(f'{self.max_processes} cores available, {min(len(sentences), self.max_processes)} used.')
        for i in range(min(len(sentences), self.max_processes)):  # create a list of temp files
            filenames.append(f'{self._PROJECT_PATH}/out/input{i}.tmp')
            temp_files.append(open(filenames[i], 'a'))

        for i, sentence in enumerate(sentences):
            temp_files[i % self.max_processes].write(sentence)  # write to each temp file in turn

        for file in temp_files:  # close all temp files
            file.write('\n')  # metamap needs a new line at EOF
            file.close()

        logger.debug(f'{len(temp_files)} temp files created.')
        pre_parse = time.time()

        # step 2: run metamap on those files using as much processors as possible in parallel
        logger.debug('pre-parsing finished, start MetaMap')
        temp_results = []
        with ProcessPoolExecutor(max_workers=self.max_processes) as pool:
            logger.info(f'dispatching jobs to {self.max_processes} cores')
            for name in filenames:
                temp_result = f'{name}.res'
                temp_results.append(temp_result)
                pool.submit(self._run_metamap, name, temp_result)

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
