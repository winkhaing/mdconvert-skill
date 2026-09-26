# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[semantic versioning](https://semver.org/).

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
