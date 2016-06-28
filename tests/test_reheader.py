#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
test_reheader
----------------------------------

Tests for `reheader` module.
"""

import csv
import re
from io import StringIO

import pytest
from reheader import reheadered

_raw_txt_1 = """name,email,zip,
Nellie Newsock,nellie@sox.com,45309,
Charles the Great,big_carl@roi.gouv.fr,12345-1234,
Catherine Devlin,catherine.devlin@gsa.gov,45309,
Grace Hopper,grace@navy.mil,21401,EAFP
Ada Lovelace,ada@maths.uk,,
"""

_raw_txt_2 = """zipcode, Name, e-mail, profession
02139, Margaret Hamilton, mhamilton@nasa.gov, programmer
19803-0000, Stephanie Kwolek, skwolek@dupont.com, chemist
48198, Elijah McCoy, realmccoy@mich-central-rr.com"""


def _data(src=_raw_txt_1, reader=csv.DictReader, with_headers=True):
    for (row_num, row) in enumerate(reader(StringIO(src))):
        if with_headers or (row_num > 0):
            yield row


class TestReheaderedExistence(object):
    @classmethod
    def setup_class(cls):
        pass

    def test_reheadered_exists(self):
        reheadered

    def test_reheadered_accepts_basic_args(self):
        reheadered([{}, ], [])

    @classmethod
    def teardown_class(cls):
        pass


class TestReheaderedFuzzyMatch(object):
    def test_perfect_column_name_match(self):
        for row in reheadered(_data(), ['name', 'email', 'zip']):
            assert 'name' in row
            assert 'email' in row
            assert 'zip' in row

    def test_perfect_column_name_match_list_of_lists(self):
        data = _data(reader=csv.reader, with_headers=True)
        for row in reheadered(data, ['name', 'email', 'zip']):
            assert 'name' in row
            assert 'email' in row
            assert 'zip' in row

    def test_list_of_lists_no_data(self):
        infile = StringIO(_raw_txt_1.splitlines()[0])
        data = csv.reader(infile)
        with pytest.raises(StopIteration):
            reheadered(data, ['name', 'email', 'zip']).__next__()

    def test_list_of_lists_whitespace_before_headers(self):
        src = "\n\n\n\n" + _raw_txt_1
        data = _data(src=src, reader=csv.reader, with_headers=True)
        for row in reheadered(data, ['name', 'email', 'zip']):
            assert 'name' in row
            assert 'email' in row
            assert 'zip' in row

    def test_whitespace_safe_in_expected(self):
        for row in reheadered(_data(), ['       name', 'email', ' zip']):
            assert 'name' in row
            assert 'email' in row
            assert 'zip' in row

    def test_whitespace_safe_in_data(self):
        for row in reheadered(
                _data(_raw_txt_2), ['zipcode', 'Name', 'e-mail'],
                minimum_score=100):
            assert 'zipcode' in row
            assert 'Name' in row
            assert 'e-mail' in row

    def test_fuzzy_column_name_match(self):
        headers = ['Name', 'mail', 'zipcode']
        for row in reheadered(_data(), headers):
            assert 'Name' in row
            assert 'name' not in row

            assert 'mail' in row
            assert row['mail']
            assert 'email' not in row

            assert 'zipcode' in row
            assert 'zip' not in row

    def test_fuzzy_column_name_match_list_of_lists(self):
        data = _data(reader=csv.reader, with_headers=True)
        headers = ['Name', 'mail', 'zipcode']
        for row in reheadered(data, headers):
            assert 'Name' in row
            assert 'name' not in row

            assert 'mail' in row
            assert row['mail']
            assert 'email' not in row

            assert 'zipcode' in row
            assert 'zip' not in row

    def test_fuzzy_column_name_match_failure(self):
        headers = ['Name', 'mail', 'thy one true zip code']
        with pytest.raises(KeyError):
            reheadered(_data(), headers).__next__()

    def test_optional_column_marker_tolerated(self):
        headers = ['Name', '?:mail', 'zip']
        for row in reheadered(_data(), headers):
            assert 'mail' in row
            assert '?:mail' not in row

    def test_optional_column_marker_honored(self):
        headers = ['Name', 'mail', 'zip', '?:nationality']
        for row in reheadered(_data(), headers):
            assert 'mail' in row
            assert 'nationality' not in row

    def test_custom_optional_marker(self):
        headers = ['Name', 'mail', 'zip', 'OPTIONAL~nationality']
        for row in reheadered(_data(), headers, optional_prefix='OPTIONAL~'):
            assert 'mail' in row
            assert 'nationality' not in row


class TestReheaderedRegexMatch(object):
    def setup_method(self, method):
        self.data = _data(reader=csv.reader)

    def test_dict_of_headers_accepted(self):
        headers = {'name': r'(\w+\s+)+', 'email': '\w+@\w+\.\w+'}
        data = _data()
        reheadered(data, headers).__next__()

    def test_list_of_lists_accepted(self):
        headers = {'name': r'(\w+\s+)+', 'email': '\w+@\w+\.\w+'}
        data = _data(reader=csv.reader, with_headers=True)
        reheadered(data, headers).__next__()

    def test_regexes_preferred_to_fuzzy_match(self):
        headers = {'columnA': '\w+@\w+\.\w+', 'columnB': '\d+'}
        for row in reheadered(_data(), headers):
            assert 'columnA' in row
            assert '@' in row['columnA']
            assert 'columnB' in row
            if row['columnB']:
                assert re.search('\d+', row['columnB'])

    def test_mix_regexes_with_column_name_matches(self):
        headers = {'columnA': '\w+@\w+\.\w+', 'zip': None}
        for row in reheadered(_data(), headers):
            assert 'columnA' in row
            assert '@' in row['columnA']
            assert 'zip' in row
            if row['zip']:
                assert re.search('\d+', row['zip'])

    def test_optional_in_regex(self):
        headers = {'zip': '\w+@\w+\.\w+', '?:email': '\d+'}
        for row in reheadered(_data(), headers):
            assert 'zip' in row
            assert '@' in row['zip']
            assert 'email' in row
            if row['email']:
                assert re.search('\d+', row['email'])


class TestOptionalArgs(object):
    def test_keep_extra_false(self):
        for row in reheadered(_data(), ['name', 'email'], keep_extra=False):
            assert 'name' in row
            assert 'email' in row
            assert 'zip' not in row
            assert '' not in row

    def test_keep_extra(self):
        for row in reheadered(_data(), ['name', 'email'], keep_extra=True):
            assert 'name' in row
            assert 'email' in row
            assert 'zip' in row

    def test_keep_extra_with_fuzzy_match(self):
        for row in reheadered(_data(), ['Name', 'e-mail'], keep_extra=True):
            assert 'Name' in row
            assert 'e-mail' in row
            assert 'zip' in row

    def test_low_minimum_score(self):
        headers = ['Name', 'mail', 'zip_code']
        for row in reheadered(_data(), headers, minimum_score=50):
            assert 'zip_code' in row

    def test_high_minimum_score(self):
        headers = ['Name', 'mail', 'zip']
        with pytest.raises(KeyError):
            reheadered(_data(), headers, minimum_score=90).__next__()

    def test_prefer_fuzzy(self):
        headers = {'columnA': '\w+@\w+\.\w+', 'name': '\d+'}
        for row in reheadered(_data(), headers, prefer_fuzzy=True):
            assert 'columnA' in row
            assert '@' in row['columnA']
            assert 'name' in row
            if row['name']:
                assert not re.search('\d+', row['name'])

    def test_header_absent_and_no_regexes(self):
        pass
