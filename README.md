# mdconvert

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![Tests](https://github.com/your-username/mdconvert-skill/actions/workflows/ci.yml/badge.svg)](https://github.com/your-username/mdconvert-skill/actions/workflows/ci.yml)

A Claude skill that converts born-digital scientific PDFs into clean, structured Markdown: correct multi-column reading order, page furniture stripped, figures cropped and described, tables as real Markdown tables, display formulas as LaTeX, and references as numbered entries.

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

General PDF-to-text tools sort text by vertical position, so a two-column article comes out with the columns interleaved line by line. Table detectors flatten plots into rows of axis labels. Reference lists arrive as one run-on paragraph. Figures are either lost or dumped as unlabelled image files.

mdconvert does the layout work explicitly, then uses Claude's vision to do the parts that geometry cannot do: reading a chart and writing what it shows, and turning a rendered formula into LaTeX.

## What it can do

| Capability | How it is done |
| --- | --- |
| Multi-column reading order | Recursive XY-cut. A vertical cut is only taken where no text block crosses the gutter, so a full-width title or banner is emitted before the columns beneath it |
| Page furniture removed | Running heads, journal and volume lines, per-page DOI strips and copyright footers are detected by recurrence across pages in the top and bottom bands; bare page numbers and rotated watermark text are dropped |
| Paragraph reconstruction | Lines are joined with hyphenation repair; a paragraph interrupted by a figure, a table or a page break is rejoined, and the interrupting block is re-anchored after it |
| Consistent headings | One `#` title, `##` sections, `###` subsections, assigned from document-wide font size and weight evidence rather than per-page guesses. Run-together headings such as "Results Study 1" are split |
| Figures and graphical abstracts | Raster placements, vector drawing clusters and caption-anchored regions are cropped to PNG at 220 dpi, saved in `images/` and linked relatively. Panels that share one caption are merged into a single image |
| Figure descriptions | Claude reads each crop and writes a short description under the image, inside the same Markdown file |
| Real tables | Ruled and whitespace-aligned tables become pipe tables with escaped separators, never screenshots |
| Charts kept out of tables | A table candidate whose area is less than 40 percent text is reclassified as a chart and cropped as a figure. This is what stops plot axes becoming fake tables |
| Captions styled consistently | Every figure and table caption is rendered `_<u>Figure 1. Caption as printed.</u>_`, italic plus underline |
| Display formulas | Equation regions are cropped and converted to `$$ ... $$` LaTeX, keeping the printed equation number as `\tag{n}` |
| Numbered references | Sequential number matching that tolerates at most two missing numbers in a row, so a volume number or a year is never mistaken for a reference number. The PDF's own numbering is preserved, and gaps are reported rather than filled |
| Scanned PDFs refused | A PDF averaging fewer than 120 characters per page exits with code 3 and a clear message. Nothing is OCR-guessed |
| Self-auditing | Figure and table caption counts are compared against extracted assets, and the reference sequence is checked for gaps. Mismatches become a repair worklist instead of a silent loss |
| Packaged output | A folder with the Markdown and `images/`, plus a zip, plus a separate conversion log |

## What it cannot do

Stated plainly, because knowing the limits is the difference between a useful tool and a misleading one.

- **No OCR.** Scanned pages, photographed pages and image-only PDFs are refused by design. Run OCR yourself first, then convert the result.
- **Not a layout engine for every discipline.** It is tuned for one and two-column scientific articles in Latin script. Vertical CJK text, right-to-left scripts, newspaper-style layouts with five columns, and dense chemistry schemes are out of scope. MinerU is documented as a fallback for these.
- **Small vector diagrams are sometimes missed.** A figure drawn as a handful of vector strokes below the size threshold may not be detected. The caption-count check flags it, and the repair pass crops it by hand.
- **Complex tables lose structure.** Merged cells, nested headers, multi-row stubs and tables split across pages come out flattened or partially. Spanning headers are not reconstructed.
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
python3 scripts/mdconvert_extract.py INPUT.pdf OUTDIR [--dpi 220]
```

| Exit code | Meaning |
| --- | --- |
| 0 | Converted. `OUTDIR` holds the Markdown, `images/`, `equations/` and `_worklist.json` |
| 3 | Scanned PDF, nothing written. Provide a born-digital PDF |
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

`_worklist.json` records the counts, the stripped page furniture, the figure and equation inventory, and the warnings. It is a working file and is deleted before delivery; its content is summarised in the conversion log.

See [examples/](examples/) for a converted document, and [docs/output-contract.md](docs/output-contract.md) for the exact formatting rules.

## How it works

```
PDF
 │
 ├─ scanned gate ──────────────── fewer than 120 chars per page → exit 3
 │
 ├─ page chrome pass ──────────── recurrence in top and bottom bands across pages
 │
 ├─ per page
 │    ├─ text blocks with font profile and geometry
 │    ├─ table candidates, scored by text coverage (chart or table)
 │    ├─ figure regions: raster rects, vector clusters, misread charts,
 │    │                  caption-anchored bands; merged, grouped by caption
 │    └─ XY-cut reading order over text, tables and figures together
 │
 ├─ document passes ───────────── title, heading levels, equations,
 │                                interrupted-paragraph rejoin, references
 │
 ├─ emit Markdown with <!-- MDC:FIG --> and <!-- MDC:EQ --> placeholders
 │
 ├─ vision passes (Claude) ────── figure descriptions, formula LaTeX
 │
 └─ repair and verification ───── warnings worked against rendered pages
```

The split matters: geometry decides *where things are*, and only the questions that genuinely need a model (what does this chart show, what is this formula) are sent to one. That keeps the conversion fast, reproducible and cheap, and confines model judgement to the places where judgement is actually required.

## Validation

`tests/` builds a synthetic two-column article with known ground truth and asserts the output contract: single H1, chrome removed, column order, paragraph integrity, caption styling, a real pipe table, a linked figure, an equation placeholder, and a sequential reference list. A separate test asserts that an image-only PDF exits with code 3.

```bash
python3 -m unittest discover -s tests -v
```

The pipeline was also checked against three structurally different real papers:

| Paper | Layout | Pages | Figures | Equations | Tables | References |
| --- | --- | --- | --- | --- | --- | --- |
| Deep residual learning (CVPR) | Two column | 12 | 6 | 2 | 13 | 1 to 50, complete |
| PLOS NTD research article | Single column | 14 | 4 | 0 | 3 | 44 found, gap at 2 to 3 reported |
| Attention is all you need | Mixed | 15 | 5 | 6 | 2 | 1 to 40, complete |

The PLOS row is the point: two reference numbers were not recoverable from the text layer, and the tool reported the gap instead of renumbering the list to look complete.

## Tuning

Thresholds live at the top of `scripts/mdconvert_extract.py` and in the per-page section. The ones worth touching:

| Constant or check | Default | Effect |
| --- | --- | --- |
| scanned gate | 120 chars per page | Lower it for very sparse documents such as poster PDFs |
| `textcov(r) < 0.40` | 0.40 | Table versus chart boundary. Raise it if plots become tables, lower it if sparse tables become images |
| `gutter_min` | `max(11, 0.022 * page width)` | Column gutter width. Raise it for wide-tracked single-column layouts that split wrongly |
| vector cluster minimum | 1.2 percent of page area | Lower it to catch small line diagrams, at the cost of picking up rules and decorations |
| chrome recurrence | 35 percent of pages | Lower it for documents where the running head changes between sections |

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
│   ├── make_fixture.py           generates the ground-truth PDF
│   └── test_extractor.py         output contract assertions
└── .github/workflows/ci.yml      tests on 3.9 to 3.12
```

## Roadmap

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

> Khaing W. mdconvert: layout aware conversion of scientific PDFs to Markdown. 2026. https://github.com/your-username/mdconvert-skill
