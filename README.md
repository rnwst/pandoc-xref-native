# pandoc-xref-native

A [pandoc](https://pandoc.org/index.html) [filter](https://pandoc.org/filters.html) that adds cross-referencing capability to [Pandoc's Markdown](https://pandoc.org/MANUAL.html#pandocs-markdown). **It is still a WIP** and at this stage can't be used for anything other than HTML output.

## Summary

There are already excellent pandoc filters for cross-references out there, namely [pandoc-crossref](https://github.com/lierdakil/pandoc-crossref), [pandoc-xnos](https://github.com/tomduck/pandoc-xnos), and [luarefnos](https://github.com/tstenner/luarefnos) (which will be referred to in the following as the *existing filters*). There are two main differences between the existing filters and pandoc-xref-native:

1. **Syntax**: Cross-referencing is done using the following syntax: `See @#figid` (which renders as "See figure 1"), unlike the existing filters, which use pandoc's citation syntax: `See @figid`. The author believes that cross-references and citations are semantically different, and should therefore be syntactically different as well.<div></div>
As a side-effect, pandoc-xref-native's cross-referencing syntax does not conflict with the citation syntax in Pandoc's Markdown, since citations must start with a letter, digit, or underscore (see [here](https://pandoc.org/MANUAL.html#citation-syntax)), and therefore pandoc will not convert `@#figid` to a citation (since "`#`" is neither a letter, digit, or underscore). As a consequence, it does not matter in which order `--citeproc` and `--filter pandoc-xref-native.py` are called (which is not the case for the existing filters, where the respective filter needs to be called before citeproc is called).


2. **pandoc-xref-native does not hard-code cross-reference numbers** - rather it lets the output format compute cross-references, natively (hence the name). Therefore, it can only support output formats which are capable of native numbering of sections, figures, equations, and tables, as well as native cross-references to those items. Some of those compatible output formats include HTML, LaTeX, ConTeXt, Docx, and ms (though, as noted, currently **only HTML is implemented**). Native numbering of sections, figures, equations, and tables in HTML is done using [CSS counters](https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Counter_Styles/Using_CSS_counters), and cross-references are numbered using JavaScript.<div></div>
This is a deliberate design choice. If the output format is edited and, for example, a figure is inserted before an existing *figure 1*, all existing cross-references to figures need to be renumbered so that they still reference the right figures (since a cross-reference that was previously referencing *figure 1* should now read *figure 2*). If the output format does not support native cross-references, this renumbering process needs to be done by hand, which is arduous and error-prone. This is, of course, not an issue if one never intends to edit in the output format.


## Known limitations

pandoc-xref-native is very much a WIP. Currently, it **only works with HTML output**. The author hopes to add other output formats which are capable of native cross-references in the fullness of time (in particular LaTeX and Docx). There are a few other items the author would like to implement, such as the ability to specify prefixes for sections, figures, equations, and tables that differ from "section", "figure", "equation", and "table".


## How it works

pandoc-xref-native first collects all IDs (and equation labels) it can find in the document, and remembers the *type* of every ID (section, figure, equation, or table). It will then resolve all cross-references found in the document (but without numbering them - that is done by the output format). If an ID cannot be matched to a corresponding element, an ID is defined more than once, or a cross-reference is not of the expected *type*, pandoc-xref-native will write a corresponding message to stderr.


## Usage

### Pandoc options

The filter can be used as follows:
```
$ pandoc input_file.pdc -o output_file.html -f markdown -t html --mathjax \
      --filter pandoc_xref_native.py --resource-path=/path/to/templates/ \
      --template=xref-native
```
Since cross-references are done natively in HTML using JavaScript, a custom template needs to be supplied, `html/xref-native.html`. The template consists of the *partials* `html/counters.css` and `html/number_crossrefs.js`. These three files must all be in the same directory, which is passed to pandoc using the `--resource-path` option. Alternatively, they can be copied to `$HOME/.local/share/pandoc/data/templates/` (see [here](https://pandoc.org/MANUAL.html#general-options) under option `--data-dir` for further details).

Displaying of equations is done using MathJax, which is configured in the template `html/xref-native.html`. Therefore, the option `--mathjax` needs to be passed to pandoc.

The option **`--number-sections` must not be passed to pandoc** - pandoc-xref-native takes care of section numbers already, and `--number-sections` would result in sections being numbered doubly. In addition, `--number-sections` hardcodes section numbers in HTML (unlike pandoc-xref-native, which uses [CSS counters](https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Counter_Styles/Using_CSS_counters)). Thus, sections wouldn't be automatically renumbered in HTML if another section was to be inserted in the output.

Further information on pandoc's options can be found [here](https://pandoc.org/MANUAL.html#options).

### Cross-referencing syntax

The syntax used for cross-referencing items is briefly presented below using a series of examples.

| Pandoc's Markdown | Output |
| --- | --- |
| `See @#figid. See @#eqid.` | See [figure 1](#). See [equation (1)](#). |
| `A sentence ends. @#figid shows clearly...` | A sentence ends. [Figure 1](#) shows clearly... |
| `See [@#figid, @#figid2, and @#figid3].` | See figures [1](#), [2](#), and [3](#). |
| `See -@#figid.` | See [1](). |

pandoc-xref-native assumes no particular ID naming convention - the user is free to use a naming convention like `@#sec:id` for section IDs, or `@#fig:id` for figure IDs, but can also choose not to do so. pandoc-xref-native will infer the cross-reference's prefix ("section", "figure", "equation", or "table") from the *type* of element that the ID references. IDs must be unique in the document.

### Specifying section and figure IDs

Section and figure IDs are specified as they would normally be in Pandoc's Markdown:
```
# A section {#id}

![Figure caption.](figure.jpg){#fig:id}
```

### Specifying equation IDs

Equation IDs/labels are specified just like they would be in LaTeX:
```
$$
E=mc^2
\label{eq:einstein}
$$
```
pandoc-xref-native will check all numbered display equations for the presence of a `\label{...}` tag. It is assumed that all display equations will be numbered, unless they contain a `\nonumber` or `\notag` tag. This is equivalent to [MathJax's `tags` value `'all'`](https://docs.mathjax.org/en/latest/input/tex/eqnumbers.html).

### Specifying table IDs

Table IDs can be specified in Pandoc's Markdown using [pandoc-table-attr](https://github.com/rnwst/pandoc-table-attr).

## License

© 2022 R. N. West. Released under the [GPL](https://www.gnu.org/licenses/old-licenses/gpl-2.0.html) version 2 or greater. This software carries no warranty of any kind. See file COPYRIGHT for full copyright and warranty notices.
