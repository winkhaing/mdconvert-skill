# Output contract

Every conversion must satisfy these rules before it is delivered. They are asserted in `tests/test_extractor.py` where they can be asserted mechanically, and checked by the agent in step 7 of the workflow where they cannot.

## Document structure

| Rule | Detail |
| --- | --- |
| One `#` | The article title, with the journal label ("Research Article", "Original Investigation") stripped from the front |
| `##` for sections | Abstract, Introduction, Methods, Results, Discussion, References and their equivalents |
| `###` for subsections | Levels are assigned from document-wide font size and weight, not per page |
| No heading that is a sentence | A candidate longer than 120 characters or 14 words, or containing `@` or a bracketed citation, or ending in a comma, is body text |
| Run-together headings split | "Materials and methods Ethics statement" becomes `## Materials and methods` followed by `### Ethics statement` |

## Removed from the body

- Running heads, journal name, volume, issue and year lines
- Per-page DOI strips and copyright footers
- Bare page numbers
- Rotated text: watermarks, spine labels, "downloaded from" stamps
- Decorative repeated glyph rows
- Axis tick labels and panel letters that fall inside a figure crop

A candidate is treated as page furniture when its digit-normalised form recurs in the top or bottom 9 percent of the page on at least 35 percent of pages.

## Paragraphs

- Physical lines are joined into one paragraph string.
- A line ending in a hyphen followed by a lowercase continuation is dehyphenated: "dependen-" plus "cies" becomes "dependencies".
- A paragraph interrupted by a figure, a table or a page break is rejoined when the first part ends mid-sentence and the continuation starts lowercase. The interrupting block is then emitted after the completed paragraph.
- No paragraph may end mid-sentence where the source does not.

## Captions

Exactly this shape, for figures and tables alike:

```
_<u>Figure 1. Caption text as printed.</u>_
```

Italic through `_ _`, underline through `<u>`, because Markdown has no underline of its own. The caption text is never rewritten, only whitespace-normalised. Recognised prefixes: Figure, Fig, Table, Scheme, Chart, Box, Panel, Exhibit, Appendix Table, Supplementary Figure, Supplementary Table, Graphical abstract, Central illustration.

## Figures

```
![Fig 2](images/fig-p03-02.png)

_<u>Fig 2. Caption as printed.</u>_

**Figure description.** Two to six sentences describing what is visible.
```

- PNG at 220 dpi by default, in `images/`, named `fig-p<page>-<sequence>.png`
- Relative links only
- Panels sharing one caption are one file
- The crop never contains the caption
- The description states the graphic type, the axes and units, the series or groups, the direction and size of the main effect, and any annotated statistics. For a multi-panel figure it goes panel by panel. It never states a value that is not printed or readable off an axis.

## Tables

- Pipe tables with a header row and a separator row
- Literal `|` inside a cell escaped as `\|`
- Cell newlines collapsed to single spaces
- Fully empty columns dropped
- A table candidate covering less than 40 percent text is not a table; it is cropped as a figure

## Formulas

```
$$
\mathcal{L} = \frac{1}{N}\sum_{i=1}^{N} (y_i - \hat{y}_i)^2 \tag{1}
$$
```

- Display equations only. Inline mathematics stays as extracted text.
- The printed equation number is kept with `\tag{n}`.
- A formula that cannot be read confidently stays as its PNG, linked in place, and is recorded in the log.

## References

- Heading `## References`
- One entry per line, `n. text`
- `n` is the PDF's own number. Numbers are accepted only in ascending order, and only within three of the previous accepted number, so a year, a volume or a page range is never promoted to a reference number.
- Missing numbers are reported in the log. They are never closed up by renumbering.
- When the bibliography carries no numbers, entries are split on block boundaries and numbered in order, and the log says so.

## The file itself

- No editorial notes, no conversion commentary, no provenance text anywhere in the Markdown.
- No `<!-- MDC:... -->` placeholder left.
- Every link in `images/` resolves, and every file in `images/` is linked.
- Plain prose in the written descriptions, with no em-dashes.

## Delivered bundle

```
<slug>/
├── <slug>.md
└── images/
<slug>_conversion_log.md
<slug>.zip
```

The log carries the source filename, page count, the counts of figures, tables, equations and references, what was stripped as page furniture, and every unresolved warning.
