# -*- coding: utf-8 -*-

from copy import copy
import logging
from fuzzywuzzy import fuzz
import re

MINIMUM_SCORE = 60
OPTIONAL_PREFIX = '?:'
logging.basicConfig(filename='reheader.log',level=logging.DEBUG)



def _normalize_whitespace(s):
    return ' '.join(s.strip().split())


def _compile_regex(raw_regex):
    if raw_regex and not hasattr(raw_regex, 'search'):
        raw_regex = re.compile(raw_regex)
    return raw_regex


def is_empty(row):
    if row:
        try:
            return not any(cell.strip() for cell in row.values())
        except AttributeError:
            try:
                return not any(cell.strip() for cell in row)
            except TypeError:
                return not bool(row)
    return True

def _parse_headers(headers, optional_prefix):
    """
    >>> from pprint import pprint
    >>> headers = _parse_headers(['a', 'b', '?:c'], '?:')
    >>> headers['a']['regex']
    None
    >>> headers['a']['required']
    True
    >>> headers['c']['required']
    False
    """
    try:
        headers = {k: {'regex': _compile_regex(v),
                       'required': True}
                   for (k, v) in headers.items()}
    except AttributeError:
        headers = {k: {'regex': None, 'required': True} for k in headers}
    for k in headers.keys():
        if k.strip().startswith(optional_prefix):
            headers[k]['required'] = False
            new_k = k.strip()[len(optional_prefix):]
            headers[new_k] = headers.pop(k)
    return {_normalize_whitespace(k): headers[k] for k in headers}


def ratio(s1, s2):
    return fuzz.ratio(_normalize_whitespace(s1), _normalize_whitespace(s2))


def header_name_match(actual, expected, minimum_score):
    if expected:
        best = sorted(expected, key=lambda s: ratio(actual, s))[-1]
        score = ratio(actual, best)
        logging.debug('Max score for {} in {} is {}: {}'.format(
            actual, expected, best, score))
        if score >= minimum_score:
            return best
        else:
            logging.debug('Score < {}, not a match'.format(minimum_score))


def best_match(actual, val, expected, minimum_score, prefer_fuzzy):
    logging.debug('Seeking best match for col {}, val {} among {}'.format(actual, val, expected.keys()))
    if prefer_fuzzy:
        logging.debug('Preferential attempt to fuzzy match')
        result = header_name_match(actual, expected, minimum_score)
        if result:
            logging.debug('Preferential fuzzy match succeeded')
            return result
    for col in expected:
        if expected[col]['regex'] and expected[col]['regex'].search(val):
            logging.debug('Successful regex match to {}'.format(val))
            return col
    logging.debug('Final attempt to fuzzy match')
    return header_name_match(actual, expected, minimum_score)

def find_mapping():
    """
    Determine dict relating header in data:user-expected header
    """
    pass


def reheadered(data,
               headers,
               keep_extra=False,
               minimum_score=MINIMUM_SCORE,
               optional_prefix=OPTIONAL_PREFIX,
               prefer_fuzzy=False):
    headers = _parse_headers(headers, optional_prefix)
    headers_in_data = None
    mapping = {}
    for (row_num, row) in enumerate(data):
        if is_empty(row):
            continue
        if not hasattr(row, 'keys'):
            if headers_in_data is None:
                # this was the header line
                headers_in_data = row
                continue
            else:
                row = {r[0]: r[1] for r in zip(headers_in_data, row)}
        if not mapping:
            row_requirements = copy(headers)
            for col in row:
                match = best_match(col, row[col], row_requirements, minimum_score, prefer_fuzzy)
                logging.info('col {} in data matched to {} in expected'.format(col, match))
                if match is not None:
                    row_requirements.pop(match)
                else:
                    if keep_extra:
                        match = col
                if match is not None:
                    mapping[match] = col
            unmet = [h for h in row_requirements
                     if row_requirements[h]['required']]
            if unmet:
                err_msg = '{} not found in row #{}: {}'.format(unmet, row_num, row)
                raise KeyError(err_msg)
        yield {k: row[mapping[k]] for k in mapping}
