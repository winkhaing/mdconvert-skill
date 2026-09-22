# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[semantic versioning](https://semver.org/).

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
