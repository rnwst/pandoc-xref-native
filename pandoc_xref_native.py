#!/usr/bin/env python3

"""Adds cross-referencing capability to Pandoc's Markdown.

Cross-referencing syntax::
    @#crossref
        => <a href=#id class="cross-ref">figure </a>
    A sentence ends. @#crossref
        => A sentence ends. <a href=#id class="cross-ref">Figure </a>
    -@#crossref
        => <a href=#id class="cross-ref"></a>
    [@#crossref1, and @#crossref2]
        => figures <a href=#id1 class="cross-ref"></a>,
           and <a href=#id2 class="cross-ref"></a>

Todo:
----
- improve sentence-end detection
- parse metadata for prefixes
- add support for other output formats
- add support for other languages (pluralize)
"""

import sys
import io
import re
import subprocess
import json
import inflect

from pandocfilters import walk, RawInline, Str

#------------------------------------------------------------------------------
# Common utility items --------------------------------------------------------
#------------------------------------------------------------------------------

prefixes = {'section': 'section',
            'equation': 'equation',
            'figure': 'figure',
            'table': 'table'}

section_ids = []
equation_ids = []
figure_ids = []
table_ids = []

"""
Ids must conform to
`HTML naming rules <https://www.w3.org/TR/html4/types.html>`_ for IDs. In
addition, it is required that IDs do not end with a period, colon, or comma,
otherwise it would not be possible to write a cross-reference of the following
kind::

    A cross-reference at the end of a sentence: @#id.

The period/colon/comma would need to be separated from the ID by a space, which
would be awkward. Periods/colons are fine as long as they are not the last
character of the ID.
"""
ID_RE = r'(?P<id>[a-zA-Z][a-zA-Z0-9-_:\.]*(?<=[a-zA-Z0-9-_]))'


def pandoc(string, para=True):
    """Convert string to pandoc AST representation using pandoc executable."""
    cmd = ['pandoc', '-t', 'json']
    output = subprocess.check_output(cmd, input=string, text=True)
    ast = json.loads(output)
    if para:
        return ast['blocks'][0]['c']
    return ast


def eprint(*args, **kwargs):
    """Print messages to stderr."""
    print(*args, file=sys.stderr, **kwargs)


# -----------------------------------------------------------------------------
# Collect IDs from document ---------------------------------------------------
# -----------------------------------------------------------------------------

def sec_id(sec):
    """Return section id."""
    return sec[1][0]


def eq_id(math):
    r"""If display equation contains `\label{id}`, return id, else None."""
    math_type = math[0]
    if math_type['t'] == 'DisplayMath':
        eq_str = math[1]
        # Labels will be converted to ids in HTML and must therefore conform
        # with HTML id naming rules are a subset of LaTeX \label{} naming
        # rules.
        result = re.search(rf'\\label\{{{ ID_RE }\}}', eq_str)
        return result.group('id') if result else None
    return None


def fig_id(image):
    """If image is figure and has id, return id, else return None."""
    _id = image[0][0]
    url, title = target = image[2] # pylint: disable=unused-variable
    # Pandoc considers an image whose title attribute starts with 'fig:'
    # a figure. See https://github.com/jgm/pandoc/issues/3177.
    return _id if _id and title.startswith('fig:') else None


def tab_id(tab):
    """If table has ID, return ID, else return None."""
    _id = tab[0][0]
    return _id if _id else None


# pylint: disable=unused-argument
# Function `walk` from module `pandocfilters` expects to be passed a function
# which accepts arguments `key, value, format, meta`.
def collect_ids(key, value, _format, meta):
    """Add IDs found in document to their respective ID lists.

    Add IDs found in headings, equations, figures, and tables to their
    respective ID lists.
    """
    if key == 'Header':
        # Headings always have IDs as pandoc autogenerates them if not
        # supplied explicitly.
        section_ids.append(sec_id(value))

    if key == 'Math':
        if eq_id(value) is not None:
            equation_ids.append(eq_id(value))

    if key == 'Image':
        if fig_id(value) is not None:
            figure_ids.append(fig_id(value))

    if key == 'Table':
        if tab_id(value) is not None:
            table_ids.append(tab_id(value))


def check_id_uniqueness():
    """Check if IDs found in document are unique and remove duplicate IDs."""
    ids = section_ids + equation_ids + figure_ids + table_ids
    freqs = [ ids.count(_id) for _id in ids ]
    duplicates = { _id for _id, freq in zip(ids, freqs) if freq > 1 }
    for duplicate in duplicates:
        eprint(f'pandoc-xref-native: ID { duplicate } was defined more '
                'than once!')
        for id_list in [section_ids, equation_ids, figure_ids, table_ids]:
            id_list[:] = [ _id for _id in id_list if _id not in duplicates ]


# -----------------------------------------------------------------------------
# Resolve cross-references ----------------------------------------------------
# -----------------------------------------------------------------------------

inflect_engine = inflect.engine()

def pluralize(prefix):
    """Return plural form of prefix.

    Used by `cross_ref.__calc_prefix()`.
    """
    if prefix[-1] == '.':
        return inflect_engine.plural(prefix[:-1]) + '.'
    return inflect_engine.plural(prefix)


class CrossRef:
    """Class for cross-references found in text."""

    # pylint: disable=too-many-instance-attributes
    # There is no elegant way to reduce the number of instance arguments.
    # Furthermore, it doesn't really cause readability issues in this case.

    # Pandoc will replace spaces after known abbreviations with non-breaking
    # spaces (\xa0) (see https://pandoc.org/MANUAL.html#reader-options, under
    # --abbreviations=FILE). If the cross-reference is preceded by a known
    # abbreviation, the resulting Str element in the AST will contain both the
    # abbreviation as well as the cross-reference, separated by a non-breaking
    # space.
    re = ( r'^(?P<known_abbreviation>\S*\xa0)??'
           r'(?P<prefix_suppressor>-)??'
           r'(?P<opening_bracket>\[)??'
          rf'@#{ ID_RE }'
           r'(?P<closing_bracket>\])??'
           r'(?P<punctuation>[^a-zA-Z0-9-_\[\]]*?)$')

    inside_brackets = False
    __bracketed_type = None

    @staticmethod
    def match(string):
        """Return CrossRef instance if string matches crossref regex."""
        match_object = re.match(CrossRef.re, string)
        return CrossRef(match_object) if match_object else None


    @staticmethod
    def reset_bracket_states():
        """Set bracket states to default values."""
        CrossRef.inside_brackets = False
        CrossRef.__bracketed_type = None


    def __init__(self, match_object):
        """Initialize CrossRef instance."""
        self.match_object = match_object
        self.known_abbreviation = match_object.group('known_abbreviation')
        self.prefix_suppressor = match_object.group('prefix_suppressor')
        # pylint thinks 'id' is too short for a name.
        self.id = match_object.group('id') # pylint: disable=invalid-name
        self.opening_bracket = match_object.group('opening_bracket')
        self.closing_bracket = match_object.group('closing_bracket')
        self.punctuation = match_object.group('punctuation')

        # The following attributes are preliminarily set to None.
        self.valid = None
        self.type = None
        self.prefix = None
        self.starts_sentence = None

        self.__check()
        self.__calc_prefix()
        self.__set_bracket_states()


    def __find_type(self):
        """Determine type (section/figure/...) of ID belonging to crossref."""
        if   self.id in section_ids:
            self.type = 'section'
        elif self.id in equation_ids:
            self.type = 'equation'
        elif self.id in figure_ids:
            self.type = 'figure'
        elif self.id in table_ids:
            self.type = 'table'
        else:
            self.type = None


    def __check(self):
        """Check if cross-reference is valid."""
        # Prefix suppressor and opening bracket may not both be present.
        if ( self.prefix_suppressor and
                          (self.opening_bracket or self.closing_bracket
                                                or CrossRef.inside_brackets) ):
            eprint( 'pandoc-xref-native: A prefix suppressor (-) cannot be '
                    'used in combination with brackets: '
                   f'{ self.match_object.group() }')
            self.valid = False
            return

        # Opening and closing brackets may not both be present.
        if self.opening_bracket and self.closing_bracket:
            eprint( 'pandoc-xref-native: Opening and closing brackets cannot '
                    'both be present in the same cross-reference: '
                   f'{ self.match_object.group() }')
            self.valid = False
            return

        # An opening bracket may not appear before the previous opening bracket
        # has been closed.
        if self.opening_bracket and self.inside_brackets:
            eprint( 'pandoc-xref-native: Another opening bracket cannot be '
                    'used before the previous opening bracket has been closed:'
                   f' { self.match_object.group() }')
            self.valid = False
            return

        self.__find_type()
        if self.type is None:
            eprint(f"pandoc-xref-native: Id { self.id } was either not found "
                    "in document or defined more than once!")
            self.valid = False
            return

        # Check if crossrefs in brackets are all of the same type.
        if (not CrossRef.__bracketed_type is self.type
                                    and CrossRef.__bracketed_type is not None):
            eprint(f'pandoc-xref-native: { self.type.capitalize() } ID '
                   f'{ self.id } is inside brackets, but is not of the same '
                    'type as the previous bracketed cross-reference '
                   f'(which was a { self.__bracketed_type })!')
            self.valid = False
            return

        self.valid = True


    def __set_bracket_states(self):
        """Set bracket states based on current CrossRef instance."""
        if self.opening_bracket:
            CrossRef.inside_brackets = True
        if self.closing_bracket:
            CrossRef.inside_brackets = False
            CrossRef.__bracketed_type = None
        # In case the first bracketed cross-reference couldn't be resolved,
        # self.__bracketed_type needs to be updated for any following
        # bracketed cross-references.
        if CrossRef.inside_brackets and self.type is not None:
            CrossRef.__bracketed_type = self.type


    def __calc_prefix(self):
        """Determine prefix of crossref."""
        if self.type is None:
            return

        if self.prefix_suppressor or CrossRef.inside_brackets:
            self.prefix = ''
        else:
            self.prefix = prefixes[self.type]
            if self.opening_bracket:
                self.prefix = pluralize(self.prefix)
            self.prefix += " "


    def __maybe_capitalize_prefix(self):
        """Capitalize crossref prefix if crossref starts sentence."""
        if self.starts_sentence and not self.known_abbreviation:
            self.prefix = self.prefix.capitalize()


    def html(self):
        """Return HTML of resolved cross-reference."""
        self.__maybe_capitalize_prefix()

        if self.type is None:
            return pandoc('**unable to resolve cross-reference!**')[0]

        opening_tag = fr'<a href=#{ self.id } class="cross-ref">'
        closing_tag = r'</a>'
        if self.opening_bracket:
            html_elt = self.prefix + opening_tag + closing_tag
        else:
            html_elt = opening_tag + self.prefix + closing_tag

        elts = [ RawInline("html", html_elt) ]
        if self.known_abbreviation:
            elts.insert(0, Str(self.known_abbreviation))
        if self.punctuation:
            elts.append(Str(self.punctuation))
        return elts


def new_sentence(previous_items):
    r"""Detect if item is starting a new sentence by looking at previous items.

    Used by resolve_crossrefs.

    Pandoc will replace spaces after known abbreviations with non-breaking
    spaces (\xa0) (see https://pandoc.org/MANUAL.html#reader-options, under
    --abbreviations=FILE). As long as the user supplies all abbreviations used
    in the document, sentence demarcations can thus be inferred from whether
    the previous element (that is not a space) ends with a sentence-ending
    symbol (period, colon,...).

    This function currently only handles Strs, not special inline formatting
    like e.g. Emph or InlineMath. This will need to be fixed.
    """
    if previous_items:
        not_a_space = previous_items[-2]
        return ( not_a_space['t'] == 'Str'
                              and re.match(r'^.*[\.!\?:]$', not_a_space['c']) )
    return True


# pylint: disable=unused-argument
# Function `walk` from module `pandocfilters` expects to be passed a function
# which accepts arguments `key, value, format, meta`.
def resolve_crossrefs(key, value, _format, meta):
    """Resolve cross-references found in document."""
    if not isinstance(value, list):
        return None

    elts = value
    CrossRef.reset_bracket_states()
    for i, elt in enumerate(elts):
        if not ( isinstance(elt, dict) and 't' in elt and elt['t'] == 'Str' ):
            continue

        cross_ref = CrossRef.match(elt['c'])
        if not (cross_ref and cross_ref.valid):
            continue

        cross_ref.starts_sentence = new_sentence(elts[:i])
        elts[i:i+1] = cross_ref.html()

    if CrossRef.inside_brackets:
        eprint( 'pandoc-xref-native: Missing closing bracket after'
               f'cross-reference: { cross_ref.match_object.group() }')

    return {'t': key, 'c': elts}


# -----------------------------------------------------------------------------
# Main function and utilities -------------------------------------------------
# -----------------------------------------------------------------------------

def read_stdin():
    """Read stdin and return parsed JSON.

    Pandoc will supply the specified output format as the first argument when
    calling the filter, provided the filter is called with the `--filter`
    option rather than via pipes.
    """
    input_stream = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')
    source = input_stream.read()
    if len(sys.argv) > 1:
        _format = sys.argv[1]
    else:
        _format = ""
    doc = json.loads(source)
    return doc, _format


def compatible_output_format(_format):
    """Check if output format supplied by pandoc is supported.

    Currently, pandoc-xref-native only works with HTML output (and native).
    Output format can also be '' since no output format argument is passed to
    the filter when it is called via pipes.
    """
    return _format in {'', 'html', 'native'}


def apply_filter(_filter, doc, _format):
    """Apply supplied filters to the document."""
    if 'meta' in doc:
        meta = doc['meta']
    else:
        meta = {}
    filtered_doc = walk(doc, _filter, _format, meta)
    return filtered_doc


def write_stdout(doc):
    """Write modified document to stdout."""
    sys.stdout.write(json.dumps(doc))


def main():
    """Read doc from stdin, apply filters, and write new doc to stdout.

    Normally functions `toJSONFilters` and `applyJSONFilters` from
    `pandocfilters` module would be used, but this can't be done here because
    stuff needs to be done in between application of filters.
    """
    doc, _format = read_stdin()

    if not compatible_output_format(_format):
        eprint( 'pandoc-xref-native does not work with output format '
               f'{ _format }!')
        write_stdout(doc)
        return

    apply_filter(collect_ids, doc, _format)
    check_id_uniqueness()
    new_doc = apply_filter(resolve_crossrefs, doc, _format)
    write_stdout(new_doc)


if __name__ == "__main__":
    main()
