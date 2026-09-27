# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[semantic versioning](https://semver.org/).

## [0.6.0] - 2026-09-27

Three faults found in an accepted manuscript prepared in a word processor, where a whole
section arrives as one text block. All three are general, not specific to that publisher.

### Fixed

- **A heading run into the body block is now split out.** "References" arrived as the
  ninth or fortieth line of the back-matter block, so it never became a heading, the
  reference section was never found, and the entire bibliography was emitted as one
  run-on paragraph. A block is now cut at any interior line that is a heading on its own
  terms: short, no terminal punctuation, and in the section vocabulary. On the AJKD
  manuscript this recovers the reference list in full, 1 to 29 with no gaps.
- **Paragraphs cut by the layout are rejoined even when the continuation starts with a
  capital.** The rule required the next block to begin lowercase, so "... outcomes
  reported in" and "RCTs, comparative cohort studies ..." stayed two fragments. The
  decisive evidence is on the left: a prose block ending with no terminal punctuation was
  cut by the layout, not by the author. An uppercase start is now accepted, and only a
  block that plainly opens something new (a section word, a numbered heading, a reference
  entry, a caption, a list item) is refused. Mid-sentence paragraph endings on the AJKD
  manuscript fell from 28 to 4, and the 4 that remain are correct: an email address, two
  reference URLs and a figure placeholder.
- **The reference list no longer swallows the back matter.** Collection stopped only at a
  post-reference heading, so table footnotes after the bibliography were absorbed into the
  last entry, which reached 2,010 characters. It now stops at the first table or figure,
  and at the first block that has stopped looking like an entry: no number, no DOI, no
  year and volume, no URL. The longest entry is now 361 characters.

### Added

- `refs_by_indent`: a bibliography whose numbering cannot be read is split on its hanging
  indent instead, which is the boundary a reader uses and is far more reliable than
  splitting on block order. Used only when the numbering fails, and reported in the log.
- Blocks now carry `line_x`, the left edge of each line, kept correct when two blocks are
  joined.

### Changed

- Tests 78 to 87. The pre-proof fixture gains a back-matter page: the heading run into the
  block, a hanging-indent reference list, and a paragraph split with the continuation
  starting on an acronym.

## [0.5.1] - 2026-09-27

### Fixed

- **Mathematics is no longer rewritten by the superscript pass.** In an expression a raised
  run is an exponent and a lowered one an index, so 0.5.0 turned "1/M" into a Unicode
  superscript one over a LaTeX subscript M, and a summation limit into a raised glyph. A
  line is now recognised as mathematics and left exactly as printed when any of three
  signals holds: a mathematics font (CMMI, CMSY, Symbol, STIX and the like), two or more
  distinct mathematical symbols, or the shape of a short line built mostly of operators
  rather than words. Prose exponents such as "kg/m²" and "mg L⁻¹" are unaffected.
- **Greek letters recovered from an unmapped Symbol font.** Many PDFs embed Symbol without
  a usable ToUnicode map, so alpha, beta and theta arrive as "a", "b" and "q", or in the
  private-use block at U+F020. Both forms are mapped back, in the prose and in figure
  labels alike. A Symbol span that already decoded to Greek is left alone.
- **Glyphs with no Unicode mapping no longer reach the Markdown.** They arrived as NUL,
  invisible in most viewers and quietly damaging to any tool reading the file. They are
  now dropped, counted under `glyphs` in the worklist with the page and font that produced
  them, and reported as a warning so the repair pass can check those spots against the
  page image.

## [0.5.0] - 2026-09-27

### Added

- **Superscripts and subscripts are kept.** PDF carries a raised or lowered run as
  geometry, not as markup, so every version before this one flattened affiliation markers,
  Vancouver citations, units and chemical formulae: "ScD1,4", "kg/m2", "CO2",
  "previously.12". A run is now recognised when it is set in smaller type than the rest of
  its line *and* sits off that line's baseline, which leaves small capitals alone, and is
  written in one of four styles.
- `--sup-style unicode|latex|html|plain`, default `unicode`: ScD¹,⁴ and CO₂ need no
  renderer, so they show correctly in Notion, Word, Slack and a plain text editor, where
  inline `$...$` does not. `latex` writes `$^{1,4}$` for Obsidian, Quarto and Pandoc,
  `html` writes `<sup>1,4</sup>` for GitHub, and `plain` restores the old flat output.
  In `unicode` style a run with no Unicode form falls back to `$^{...}$` for that run alone.
- A raised `TM` becomes ™ and a raised `®`, `°`, prime or dagger is left as printed, in
  every style, so "MerativeTM MarketScan®" comes out as "Merative™ MarketScan®".
- Table cells are repaired. The table extractor assembles a cell from characters and keeps
  no span information, so each page's own substitutions are replayed into its cells, keyed
  on three characters of preceding context: "kg/m²", "Abs. Std. Diff.ᵃ", "(2ⁿᵈ gen)".
- `scripts` in the worklist reports the style used and how many lines changed.

### Changed

- Tests: 53 to 71. The English fixture gains a raised footnote marker in a table header
  cell; the pre-proof fixture gains raised affiliation markers, a Vancouver citation
  marker, a lowered chemical subscript and a squared unit.

## [0.4.0] - 2026-09-27

### Added

- **Permission gate for restricted copies.** A journal pre-proof, an accepted manuscript or
  an article carrying an all-rights-reserved notice with no open licence now exits with code
  6 before anything is written, printing a `document` block with the status, title, journal,
  DOI and licence. `SKILL.md` step 3 tells the user what the file is and asks; on a yes the
  same command is rerun with `--confirm-restricted`. An openly licensed article (CC-BY and
  similar) is detected as such and converts without asking.
- Publisher cover sheets (the Elsevier pre-proof front page: banner, PII, DOI, citation
  notice, disclaimer) are dropped whole and listed under `cover_sheet_removed`.
- The title is taken from the PDF metadata when that title appears in the text, merging the
  blocks it is set over, which repairs a title split across two lines. The font-size rule
  remains the fallback.
- A figure printed on its own page, after its caption on the page before, is matched to that
  page. This is how accepted manuscripts append their figures.
- Pre-proof fixture and eight tests covering the gate, the cover sheet, the title, heading
  levels and the figure page: 53 tests in total.

### Fixed

- A caption with no graphic beside it no longer crops an empty band as a figure. The band
  must contain a drawing or an image that is not part of a recurring stamp, and its ink is
  measured with the watermark painted out.
- When every heading in a document is set in one size, as in an accepted manuscript, the
  standard sections are now level 2 and the rest level 3 instead of all becoming level 1.

## [0.3.0] - 2026-09-26

### Added

- **Figure label text read from the PDF.** For every figure the worklist now carries the
  text printed inside it as vector text with positions: `text` (each label with its box,
  size and rotation), `ticks` (numeric tick labels per axis with their values, range and
  measured `linear` / `log` / `unknown` scale, plus `repeats` when side-by-side panels
  share an axis), `axis_titles`, `printed_stats` (p-values, `n =`, confidence-interval
  mentions, significance marks), `panels` (panel letters with boxes, when two or more) and
  `cited_by` (the body sentences citing that figure). Units, group names and printed
  statistics are now exact instead of being guessed from pixels.
- Axis scale is measured, not assumed: a tick row is accepted only when at least three
  numeric labels run one way across the axis, so numbers inside a diagram (layer widths,
  node labels) no longer produce a fake axis.
- The figure pass in `SKILL.md` uses those strings verbatim, states the axis scale, checks
  the description against the caption and the citing sentences, and records an
  `unreadable` list in the conversion log for anything it could not read.
- Fixture additions: numeric tick rows on both axes, a rotated y-axis title, an x-axis
  title, a printed p-value and group size, and a body sentence citing the figure. Unit
  tests for label parsing, scale fitting and axis detection: 45 tests in total.

### Fixed

- A rotated string inside a figure is read as an axis title instead of being dropped as a
  watermark, and the watermark count no longer includes it (`axis_text_recovered`).
- Axis labels and plot annotations that sit outside the figure's drawing no longer leak
  into the Markdown as stray one-line paragraphs, which also kept the figure's caption
  from being attached to it. A block is only treated as a label when it lies inside the
  figure's padded box, is shorter than 50 characters and is set in label-sized type, so a
  heading beside a figure is left alone.

### Unchanged

- The Markdown output of the three validation papers is byte-identical to 0.2.0. This
  release adds data to the worklist and does not alter the conversion.

## [0.2.0] - 2026-09-22

### Added

- **Watermark removal.** Watermarks the PDF declares (`/Artifact /Watermark` marked
  content, watermark layers) are cut out of the page content in memory, so they are absent
  from the text and from figure crops. Undeclared watermarks are removed span by span
  before layout: rotated or diagonal text, transparent text, large light text, text on a
  watermark layer, and text recurring at one position on most pages. Recurring logo and
  stamp images are hidden and never extracted as figures. Everything removed is counted
  and sampled under `watermarks` in the worklist.
- Removal of licence and permission notices, "Downloaded from" lines and journal metadata
  blocks (Citation, Editor, Received and Accepted, Copyright), listed under
  `front_matter_removed`.
- Recovery of a table's row-label column printed outside the ruled grid.
- Chinese support: line joining without spaces, 圖 and 表 captions, Chinese section and
  reference headings, Chinese reference entries.
- Exit code 4 for encrypted PDFs, with `--password`; exit code 5 for damaged or non-PDF
  files; `--version`.
- Chinese fixture, watermark, encryption and damaged-file tests, and unit tests for the
  text helpers: 35 tests in total.

### Fixed

- Author names and affiliations under the title were rendered as headings.
- Ligature glyphs ("ﬁ") and TeX spacing accents ("M¨uller") were left in the text.
- Compound words lost their hyphen at a line break ("high-level" became "highlevel"),
  and some broken words kept a hyphen and a space ("dependen- cies").
- In-text mentions such as "Fig. 6 (middle) shows" were counted as captions.
- Small captioned diagrams were missed; ResNet Figure 2 is now found.
- Plots whose grid cells hold tick labels were emitted as tables; curves and diagonal
  strokes now mark a chart.
- A paragraph split across a column or page break with nothing in between stayed split.
- The reference list was emitted after an appendix that follows it in the PDF.
- A hyphen split across two blocks of one reference entry was not repaired.

## [0.1.0] - 2026-09-20

First public release.

### Added

- Layout aware extractor (`scripts/mdconvert_extract.py`) built on PyMuPDF:
  - recursive XY-cut reading order for one and two-column pages
  - page furniture removal by cross-page recurrence, plus rotated watermark and
    bare page number filtering
  - paragraph reconstruction with hyphenation repair and rejoining of
    paragraphs interrupted by figures, tables and page breaks
  - document-wide heading level assignment, title detection with journal label
    stripping, and splitting of run-together headings
  - figure regions from raster placements, vector clusters, misread charts and
    caption-anchored bands, merged and grouped so that one caption gives one image
  - table extraction to pipe tables, with a text-coverage test that reclassifies
    a chart as a figure instead of flattening it into rows
  - display equation detection and cropping for the formula pass
  - reference parsing with tolerant sequential number matching that preserves
    the source numbering and reports gaps
  - scanned PDF gate returning exit code 3
  - self-audit comparing caption counts against extracted assets
- `SKILL.md`: the three-stage workflow, the output contract, and the repair and
  verification steps
- Generated two-column fixture (`tests/make_fixture.py`) and 11 output contract
  tests (`tests/test_extractor.py`)
- Documentation: output contract, limitations, troubleshooting
- Worked example with its figure
- Build scripts for the upload bundle and the single-file skill variant
- CI across Python 3.9 to 3.12
