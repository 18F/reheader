# -*- coding: utf-8 -*-

import csv
from copy import copy

import pytest
from fuzzywuzzy import fuzz

_MINIMUM_SCORE = 60


def fuzzy_map(short_list, long_list, minimum_score=_MINIMUM_SCORE):
    result = {}
    for key in short_list:
        match = sorted(long_list, key=lambda s: fuzz.ratio(key, s))[-1]
        if fuzz.ratio(key, match) < minimum_score:
            raise KeyError('Could not find score {} match for {} in {}'.format(
                minimum_score, key, long_list))
        result[key] = match
        long_list.remove(match)
    return result


class DictReader(csv.DictReader):
    def find_in_columns(self, desired_name, pattern, columns):
        for (index, column) in enumerate(columns):
            if not column['used']:
                if pattern.search(column['first_value']):
                    column['used'] = 'True'
                    column['new_fieldname'] = desired_name
                    return
        raise IndexError('Could not find {} in {}'.format(pattern, columns))

    def assigned_fieldnames(self, desired):
        columns = [{'first_value': f,
                    'used': False,
                    'new_fieldname': None} for f in self.fieldnames]
        for (name, pattern) in desired.items():
            try:
                self.find_in_columns(name, pattern, columns)
            except AttributeError:
                return None
        return [c['new_fieldname'] for c in columns]

    def __init__(self, csvfile, fieldnames=None, *arg, **kwarg):
        result = super(DictReader, self).__init__(csvfile, *arg, **kwarg)
        if self.fieldnames:
            if fieldnames:
                if hasattr(fieldnames, 'items'):  # dict or dict-like
                    new_fieldnames = self.assigned_fieldnames(fieldnames)
                    if new_fieldnames:
                        self.mapping = {k: k for k in fieldnames}
                        result = super(DictReader, self).__init__(
                            csvfile,
                            fieldnames=new_fieldnames,
                            *arg,
                            **kwarg)
                    else:
                        self.mapping = fieldnames
                else:
                    # fieldnames supplied as list
                    self.mapping = fuzzy_map(fieldnames, copy(self.fieldnames))
            else:
                self.mapping = {h: h for h in self.fieldnames}
            self.schema = [k for k in self.fieldnames if k]
        return result

    def __next__(self, *arg, **kwarg):
        raw_next = super(DictReader, self).__next__(*arg, **kwarg)
        result = {k: raw_next[v] for (k, v) in self.mapping.items()}
        return result

    def find_mapping(self, fieldnames, first_row):
        return {f: f for f in fieldnames}
