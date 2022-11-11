#!/usr/bin/env python

"""Tests for pandoc-xref-native."""

import unittest
import json
import subprocess
import re

from pandocfilters import Header, Math, Image, walk

from pandoc_xref_native import section_ids, equation_ids, figure_ids, \
                               table_ids, pandoc, sec_id, eq_id, fig_id, \
                               tab_id, collect_ids, check_id_uniqueness, \
                               pluralize, CrossRef, new_sentence, \
                               resolve_crossrefs

# -----------------------------------------------------------------------------
# Utility functions -----------------------------------------------------------
# -----------------------------------------------------------------------------

def mock_attr(_id):
    """Create a 'mock attribute' for creation of various AST elements."""
    return [_id, [], []]


def reset_idlists():
    """Empty id lists imported from module `pandoc_xref_native`."""
    section_ids[:] = []
    equation_ids[:] = []
    figure_ids[:] = []
    table_ids[:] = []


def depandoc(doc):
    """Turn Pandoc AST back into Pandoc's Markdown.

    Does the opposite of what `pandoc-xref-native`'s function `pandoc` does.
    """
    doc_json = json.dumps(doc)
    cmd = ['pandoc', '-f', 'json', '-t', 'markdown']
    output = subprocess.check_output(cmd, input=doc_json, text=True)
    return output


class TestUtils(unittest.TestCase):
    """Test this module's utility functions."""

    def test_depandoc(self):
        """Test depandoc."""
        pdc = ("A paragraph with some math: $E=mc^2$.\n")
        doc = pandoc(pdc, para=False)
        pdc2 = depandoc(doc)
        self.assertEqual(pdc2, pdc)


# -----------------------------------------------------------------------------
# Test class for pandoc-xref-native -------------------------------------------
# -----------------------------------------------------------------------------

class TestPandocXrefNative(unittest.TestCase):
    """Tests for pandoc-xref-native."""

    # pylint: disable=missing-function-docstring
    # It is fairly obvious what the tests do.

    # Test utility items ------------------------------------------------------

    def test_pandoc(self):
        res = pandoc('A test.')
        self.assertEqual(res,
          [{'t': 'Str', 'c': 'A'}, {'t': 'Space'}, {'t': 'Str', 'c': 'test.'}])


    # Tests for collecting IDs from document ----------------------------------

    def test_sec_id(self):
        _id = 'sec1'
        returned_id = sec_id(Header(1, mock_attr(_id), 'A heading!')['c'])
        self.assertEqual(_id, returned_id)


    def test_eq_id(self):
        _id = 'eq:einstein'
        equation = f'\nE=mc^2\n\\label{{{ _id }}}\n'
        returned_id = eq_id(Math({'t': 'DisplayMath'}, equation)['c'])
        self.assertEqual(_id, returned_id)

        self.assertEqual(None, eq_id(Math({'t': 'InlineMath'}, equation)['c']))


    def test_fig_id(self):
        _id = 'fig:fig1'

        returned_id = fig_id(Image(mock_attr(_id), None, [None, 'fig:title'])
                                                                         ['c'])
        self.assertEqual(_id, returned_id)

        returned_id = fig_id(Image(mock_attr(_id), None, [None, 'title'])['c'])
        self.assertIsNone(returned_id)


    def test_tab_id(self):
        _id = 'tab:tab1'
        returned_id = tab_id([mock_attr(_id), None, None, None, None, None])
        self.assertEqual(_id, returned_id)


    def test_collect_ids(self):
        reset_idlists()
        pdc = ("# Header {#sec1}\n"
               "\n"
               "A display equation:\n"
               "$$\n"
               "E=mc^2\n"
               "\\label{eq:einstein}\n"
               "$$\n"
               "\n"
               "![Figure caption](einstein.jpg){#fig1}")
        doc = pandoc(pdc, para=False)
        walk(doc, collect_ids, None, None)
        self.assertEqual(section_ids, ['sec1'])
        self.assertEqual(equation_ids, ['eq:einstein'])
        self.assertEqual(figure_ids, ['fig1'])


    def test_check_id_uniqueness(self):
        reset_idlists()
        section_ids[:] = ['killer_bunny', 'brian', 'brian', 'shrubbery']
        figure_ids[:] = ['brian', 'balloon', 'ex-parrot']
        table_ids[:] = ['balloon', 'airship']
        check_id_uniqueness()
        self.assertEqual(section_ids, ['killer_bunny', 'shrubbery'])
        self.assertEqual(figure_ids, ['ex-parrot'])
        self.assertEqual(table_ids, ['airship'])


    # Tests for resolving cross-references ------------------------------------

    def test_pluralize(self):
        self.assertEqual(pluralize('fig.'), 'figs.')
        self.assertEqual(pluralize('figure'), 'figures')
        self.assertEqual(pluralize('Figure'), 'Figures')
        self.assertEqual(pluralize('Table'), 'Tables')


    def test_crossref_re(self):
        regex = CrossRef.re

        match = re.match(regex, '@#id')
        self.assertEqual(match.group('id'), 'id')

        match = re.match(regex, '-@#id')
        self.assertEqual(match.group('prefix_suppressor'), '-')

        match = re.match(regex, '[@#id')
        self.assertEqual(match.group('opening_bracket'), '[')

        match = re.match(regex, '@#id]')
        self.assertEqual(match.group('closing_bracket'), ']')

        match = re.match(regex, '@#id].')
        self.assertEqual(match.group('punctuation'), '.')

        # Non-breaking space after known abbreviation.
        match = re.match(regex, 'e.g.\xa0@#id')
        self.assertEqual(match.group('known_abbreviation'), 'e.g.\xa0')

        match = re.match(regex, '@#part1.part2.')
        self.assertEqual(match.group('id'), 'part1.part2')
        self.assertEqual(match.group('punctuation'), '.')

        match = re.match(regex, '@#part1.part2]')
        self.assertEqual(match.group('id'), 'part1.part2')
        self.assertEqual(match.group('closing_bracket'), ']')

        match = re.match(regex, '@#part1.part2].')
        self.assertEqual(match.group('id'), 'part1.part2')
        self.assertEqual(match.group('closing_bracket'), ']')
        self.assertEqual(match.group('punctuation'), '.')


    def test_crossref_check(self):
        reset_idlists()
        section_ids[:] = ['id']
        table_ids[:] = ['tab:id']
        tests = [('-[@#id.', False),
                 ('[@#id].', False),
                 ('@#id', True),
                 ('-@#id', True),
                 ('[@#id', True),
                 # CrossRef remembers the previous opening bracket
                 ('[@#id', False),
                 ('@#id].', True),
                 ('[@#id', True),
                 ('@#tab:id]', False), # bracketed ids must be of same type
                 ('@#unknown_id', False)]
        for cross_ref_str, valid in tests:
            cross_ref = CrossRef.match(cross_ref_str)
            validity = { True: 'valid', False: 'invalid' }
            self.assertEqual(cross_ref.valid, valid,
                msg=(f'Expected cross-reference "{cross_ref_str}" to be '
                     f'{validity[valid]}, but it turned out to be '
                     f'{validity[cross_ref.valid]}! '
                     f'`CrossRef.inside_brackets` is '
                     f'{str(CrossRef.inside_brackets)}.') )


    def test_new_sentence(self):
        tests = [('A test. @#id.', True),
                 ('Also @#id', False),
                 ('A test! @#id.', True),
                 ('A test: @#id.', True),
                 ('A test? @#id.', True)]
        for string, expected_result in tests:
            elts = pandoc(string)
            result = new_sentence(elts[:-1])
            sentences = { True: 'a new sentence', False: 'no new sentence' }
            self.assertEqual(bool(result), expected_result,
                msg=(f'Cross-reference in `{string}` starts '
                     f'{sentences[expected_result]}, but function '
                      '"new_sentence" says otherwise!') )


    def test_resolve_crossrefs(self):
        reset_idlists()
        CrossRef.reset_bracket_states()
        equation_ids[:] = ['eq1']
        figure_ids[:] = ['fig1', 'fig2']
        tests = [
         ['See @#fig1.',
          'See `<a href=#fig1 class="cross-ref">figure </a>`{=html}.'],

         ['See [@#fig1 and @#fig2].',
          ('See `figures <a href=#fig1 class="cross-ref"></a>`{=html} and '
           '`<a href=#fig2 class="cross-ref"></a>`{=html}.')],

         # Known abbreviation preceding cross-reference.
         ['See e.g. @#fig1.',
          'See e.g. `<a href=#fig1 class="cross-ref">figure </a>`{=html}.'],

         # Known abbreviation preceding cross-reference at the start of a
         # sentence.
         ['Fig. -@#fig1.',
          'Fig. `<a href=#fig1 class="cross-ref"></a>`{=html}.'],

         # Cross-references in brackets not of the same type!
         ['See [@#fig1 and @#eq1].',
          ('See `figures <a href=#fig1 class="cross-ref"></a>`{=html} '
           'and @#eq1].')],

         ['@#fig1 shows...',
          '`<a href=#fig1 class="cross-ref">Figure </a>`{=html} shows...'],
        ]
        for pdc, exp_pdc in tests:
            doc = pandoc(pdc, para=False)
            new_doc = walk(doc, resolve_crossrefs, None, None)
            exp_doc = pandoc(exp_pdc, para=False)
            # Using depandoc instead of the AST versions improves readability
            # greatly if the test fails.
            self.assertEqual(depandoc(new_doc), depandoc(exp_doc))


# -----------------------------------------------------------------------------
# Main ------------------------------------------------------------------------
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main(buffer=True)
