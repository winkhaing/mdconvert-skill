---
name: mdconvert
description: Convert a born-digital scientific PDF into clean Markdown with extracted figure images whose labels, axes and printed statistics are read from the PDF itself, real Markdown tables, display LaTeX formulas and numbered references, with watermarks removed, delivered as a folder plus a zip.
---

# mdconvert

Turns a scientific PDF (journal article, preprint, report) into one Markdown file plus an `images/` folder.

Three stages, in order:

1. **Deterministic extraction** with PyMuPDF geometry: watermark and page chrome removal, multi-column reading order, paragraph reconstruction, tables, figure cropping, reference parsing.
2. **Vision passes**: read each cropped figure and each cropped formula yourself and write the description / LaTeX into the file.
3. **Repair and verification** against the page images, then packaging.

Scanned PDFs are refused, not OCR-guessed. English and Chinese (Traditional and Simplified) articles are supported.

## Output contract

These rules are not negotiable. Check every one of them in step 7.

- One `#` title. Section headings use `##`, subsections `###`. Heading level comes from document-wide font evidence, applied consistently. Author names and affiliations under the title are plain text, never headings.
- Running heads, journal name, volume/issue lines, per-page DOI strips, copyright footers, page numbers, licence and permission notices, and journal metadata blocks (Citation, Editor, Received/Accepted, Copyright) are removed.
- **Watermarks never reach the Markdown**: diagonal or rotated stamps, transparent text, text on a watermark layer, watermarks the PDF declares as such, large light-grey stamps such as DRAFT, text repeated at the same spot on every page, and recurring logo or stamp images.
- Reading order follows the columns, not the raster lines. Nothing from column 2 interleaves into column 1.
- A paragraph split by a figure, a table, a footnote, a column break or a page break is rejoined into one paragraph; the interrupting block is then placed after that paragraph, never inside it.
- Line-end hyphens are resolved: "classi-" + "fication" becomes "classification", while "high-" + "level" stays "high-level". Ligatures and TeX-style accents are repaired ("ﬁ" to "fi", "M¨uller" to "Müller").
- Figure and table captions are italic and underlined, exactly: `_<u>Figure 1. Caption as printed.</u>_`
- Tables are pipe tables, including a row-label column that sits outside the ruled grid. Never a screenshot of a table.
- Figures, infographics and graphical abstracts are saved as PNG in `images/` and linked relatively. A short description sits directly under each one, with every label, unit and printed statistic taken from the PDF's own text rather than read off the picture.
- Display formulas become `$$ ... $$` LaTeX.
- References are one numbered entry per line, carrying the PDF's own numbering, in the position where the reference section stands. Never invent a number that is not in the source.
- The Markdown body carries no editorial notes, no provenance text, no conversion commentary. All of that belongs in the separate log file written in step 8.
- Write plain prose in the descriptions. No em-dashes.

## Workflow

### 1. Locate the PDF and set up

A PDF attached to the chat is under `/mnt/user-data/uploads/`. A PDF in a connected folder must be staged into the container first, because the vision passes need to open the crops here.

```bash
python3 -c "import pymupdf" 2>/dev/null || pip install --quiet --break-system-packages pymupdf
```

The extractor ships with this skill at `scripts/mdconvert_extract.py`. Pick a short slug for the output, from the PDF filename or the article title (lowercase, hyphens, no spaces).

### 2. Run the extractor

```bash
python3 scripts/mdconvert_extract.py "<input.pdf>" "<workdir>/<slug>" --dpi 220
```

Add `--password "<pw>"` only when the user has given one. The extractor writes `<slug>.md`, `images/`, `equations/` and `_worklist.json`, and prints a summary.

| Exit | Meaning | What to do |
| --- | --- | --- |
| 0 | Converted | Continue with step 4 |
| 3 | Scanned or image-only PDF | Step 3 |
| 4 | Encrypted, password needed or wrong | Ask for the password, then rerun with `--password` |
| 5 | Not a PDF, or damaged | Tell the user the file cannot be opened and ask for another copy |

### 3. Scanned PDF: stop

On exit 3, do not OCR, do not deliver a partial file. Reply with one line:

> This is a scanned PDF with no text layer. Please provide the original (born-digital) PDF and I will convert it.

### 4. Figure pass

Read `_worklist.json`. Each entry in `figures` carries the crop plus the figure's own text, read out of the PDF rather than off the image:

| Field | What it holds |
| --- | --- |
| `caption` | the caption as printed |
| `text` | every label inside the figure: `t` text, `b` box, `s` size, `rot` true when rotated |
| `ticks.x`, `ticks.y` | the numeric tick labels, their `values`, `range`, `scale` (`linear`, `log` or `unknown`), and `repeats` when side-by-side panels share the axis |
| `axis_titles` | the x and y axis titles |
| `printed_stats` | p-values, `n =`, confidence-interval mentions and significance marks printed on the plot |
| `panels` | panel letters with their boxes, when two or more were found |
| `cited_by` | the sentences in the body that cite this figure |
| `label_box` | the figure plus the labels around it. The crop is the figure itself, so use this box to re-crop wider when a label is cut off |

**These strings are the ground truth. Use them verbatim.** Do not re-read a label off the crop when `text` already gives it, and never "tidy" a unit, a gene name or a group label into something that reads better. Open `images/<id>.png` with the Read tool (up to about six per turn) for what only the picture can tell you: the graphic type, the shape and direction of the data, which series is which, and what the panels show.

Then replace the matching `<!-- MDC:FIG:<id> -->` placeholder so the block reads:

```
![Fig 2](images/fig-p03-02.png)

_<u>Fig 2. Confocal images of RVFV antigen in ovarian tissue.</u>_

**Figure description.** Two to six sentences: what kind of graphic it is, the axes with their units as printed, the series or groups, the direction and size of the main effect, and any statistics printed on the plot. Describe a multi-panel figure panel by panel, using the letters in `panels`.
```

Rules for the description:

- State the axis scale when `ticks` gives it, and say `log` when it is log. Reading a log axis as linear is the error that moves a value by an order of magnitude.
- Report only values that are printed. A bar height read off the picture is not a value, so describe the pattern ("about a third higher") rather than inventing a number.
- Check the description against `caption` and `cited_by` before you write it. If the picture seems to contradict what the authors say about it, keep the description factual and add the disagreement to the repair list, never to the Markdown.
- Keep a list of what you could not read (an illegible tick row, a legend hidden behind ink, an unresolvable panel). It goes in the log in step 8 as `unreadable`. Saying nothing is worse than saying a label could not be read.
- For a graphical abstract or infographic, transcribe its labels in reading order, from `text` where possible.
- If a faint watermark still shows across a crop, ignore it: describe the figure only, and never mention the watermark.

If a crop is blank, or is clearly a fragment of a figure, or duplicates another, delete the PNG, remove its link and placeholder, and add it to the repair list for step 6.

### 5. Formula pass

For each entry in `equations`, read `equations/<id>.png` and replace `<!-- MDC:EQ:<id> -->` with display LaTeX:

```
$$
\mathcal{L} = \frac{1}{N}\sum_{i=1}^{N} (y_i - \hat{y}_i)^2 \tag{1}
$$
```

Keep the printed equation number with `\tag{n}`. Leave inline math inside sentences as it is unless it is garbled. Delete the `equations/` folder afterwards; keep only a PNG for a formula you could not read, and link it in place.

### 6. Repair pass

Work through `warnings` in `_worklist.json`, plus anything you flagged in step 4.

Render the pages involved and look at them:

```bash
python3 -c "import pymupdf,sys; d=pymupdf.open(sys.argv[1]); [d[i-1].get_pixmap(dpi=140).save(f'page{i}.png') for i in [3,7]]" "<input.pdf>"
```

- Caption count above image count: crop the missing figure yourself with `page.get_pixmap(clip=pymupdf.Rect(x0,y0,x1,y1), dpi=220, annots=False)`, save it into `images/`, and insert the link plus description at the right anchor.
- Caption count above table count: transcribe the missed table from the page image as a pipe table.
- Reference gaps: open the reference pages and insert the missing entries at their numbered positions.

Never invent content. If the PDF does not show it, leave it out and record it in the log.

### 7. Verify before delivering

```bash
grep -c "MDC:" "<slug>.md"                      # must be 0
grep -o "images/[^)]*" "<slug>.md" | sort -u    # each must exist in images/
ls images/                                      # each must be linked
grep -c "^# " "<slug>.md"                        # must be 1
python3 -c "import json,sys; w=json.load(open('_worklist.json'))['watermarks']['samples']; md=open(sys.argv[1]).read(); print([s for s in w if s in md])" "<slug>.md"   # must print []
```

Then confirm by eye: page 1 and the most figure-heavy page rendered as images, read side by side with the Markdown. Check reading order, paragraph integrity, caption formatting, table column counts, reference sequence, and that no running head, page number or watermark survived.

### 8. Package and deliver

- Final folder `<slug>/` holds `<slug>.md` and `images/`.
- Write `<slug>_conversion_log.md` beside the folder: source filename, page count, counts of figures, tables, equations and references, what was stripped as page chrome and front matter, the watermarks removed (from `watermarks` in the worklist), row-label columns recovered, an `unreadable` section listing everything in a figure or formula you could not read, and every unresolved warning. Nothing of this goes inside the Markdown.
- Delete `_worklist.json`.
- Zip it: `cd <workdir> && zip -qr <slug>.zip <slug> <slug>_conversion_log.md`, copy the zip to the outputs directory, then deliver it.
- If the user has a connected folder, write the folder files back into it as well.
- Report in one or two sentences: where the folder landed, and the counts.

## Hard cases

If the layout defeats this pipeline (vertical CJK text, heavily rotated tables, dense chemistry schemes), MinerU is the fallback, on request:

```bash
pip install uv && uv pip install -U "mineru[all]"
mineru -p "<input.pdf>" -o mineru_out -b pipeline
```

It downloads about 1 to 2 GB of models and takes several minutes on CPU. Reformat its Markdown to this skill's output contract before delivering; do not hand over MinerU's raw output.

## Notes on the engine

- Reading order is a recursive XY-cut: a vertical cut is only possible where no block crosses the gutter, so a full-width title or banner is emitted before the columns below it. Watermarks are removed before layout, so a diagonal stamp can never block a column cut.
- Declared watermarks (`/Artifact /Watermark` marked content and watermark layers) are cut out of the page content in memory, so they vanish from text and from figure crops alike. Undeclared ones are removed from the text span by span.
- A `find_tables` candidate that contains curves or diagonal strokes, or that is mostly empty and mostly graphics, is treated as a chart and cropped as a figure. This is what stops plots from being flattened into fake pipe tables.
- Figure panels that share one caption are unioned into a single image, so a multi-panel figure stays one file.
- The text printed inside a figure is collected from the PDF, not from the crop: tick labels, axis titles, legend entries, panel letters and plot annotations, with their boxes. The collection box is padded, because tick labels usually sit just outside the drawing, and a rotated string inside a figure is read as an axis title rather than treated as a watermark. Those label blocks are then kept out of the prose flow, so stray axis numbers no longer appear as one-line paragraphs.
- A tick row is accepted only when at least three numeric labels run one way across the axis, and the scale is decided by measuring which of linear or log fits the tick positions. Numbers inside a diagram, such as layer widths, produce no axis.
- The `warnings` list is the repair worklist. Caption counts are compared against extracted assets, and the reference sequence is checked for gaps, so systematic misses surface instead of passing silently.
