# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[semantic versioning](https://semver.org/).

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
