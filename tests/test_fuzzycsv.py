#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
test_fuzzycsv
----------------------------------

Tests for `fuzzycsv` module.
"""

import io
import re

import fuzzycsv
import pytest


class TestReadWithHeaders(object):

    _raw_txt = """name,email,zip,
    Nellie Newsock,nellie@sox.com,45309,
    Charles the Great,big_carl@roi.gouv.fr,12345-1234,
    Catherine Devlin,catherine.devlin@gsa.gov,45309,
    Grace Hopper,grace@navy.mil,21401,EAFP
    Ada Lovelace,ada@maths.uk,,
    """

    _raw_txt2 = """zipcode, Name, e-mail, profession
    02139, Margaret Hamilton, mhamilton@nasa.gov, programmer
    19803-0000, Stephanie Kwolek, skwolek@dupont.com, chemist
    48198, Elijah McCoy, realmccoy@mich-central-rr.com"""

    @classmethod
    def setup_class(cls):
        pass

    def setup_method(self, method):
        self.file = io.StringIO(self._raw_txt)

    def test_DictReader_exists(self):
        fuzzycsv.DictReader

    def test_no_fieldnames(self):
        reader = fuzzycsv.DictReader(self.file, )
        for row in reader:
            assert 'name' in row
            assert 'email' in row
            assert 'zip' in row

    def test_perfect_column_name_match(self):
        reader = fuzzycsv.DictReader(self.file,
                                     fieldnames=['name', 'email', 'zip'])
        for row in reader:
            assert 'name' in row
            assert 'email' in row
            assert 'zip' in row

    def test_empty_file_is_empty(self):
        reader = fuzzycsv.DictReader(
            io.StringIO(''),
            fieldnames=['name', 'email', 'zip'])
        assert len(list(reader)) == 0

    def test_discard_unwanted_column_name(self):
        reader = fuzzycsv.DictReader(self.file, fieldnames=['email', 'zip'])
        # verify it does produce rows
        assert reader.__next__()
        for row in reader:
            assert 'name' not in row
            assert 'email' in row
            assert 'zip' in row

    def test_near_perfect_column_name_match(self):
        reader = fuzzycsv.DictReader(self.file,
                                     fieldnames=['mail', 'zip', 'name'])
        assert reader.__next__()
        for row in reader:
            if row['mail']:
                assert ' ' in row['name']
                assert '@' in row['mail']

    def test_near_perfect_column_names_but_perfection_demanded(self):
        with pytest.raises(KeyError):
            reader = fuzzycsv.DictReader(self.file,
                                         fieldnames=['mail', 'zip', 'name'],
                                         minimum_score=100)

    def test_fieldnames_as_string_to_string_dict(self):
        fieldnames = {'mail': 'email', 'postal_code': 'zip'}
        reader = fuzzycsv.DictReader(self.file, fieldnames=fieldnames)
        assert reader.__next__()
        for row in reader:
            assert 'mail' in row
            assert 'postal_code' in row

    def test_field_names_in_reader_schema(self):
        reader = fuzzycsv.DictReader(self.file, )
        assert hasattr(reader, 'schema')
        assert isinstance(reader.schema, list)

    def test_user_past_schema_as_fieldnames(self):
        reader1 = fuzzycsv.DictReader(self.file, )
        file2 = io.StringIO(self._raw_txt2)
        reader2 = fuzzycsv.DictReader(file2, fieldnames=reader1.schema)
        assert reader2.__next__()
        for row in reader2:
            assert 'email' in row
            assert '@' in row['email']
            assert 'zip' in row
            assert 'name' in row

    @classmethod
    def teardown_class(cls):
        pass

    def teardown_method(self, method):
        self.file.close()


class TestReadWithoutHeaders(object):

    _raw_txt = """Nellie Newsock,nellie@sox.com,45309,
    Charles the Great,big_carl@roi.gouv.fr,12345-1234,
    Catherine Devlin,catherine.devlin@gsa.gov,45309,
    Grace Hopper,grace@navy.mil,21401,EAFP
    Ada Lovelace,ada@maths.uk,,
    """

    _raw_txt2 = """02139, Margaret Hamilton, mhamilton@nasa.gov, programmer
    19803-0000, Stephanie Kwolek, skwolek@dupont.com, chemist
    48198, Elijah McCoy, realmccoy@mich-central-rr.com"""

    @classmethod
    def setup_class(cls):
        pass

    def setup_method(self, method):
        self.file = io.StringIO(self._raw_txt)

    def test_DictReader_exists(self):
        fuzzycsv.DictReader

    def test_fieldnames_as_regex(self):
        fieldnames = {'email': re.compile(r'\w+@\w+\.\w+'),
                      'zip': re.compile(r'\d+(\-?\d+)?'),
                      'name': re.compile(r'^\s*[A-Z][a-z]+'), }
        reader = fuzzycsv.DictReader(self.file, fieldnames=fieldnames)
        assert reader.__next__()
        for row in reader:
            assert 'email' in row
            if row['email']:
                for column_name in fieldnames:
                    assert column_name in row
                    val = row[column_name]
                    assert (not val) or fieldnames[column_name].search(val)

    def test_fieldnames_with_bad_regex(self):
        fieldnames = {'email': re.compile(r'\w+@ OOPS \w+\.\w+'),
                      'zip': re.compile(r'\d+(\-?\d+)?'),
                      'name': re.compile(r'^\s*[A-Z][a-z]+'), }
        with pytest.raises(IndexError):
            reader = fuzzycsv.DictReader(self.file, fieldnames=fieldnames)

    @classmethod
    def teardown_class(cls):
        pass

    def teardown_method(self, method):
        self.file.close()
