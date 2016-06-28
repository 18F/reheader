# -*- coding: utf-8 -*-

import itertools
import logging
import re
import string

from fuzzywuzzy import fuzz

MINIMUM_SCORE = 60
OPTIONAL_PREFIX = '?:'
logging.basicConfig(filename='reheader.log', level=logging.DEBUG)


def reheadered(data,
               desired_headers,
               keep_extra=False,
               minimum_score=MINIMUM_SCORE,
               optional_prefix=OPTIONAL_PREFIX,
               prefer_fuzzy=False,
               header_present=None):
    """Re-emit a data stream with headers altered to `desired_headers`.

    Args:
        data (iterator): The series of dicts or lists to re-emit.
        desired_headers (dict or list): Dict of
            {<desired column name>:<regex>},
            or list of [<desired column name>,]
        minimum_score (int): 0-100, what Levenshtein ratio a header in the data
            needs to be matched to a desired column name.  Default 60.
        optional_prefix (str): Desired column name beginning with this will be
            considered optional.  Default is ``?:``
        prefer_fuzzy (bool): Even if a regex is present, try first to match
            desired to data by header similarity.  Default ``False``.
        header_present (*): When ``data`` is a series of lists, whether the
            first data row is headers.

    Returns:
        iterator of dicts with altered keys.
    """

    expected = _parse_desired_headers(desired_headers, optional_prefix)
    any_regexes = any(h['regex'] for h in expected.values())
    (header_present, data) = _headers_present(header_present, data,
                                              any_regexes)
    headers_in_data = None
    mapping = {}
    for row in data:
        if is_empty(row):
            continue
        if not hasattr(row, 'keys'):
            if headers_in_data is None:
                if header_present:
                    headers_in_data = row
                    continue
                else:
                    headers_in_data = ['column_{}'.format(n)
                                       for n in range(len(row))]
            row = {r[0]: r[1] for r in zip(headers_in_data, row)}
        if not mapping:
            mapping = _find_mapping(row=row,
                                    expected=expected,
                                    minimum_score=minimum_score,
                                    prefer_fuzzy=prefer_fuzzy,
                                    keep_extra=keep_extra)
        yield {k: row[mapping[k]] for k in mapping}


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


def _parse_desired_headers(headers, optional_prefix):
    """
    >>> from pprint import pprint
    >>> headers = _parse_desired_headers(['a', 'b', '?:c'], '?:')
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


_roughen_in = string.ascii_lowercase + string.ascii_uppercase + string.digits
_roughen_out = 'a' * 26 + 'A' * 26 + '9' * 10
_roughen_table = str.maketrans(_roughen_in, _roughen_out)


def _roughen_string(orig):
    """A 'high-level' view of a string

    >>> _roughen_string("Barbara McClintock, 1902-1992")
    'Aaaaaaa AaAaaaaaaa, 9999-9999'
    """
    result = ' '.join(orig.split())
    return str.translate(result, _roughen_table)


def _row_similarity(row1, row2):
    similarities = []
    for (val1, val2) in zip(row1, row2):
        if val1.strip() and val2.strip():
            similarities.append(fuzz.ratio(val1, val2))
    return sum(similarities) / len(similarities)


def _nonempty_row_slice(data, size=10):
    captured_rows = []
    nonempty_rows = []
    rows_found = 0
    for row in data:
        captured_rows.append(row)
        if not is_empty(row):
            nonempty_rows.append(row)
            rows_found += 1
        if rows_found >= size:
            break
    # Put examined rows back
    data = itertools.chain(captured_rows, data)
    return (nonempty_rows, data)


def _big_difference_first_to_second_row(rows):
    """
    Looks for a "large difference" between the first row in data and later rows
    """
    if len(rows) < 2:
        return False
    header_similarity = _row_similarity(*rows[0:2])
    general_similarities = []
    for row_num in range(1, len(rows) - 1):
        general_similarities.append(_row_similarity(*rows[row_num:row_num +
                                                          2]))
    average_similarity = sum(general_similarities) / len(general_similarities)
    return header_similarity < average_similarity - 10


def _headers_present(header_present, data, any_regexes):
    if header_present in (True, False):
        return (header_present, data)
    try:
        return (int(header_present), data)
    except (TypeError, ValueError):
        (rows, data) = _nonempty_row_slice(data)
        if len(rows) == 0:
            return (False, data)
        if hasattr(rows[0], 'keys'):
            return (False, data)
        if len(rows) == 1:
            if any_regexes:
                return (False, data)
            else:
                return (True, data)
        if len(rows) == 2:
            return (_row_similarity(*rows) < 0.2, data)
        header_present = _big_difference_first_to_second_row(rows)
        return (header_present, data)
