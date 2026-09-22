# Output contract

Every conversion must satisfy these rules before it is delivered. They are asserted in `tests/test_extractor.py` where they can be asserted mechanically, and checked by the agent in step 7 of the workflow where they cannot.

## Document structure

| Rule | Detail |
| --- | --- |
| One `#` | The article title, with the journal label ("Research Article", "Original Investigation") stripped from the front |
| `##` for sections | Abstract, Introduction, Methods, Results, Discussion, References and their equivalents, including 摘要, 結果, 討論 and 參考文獻 |
| `###` for subsections | Levels are assigned from document-wide font size and weight, not per page |
| Authors are not headings | Everything between the title and the first section heading on page 1 (author names, affiliations, correspondence) stays plain text |
| No heading that is a sentence | A candidate longer than 120 characters or 14 words (30 characters for Chinese), or containing `@` or a bracketed citation, or ending in a comma, is body text |
| Run-together headings split | "Materials and methods Ethics statement" becomes `## Materials and methods` followed by `### Ethics statement` |

## Removed from the body

**Watermarks**, in two layers:

1. *Declared by the PDF.* Content inside `/Artifact <</Subtype /Watermark>>` marked content, and content tagged with an optional-content layer whose name matches watermark, draft, confidential, do not copy, sample, stamp or background. These sections are cut out of the page content in memory before anything is read, so they are absent from the text and from every figure crop. Watermark layers are also switched off for rendering.
2. *Not declared.* Removed from the text span by span, before layout:
   - rotated or diagonal text
   - transparent text (alpha below 200 of 255)
   - large light text: at least 2.5 times the body font size with luminance 0.6 or more
   - text that sits at the same position on at least 60 percent of pages
   - text on a watermark layer that is attached to an object rather than to marked content

Images drawn at the same position on at least 60 percent of pages (logos, stamps, page backgrounds) are hidden from figure crops and are never extracted as figures. Vector marks recurring the same way are ignored as figure candidates.

**Page furniture:**

- Running heads, journal name, volume, issue and year lines
- Per-page DOI strips and copyright footers
- Bare page numbers
- Decorative repeated glyph rows
- Axis tick labels and panel letters that fall inside a figure crop

A candidate is page furniture when its digit-normalised form recurs in the top or bottom 9 percent of the page on at least 35 percent of pages.

**Front matter and notices**, when shorter than 700 characters and placed on the first or last page, in the top or bottom 12 percent of a page, or in small print:

- licence and permission notices, "Downloaded from" lines, "Check for updates"
- Citation, Editor, Received and Accepted, and Copyright blocks
- arXiv identifier stamps

A block that begins like a reference entry (`12.` or `[12]`) is never removed by these rules.

Everything removed under this section is listed in the conversion log.

## Characters

- Ligature glyphs are expanded: ﬀ ﬁ ﬂ ﬃ ﬄ become ff fi fl ffi ffl.
- A spacing accent placed before its letter, as TeX-produced PDFs emit it, is recombined: "M¨uller" becomes "Müller", "Doll´ar" becomes "Dollár". A prime after a digit ("5´UTR") is left alone.
- Text is normalised to Unicode NFC.

## Paragraphs

- Physical lines are joined into one paragraph string.
- A line-end hyphen is resolved in this order:
  1. followed by an uppercase letter or a digit: kept, no space ("SARS-" + "CoV-2")
  2. preceded by a digit, or by two or more capitals: kept ("2-year", "IgG-positive")
  3. preceded by a word ending in "-ly": kept ("deeply-supervised")
  4. the document's own vocabulary decides: whichever of "highlevel" and "high-level" appears more often elsewhere in the text wins
  5. otherwise kept only if the first part is a common compound element (high, low, well, non, self, ...), and joined in every other case ("dependen-" + "cies")
- Chinese lines join without a space between characters.
- A paragraph interrupted by a figure, a table, an equation, a caption, a footnote, a column break or a page break is rejoined when the first part ends mid-sentence and the continuation starts lowercase (or, in Chinese, with a character after an unfinished sentence). The interrupting block is then emitted after the completed paragraph.
- No paragraph may end mid-sentence where the source does not.

## Captions

Exactly this shape, for figures and tables alike:

```
_<u>Figure 1. Caption text as printed.</u>_
```

Italic through `_ _`, underline through `<u>`, because Markdown has no underline of its own. The caption text is never rewritten, only whitespace-normalised.

A block is a caption when it starts with a label and a number followed by punctuation, an uppercase word, or the end of the block. Recognised labels: Figure, Fig, Table, Scheme, Chart, Box, Panel, Exhibit, Appendix Table, Supplementary Figure, Supplementary Table, Graphical abstract, Central illustration, 圖, 图, 図, 表. "Fig. 6 (middle) shows" and "Table 1 shows" are body text.

## Figures

```
![Fig 2](images/fig-p03-02.png)

_<u>Fig 2. Caption as printed.</u>_

**Figure description.** Two to six sentences describing what is visible.
```

- PNG at 220 dpi by default, in `images/`, named `fig-p<page>-<sequence>.png`, rendered without annotations
- Relative links only
- Panels sharing one caption are one file
- The crop never contains the caption
- The description states the graphic type, the axes and units, the series or groups, the direction and size of the main effect, and any annotated statistics. For a multi-panel figure it goes panel by panel. It never states a value that is not printed or readable off an axis, and it never mentions a watermark.

## Tables

- Pipe tables with a header row and a separator row
- Literal `|` inside a cell escaped as `\|`
- Cell newlines collapsed to single spaces
- Fully empty columns dropped
- A row-label column printed outside the ruled grid is added as the first column when at least half of the body rows carry a left-aligned label within 80 points of the grid
- On a page where watermark text was removed, cell text is rebuilt from the filtered words, so a watermark across a table never enters a cell
- A table candidate with 3 or more curves or diagonal strokes inside it, or with text coverage below 0.40 and fewer than half its cells filled, is a chart and is cropped as a figure

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

- Heading `## References`, or the source heading when it is not English (`## 參考文獻`)
- The list sits where the reference section stands in the document, so an appendix that follows the references still follows them
- One entry per line, `n. text`; a hyphen split across the lines or blocks of an entry is repaired
- `n` is the PDF's own number. Numbers are accepted only in ascending order, and only within three of the previous accepted number, so a year, a volume or a page range is never promoted to a reference number.
- Missing numbers are reported in the log. They are never closed up by renumbering.
- When the bibliography carries no numbers, entries are split on block boundaries and numbered in order, and the log says so.

## The file itself

- No editorial notes, no conversion commentary, no provenance text anywhere in the Markdown.
- No `<!-- MDC:... -->` placeholder left.
- No watermark sample from the worklist appears in the Markdown.
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

The log carries the source filename, page count, the counts of figures, tables, equations and references, what was stripped as page furniture and front matter, the watermarks removed, the row-label columns recovered, and every unresolved warning.
