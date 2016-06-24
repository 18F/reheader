===============================
fuzzycsv
===============================


.. image:: https://img.shields.io/pypi/v/fuzzycsv.svg
        :target: https://pypi.python.org/pypi/fuzzycsv

.. image:: https://img.shields.io/travis/18f/fuzzycsv.svg
        :target: https://travis-ci.org/18f/fuzzycsv

.. image:: https://pyup.io/repos/github/18f/cookiecutter-django/shield.svg
     :target: https://pyup.io/repos/github/18f/fuzzycsv/
     :alt: Updates

Supplies a ``DictReader`` class - subclassed from ``csv.DictReader`` -
for tabular data with inconsistent or absent table headings.

License
-------

This project is in the public domain within the United States,
and we waive worldwide copyright and related rights through
CC0 universal public domain dedication.

Usage
-----

::

  from fuzzycsv import DictReader

Pass *desired* ``fieldnames``, and ``fuzzycsv.DictReader`` will find
an approximate match from the actual column headings::

  $ cat people.csv
  name,email,zip,
  Nellie Newsock,nellie@sox.com,45309,
  Charles the Great,big_carl@roi.gouv.fr,12345-1234,

  >>> from fuzzycsv import DictReader
  >>> with open('people.csv') as infile:
  ...     reader = DictReader(infile, fieldnames=['mail', 'zipcode'])
  ...     for row in reader:
  ...         print(row)
  ...
  {'mail': 'nellie@sox.com', 'zipcode': '45309'}
  {'mail': 'big_carl@roi.gouv.fr', 'zipcode': '12345-1234'}

The optional ``minimum_score`` parameter (0 - 100, default 60) determines how
precisely the expected and actual headers must match.

Pass a dict to explicitly match desired to actual column names:

  fieldnames = {
      'mail': 'email',
      'postal_code': 'zip',
  }
  DictReader(infile, fieldnames=fieldnames)

Or pass *compiled* regexes to recognize columns by their *values*::

  fieldnames = {
      'email': re.compile(r'\w+@\w+\.\w+'),
      'zip': re.compile(r'\d{5}(\-?\d{4})?')
  }
  DictReader(infile, fieldnames=fieldnames)

Each returned reader includes a `schema`, which can be passed to subsequent
readers to coerce multiple sources into a consistent data set::

  reader1 = DictReader(infile)
  reader2 = DictReader(infile2, fieldnames=reader1.schema)
  alldata = list(reader1) + list(reader2)

Ambitions
---------

- Match columns by example, not regex
- Handle synonyms (like "zip" to "postal code")

Credits
---------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
