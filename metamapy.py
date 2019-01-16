import os
import time
import re
import logging
from typing import List
from concurrent.futures import ProcessPoolExecutor

MAX_PROCESSES = 3

# configure logger
logging.basicConfig(format='%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s', level=logging.INFO)
logger = logging.getLogger('MetaMaPY')


def split_into_sentences(text: str) -> List[str]:
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


def remove_non_ascii(s: str) -> str:
    """
    get rid of non-ASCII characters
    :param s: a string to format
    :return: a string of ascii characters only
    """
    return "".join(c for c in s if ord(c) < 128)


def run_command(command_line: str) -> str:
    """
    execute a bash command
    :param command_line: the command to execute
    :return: terminal output
    """
    logger.info(f'executing command: $ {command_line}')
    return os.popen(command_line).read()


def run_metamap(in_file, out_file, configs=('cgab', 'genf', 'lbpr', 'lbtr', 'patf', 'dsyn', 'fndg')):
    """
    run MetaMap
    :param in_file: path to input file
    :param out_file: path to output file
    :param configs: the sts to restrict to, use default in common case
    :return: None
    """
    commands = f"metamap -I -p -N -K -8 --conj -J {','.join(configs)} -R 'HPO' {in_file} {out_file}"
    logger.info(run_command(commands))


def run(text: str):
    start_time = time.time()
    if not os.path.exists('./out'):
        logger.info('creating output folder.')
        os.makedirs('./out')

    # step 1: parse the input text, split them into several files evenly
    logger.info('start pre-parsing.')
    ascii_text = remove_non_ascii(text)
    sentences = split_into_sentences(ascii_text)
    filenames = []
    temp_files = []

    logger.info(f'{MAX_PROCESSES} cores available, {min(len(sentences), MAX_PROCESSES)} used.')
    for i in range(min(len(sentences), MAX_PROCESSES)):  # create a list of temp files
        filenames.append(f'./out/input{i}.tmp')
        temp_files.append(open(filenames[i], 'a'))

    for i, sentence in enumerate(sentences):
        temp_files[i % MAX_PROCESSES].write(sentence)  # write to each temp file in turn

    for file in temp_files:  # close all temp files
        file.write('\n')  # metamap needs a new line at EOF
        file.close()

    logger.info(f'{len(temp_files)} temp files created.')
    pre_parse = time.time()

    # step 2: run metamap on those files using as much processors as possible in parallel
    logger.info('pre-parsing finished, start MetaMap')
    temp_results = []
    with ProcessPoolExecutor(max_workers=MAX_PROCESSES) as pool:
        logger.info(f'dispatching jobs to {MAX_PROCESSES} cores')
        for name in filenames:
            temp_result = f'{name}.res'
            temp_results.append(temp_result)
            pool.submit(run_metamap, name, temp_result)

    metamap_time = time.time()

    # step 3: parse metamap results
    logger.info('MetaMap finished, start parsing result')
    """
    command explanation:
    - select lines starting with <numbers>|MMI|
    - split with | and retrieve column 3,4,5 (score, name, ID)
    - write to file
    """
    _result_filename = './out/result.txt'
    command = f"grep '^\d*|MMI|' ./out/*.res | cut -d '|' -f 3,4,5 > {_result_filename}"
    run_command(command)
    terms = {}
    with open(_result_filename) as res_file:
        for line in res_file:
            score, name, _id = line.strip().split('|')
            if _id in terms.keys():
                terms[_id]['score'] += float(score)    # sum up scores for same id
            else:   # create a new entry
                terms[_id] = {
                    'name': name,
                    'score': float(score),
                }

    logger.info('removing temp files.')
    command = 'rm ./out/*.tmp*'  # remove all tmp files
    run_command(command)
    post_parse = time.time()

    logger.info(f'pre-parse time: {pre_parse - start_time}')
    logger.info(f'metamap time: {metamap_time - pre_parse}')
    logger.info(f'result parse time: {post_parse - metamap_time}')
    logger.info(f'{len(terms.keys())} terms found')
    return terms
