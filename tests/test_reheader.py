#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
test_reheader
----------------------------------

Tests for `reheader` module.
"""

import pytest
import csv
from io import StringIO

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
    for row in reader(StringIO(src)):
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
            assert '' in row

    def test_keep_extra_with_fuzzy_match(self):
        for row in reheadered(_data(), ['Name', 'e-mail'], keep_extra=True):
            assert 'Name' in row
            assert 'e-mail' in row
            assert 'zip' in row
            assert '' in row

    def test_low_minimum_score(self):
        headers = ['Name', 'mail', 'zip_code']
        for row in reheadered(_data(), headers, minimum_score=50):
            assert 'zip_code' in row

    def test_high_minimum_score(self):
        headers = ['Name', 'mail', 'zip']
        with pytest.raises(KeyError):
            reheadered(_data(), headers, minimum_score=90).__next__()
