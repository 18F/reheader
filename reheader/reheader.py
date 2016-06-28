# -*- coding: utf-8 -*-

import logging
import re

from fuzzywuzzy import fuzz

MINIMUM_SCORE = 60
OPTIONAL_PREFIX = '?:'
logging.basicConfig(filename='reheader.log', level=logging.DEBUG)


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


def _parse_expected_headers(headers, optional_prefix):
    """
    >>> from pprint import pprint
    >>> headers = _parse_expected_headers(['a', 'b', '?:c'], '?:')
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


def _similarity(s1, s2):
    return fuzz.ratio(_normalize_whitespace(s1), _normalize_whitespace(s2))


def _map_by_fuzzy_header_name(actual, val, expected, minimum_score):
    if expected:
        best = sorted(expected, key=lambda s: _similarity(actual, s))[-1]
        score = _similarity(actual, best)
        logging.debug('Max score for {} in {} is {}: {}'.format(
            actual, expected, best, score))
        if score >= minimum_score:
            return best
        else:
            logging.debug('Score < {}, not a match'.format(minimum_score))


def _map_by_regex(actual, val, expected, minimum_score):
    for col in expected:
        if expected[col]['regex'] and expected[col]['regex'].search(val):
            logging.debug('Successful regex match to {}'.format(val))
            return col


def _map_unchanged(actual, val, expected, minimum_score):
    return actual


def _find_mapping(row, expected, minimum_score, prefer_fuzzy, keep_extra):
    """
    Determine dict relating header_in_data:user_expected_header
    """
    mappers = [_map_by_regex, _map_by_fuzzy_header_name]
    if prefer_fuzzy:
        mappers.reverse()
    if keep_extra:
        mappers.append(_map_unchanged)
    mapping = {}
    for mapper in mappers:
        for col in row:
            if not mapping.get(col):
                mapping[col] = mapper(col, row[col], expected, minimum_score)
                if mapping[col]:
                    expected.pop(mapping[col], None)
    unmet = [h for h in expected if expected[h]['required']]
    if unmet:
        err_msg = '{} not found in {}'.format(unmet, row)
        raise KeyError(err_msg)
    return {mapping[k]: k for k in mapping if mapping[k]}


def reheadered(data,
               expected_headers,
               keep_extra=False,
               minimum_score=MINIMUM_SCORE,
               optional_prefix=OPTIONAL_PREFIX,
               prefer_fuzzy=False):
    expected = _parse_expected_headers(expected_headers, optional_prefix)
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
            mapping = _find_mapping(row=row,
                                    expected=expected,
                                    minimum_score=minimum_score,
                                    prefer_fuzzy=prefer_fuzzy,
                                    keep_extra=keep_extra)
        yield {k: row[mapping[k]] for k in mapping}
