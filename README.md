# mdconvert

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![Tests](https://github.com/your-username/mdconvert-skill/actions/workflows/ci.yml/badge.svg)](https://github.com/your-username/mdconvert-skill/actions/workflows/ci.yml)

A Claude skill that converts born-digital scientific PDFs into clean, structured Markdown: correct multi-column reading order, page furniture and watermarks stripped, figures cropped and described, tables as real Markdown tables, display formulas as LaTeX, and references as numbered entries.

Built for researchers who need paper text in a form that a notebook, a reference manager, a static site or a retrieval index can actually use.

## Contents

- [Why this exists](#why-this-exists)
- [What it can do](#what-it-can-do)
- [What it cannot do](#what-it-cannot-do)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Output layout](#output-layout)
- [How it works](#how-it-works)
- [Validation](#validation)
- [Tuning](#tuning)
- [Repository layout](#repository-layout)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [Licence](#licence)
- [Citation](#citation)

## Why this exists

General PDF-to-text tools sort text by vertical position, so a two-column article comes out with the columns interleaved line by line. Table detectors flatten plots into rows of axis labels. Reference lists arrive as one run-on paragraph. Watermarks such as DRAFT or "Downloaded from" land in the middle of sentences. Figures are either lost or dumped as unlabelled image files.

mdconvert does the layout work explicitly, then uses Claude's vision to do the parts that geometry cannot do: reading a chart and writing what it shows, and turning a rendered formula into LaTeX.

## What it can do

| Capability | How it is done |
| --- | --- |
| Multi-column reading order | Recursive XY-cut. A vertical cut is only taken where no text block crosses the gutter, so a full-width title or banner is emitted before the columns beneath it |
| Watermarks removed | Watermarks the PDF declares (`/Artifact /Watermark` content, watermark layers) are cut out of the page content in memory, so they disappear from the text and from figure crops. Undeclared ones are removed span by span: rotated or diagonal text, transparent text, large light-grey stamps such as DRAFT, and text repeated at the same spot on most pages. Recurring logo and stamp images are hidden and never extracted as figures |
| Page furniture removed | Running heads, journal and volume lines, per-page DOI strips and copyright footers are detected by recurrence across pages; bare page numbers are dropped |
| Front matter cleaned | Licence and permission notices, "Downloaded from" lines and journal metadata blocks (Citation, Editor, Received and Accepted dates, Copyright) are removed and listed in the conversion log. Author names and affiliations stay as plain text, never as headings |
| Paragraph reconstruction | Lines are joined with hyphenation repair; a paragraph interrupted by a figure, a table, a footnote, a column break or a page break is rejoined, and the interrupting block is re-anchored after it |
| Correct hyphenation | A line-end hyphen is decided against the document's own vocabulary, then simple rules: "classi-" + "fication" joins, "high-level", "2-year", "IgG-positive" and "SARS-CoV-2" keep their hyphen |
| Clean characters | Ligature glyphs are expanded ("ﬁ" to "fi") and TeX-style spacing accents are recombined ("M¨uller" to "Müller"), so the text is searchable |
| Consistent headings | One `#` title, `##` sections, `###` subsections, assigned from document-wide font size and weight evidence rather than per-page guesses. Run-together headings such as "Results Study 1" are split |
| Figures and graphical abstracts | Raster placements, vector drawing clusters, small diagrams that sit next to a caption, and caption-anchored regions are cropped to PNG at 220 dpi, saved in `images/` and linked relatively. Panels that share one caption are merged into a single image |
| Figure descriptions | Claude reads each crop and writes a short description under the image, inside the same Markdown file |
| Real tables | Ruled and whitespace-aligned tables become pipe tables with escaped separators, never screenshots. A row-label column printed outside the ruled grid is recovered and joined to its rows |
| Charts kept out of tables | A table candidate that contains curves or diagonal strokes, or that is mostly empty and mostly graphics, is reclassified as a chart and cropped as a figure |
| Captions styled consistently | Every figure and table caption is rendered `_<u>Figure 1. Caption as printed.</u>_`, italic plus underline. In-text mentions such as "Fig. 6 shows" are not mistaken for captions |
| Display formulas | Equation regions are cropped and converted to `$$ ... $$` LaTeX, keeping the printed equation number as `\tag{n}` |
| Numbered references | Sequential number matching that tolerates at most two missing numbers in a row, so a volume number or a year is never mistaken for a reference number. The PDF's own numbering is preserved, gaps are reported rather than filled, and the list stays where the reference section stands, ahead of any appendix |
| Chinese articles | Traditional and Simplified Chinese: lines join without stray spaces, and 圖 / 表 captions, 摘要 / 結果 / 參考文獻 sections and Chinese reference lists are recognised |
| Problem files handled | Scanned PDFs exit with code 3, encrypted PDFs with code 4 (a password can be supplied), damaged or non-PDF files with code 5. Nothing is OCR-guessed |
| Self-auditing | Figure and table caption counts are compared against extracted assets, and the reference sequence is checked for gaps. Mismatches become a repair worklist instead of a silent loss |
| Packaged output | A folder with the Markdown and `images/`, plus a zip, plus a separate conversion log |

## What it cannot do

Stated plainly, because knowing the limits is the difference between a useful tool and a misleading one.

- **No OCR.** Scanned pages, photographed pages and image-only PDFs are refused by design. Run OCR yourself first, then convert the result.
- **Not a layout engine for every script and discipline.** It is tuned for one and two-column scientific articles in Latin script and horizontal Chinese. Vertical CJK text, right-to-left scripts, newspaper layouts with five columns, and dense chemistry schemes are out of scope. MinerU is documented as a fallback for these.
- **Borderless tables are often missed.** A table set with whitespace alone and no rules may not be detected; the Transformer paper came out with 2 of its 4 tables. The caption-count check flags every such miss, and the repair pass transcribes the table from the page image.
- **Complex tables lose structure.** Merged cells, nested headers and tables continued across pages come out flattened or partially. Spanning headers are not reconstructed.
- **An undeclared watermark crossing a figure stays faintly in that crop.** Its text never reaches the Markdown, and declared watermarks and recurring stamp images are removed from the pixels too, but a plain transparent stamp drawn across a chart cannot be separated from the chart's own ink.
- **Watermark rules can, rarely, remove genuine text.** Very large light-grey text, fully transparent text and text repeated at the identical position on most pages are treated as watermarks. Everything removed is listed in the conversion log so it can be checked.
- **Formula conversion is not guaranteed.** Display equations are converted from the rendered image, which is reliable for ordinary mathematics and unreliable for long multi-line derivations, matrices and heavily annotated expressions. Inline mathematics inside a sentence is left as extracted text.
- **Unnumbered reference styles are approximate.** Author-year bibliographies without numbers are split on block boundaries and numbered in order, which can merge two short entries. The log says when this fallback was used.
- **Semantics are not checked.** The tool preserves what the PDF says. It does not verify claims, resolve citations, or reconcile numbers in the text against numbers in the tables.
- **Not a batch server.** It converts one document per run, interactively, with Claude in the loop for the vision and repair passes. There is no unattended queue mode.
- **Figure descriptions are descriptions, not data.** They record what is visible. They do not read exact values off a chart, and they should not be used as a substitute for the underlying data.

## Requirements

- Python 3.9 or newer
- [PyMuPDF](https://pymupdf.readthedocs.io/) 1.24 or newer (`pip install pymupdf`)
- Claude Code, Claude Cowork, or claude.ai with skills enabled, for the vision and repair passes
- The extractor alone runs anywhere Python runs, with no Claude required

## Installation

### Option A: Claude Code (filesystem skills)

```bash
git clone https://github.com/your-username/mdconvert-skill.git ~/.claude/skills/mdconvert
pip install -r ~/.claude/skills/mdconvert/requirements.txt
```

Restart Claude Code. The skill appears as `mdconvert`.

For a project-scoped install, clone into `.claude/skills/mdconvert` inside the repository instead.

### Option B: claude.ai and Cowork (uploaded skill)

```bash
git clone https://github.com/your-username/mdconvert-skill.git
cd mdconvert-skill
bash scripts/build_bundle.sh          # writes dist/mdconvert.zip
```

Upload `dist/mdconvert.zip` in Settings, under Capabilities, then Skills.

If the interface accepts only a single file, build the self-contained variant instead, which inlines the extractor into the skill file:

```bash
python3 scripts/build_single_file_skill.py    # writes dist/SKILL.single.md
```

### Option C: extractor only, no Claude

```bash
git clone https://github.com/your-username/mdconvert-skill.git
cd mdconvert-skill
pip install -r requirements.txt
python3 scripts/mdconvert_extract.py paper.pdf out/paper
```

You get the Markdown, the figure crops and the worklist. Figure descriptions and LaTeX stay as `<!-- MDC:... -->` placeholders, since those steps need a vision model.

## Usage

### In Claude

Attach a PDF and ask:

> Convert this paper to Markdown with mdconvert

Claude runs the extractor, reads each figure crop and each formula crop, repairs what the worklist flags, verifies the output contract, and returns a folder plus a zip.

### From the command line

```bash
python3 scripts/mdconvert_extract.py INPUT.pdf OUTDIR [--dpi 220] [--password PW]
```

| Exit code | Meaning |
| --- | --- |
| 0 | Converted. `OUTDIR` holds the Markdown, `images/`, `equations/` and `_worklist.json` |
| 3 | Scanned or image-only PDF, nothing written. Provide a born-digital PDF |
| 4 | Encrypted PDF: a password is needed, or the one given is wrong. Rerun with `--password` |
| 5 | The file is not a PDF, or is too damaged to open |
| other | Unhandled error, see the traceback |

`--dpi` sets the resolution of the figure crops. 220 suits screen reading; 300 or more suits reuse in a manuscript, at a larger file size.

## Output layout

```
paper/
├── paper.md
├── images/
│   ├── fig-p01-01.png
│   └── fig-p04-02.png
└── equations/            (removed after the formula pass)
    └── eq-001.png
paper_conversion_log.md
paper.zip
```

`_worklist.json` records the counts, the stripped page furniture and front matter, the watermarks removed, the figure and equation inventory, and the warnings. It is a working file and is deleted before delivery; its content is summarised in the conversion log.

See [examples/](examples/) for a converted document, and [docs/output-contract.md](docs/output-contract.md) for the exact formatting rules.

## How it works

```
PDF
 │
 ├─ open ──────────────────────── damaged → exit 5, encrypted without password → exit 4
 │
 ├─ declared watermarks ───────── cut /Artifact /Watermark and watermark-layer content
 │                                out of the page streams, hide watermark layers
 │
 ├─ scanned gate ──────────────── fewer than 120 chars per page → exit 3
 │
 ├─ document statistics ───────── body font size, vocabulary, text and images that
 │                                recur at the same position on most pages
 │
 ├─ span filter ───────────────── drop rotated, transparent, layer, large light and
 │                                recurring text before any layout decision is made
 │
 ├─ per page
 │    ├─ text blocks with font profile and geometry
 │    ├─ table candidates, charts told apart by curves and cell occupancy,
 │    │  row-label columns recovered from outside the grid
 │    ├─ figure regions: raster rects, vector clusters, captioned small diagrams,
 │    │                  caption-anchored bands; merged, grouped by caption
 │    └─ XY-cut reading order over text, tables and figures together
 │
 ├─ document passes ───────────── title, front matter, heading levels, footnotes,
 │                                equations, split-paragraph rejoin, references
 │
 ├─ emit Markdown with <!-- MDC:FIG --> and <!-- MDC:EQ --> placeholders
 │
 ├─ vision passes (Claude) ────── figure descriptions, formula LaTeX
 │
 └─ repair and verification ───── warnings worked against rendered pages
```

The split matters: geometry decides *where things are*, and only the questions that genuinely need a model (what does this chart show, what is this formula) are sent to one. That keeps the conversion fast, reproducible and cheap, and confines model judgement to the places where judgement is actually required.

## Validation

`tests/` builds two synthetic articles with known ground truth and asserts the output contract in 35 tests.

The English fixture is a three-page, two-column article carrying a running header and page numbers, a licence notice above the title, an author line, hand-set line-end hyphens of both kinds, a display equation, a figure, a table whose row labels sit outside the ruled grid, a TeX-style accent, content after the references, a paragraph that continues across a column break, and five watermarks: a transparent diagonal stamp across body text, a declared watermark, text on a watermark layer, a large light DRAFT across the table, and a recurring stamp image. The Chinese fixture covers joining, captions, sections and references. Further tests cover scanned, encrypted and damaged files, and the text helpers directly.

```bash
python3 -m unittest discover -s tests -v
```

The pipeline was also checked against three structurally different real papers:

| Paper | Layout | Pages | Figures | Equations | Tables | References |
| --- | --- | --- | --- | --- | --- | --- |
| Deep residual learning (CVPR) | Two column | 12 | 7 of 7 | 2 | 13 of 14 | 1 to 50, complete |
| PLOS NTD research article | Single column | 14 | 3 of 3 | 0 | 3 of 3, 2 row-label columns recovered | 44 found, gap at 2 to 3 reported |
| Attention is all you need | Mixed | 15 | 5 of 5 | 6 | 2 of 4, borderless | 1 to 40, complete |

The counts are reported against the captions printed in each paper, and every shortfall appeared as a warning in the worklist rather than as a silent loss. The PLOS row is the point: two reference numbers were not recoverable from the text layer, and the tool reported the gap instead of renumbering the list to look complete.

## Tuning

Thresholds live in `scripts/mdconvert_extract.py`. The ones worth touching:

| Constant or check | Default | Effect |
| --- | --- | --- |
| scanned gate | 120 chars per page | Lower it for very sparse documents such as poster PDFs |
| transparent text | alpha below 200 of 255 | Text drawn more transparent than this is a watermark |
| large light text | 2.5 times body size and luminance 0.6 | Raise either if a genuine light-coloured heading disappears |
| recurrence | 60 percent of pages, at least 2 | Text, images and vector marks repeated at one position this often are furniture or watermarks |
| `WM_LAYER_RE` | watermark, draft, confidential, stamp, ... | Layer names treated as watermarks |
| chart test | 3 curves or diagonals, or text coverage under 0.40 with cells mostly empty | Table versus chart boundary |
| `gutter_min` | `max(11, 0.022 * page width)` | Column gutter width. Raise it for wide-tracked single-column layouts that split wrongly |
| vector cluster minimum | 1.2 percent of page area, 0.3 percent next to a caption | Lower it to catch small line diagrams, at the cost of picking up rules and decorations |
| `COMPOUND_FIRST` | high, low, well, non, ... | Words that keep a line-end hyphen when the document itself gives no evidence |

## Repository layout

```
mdconvert-skill/
├── SKILL.md                      skill entry point, workflow and output contract
├── scripts/
│   ├── mdconvert_extract.py      the extractor
│   ├── build_bundle.sh           builds dist/mdconvert.zip for upload
│   └── build_single_file_skill.py builds dist/SKILL.single.md
├── docs/
│   ├── output-contract.md        the exact formatting rules
│   ├── limitations.md            the long form of "what it cannot do"
│   └── troubleshooting.md        symptom to fix
├── examples/
│   └── two-column-article.md     converted output of the test fixture
├── tests/
│   ├── make_fixture.py           generates the ground-truth PDFs
│   └── test_extractor.py         output contract assertions
└── .github/workflows/ci.yml      tests on 3.9 to 3.12
```

## Roadmap

- Borderless table detection from column alignment
- Table structure: merged cells and spanning headers
- Tables continued across pages, joined into one
- Inline mathematics recovered from math-font spans
- A `--json` output carrying the document tree for retrieval pipelines
- Optional MinerU backend behind the same output contract

## Contributing

Issues and pull requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md). A conversion bug report is most useful with the DOI or a link to the open-access PDF, the page number, what the output looked like, and what it should have been.

## Licence

MIT. See [LICENSE](LICENSE).

The extractor depends on PyMuPDF, which is distributed under AGPL-3.0 or a commercial licence from Artifex. Using PyMuPDF as a library in your own distributed software carries AGPL obligations. Running it locally to convert your own documents does not.

## Citation

If this tool contributes to published work, cite it through [CITATION.cff](CITATION.cff), or:

> Khaing W. mdconvert: layout aware conversion of scientific PDFs to Markdown. Version 0.2.0. 2026. https://github.com/your-username/mdconvert-skill
