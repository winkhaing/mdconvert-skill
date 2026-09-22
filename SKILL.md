---
name: mdconvert
description: Convert a born-digital scientific PDF into clean Markdown with extracted figure images and descriptions, real Markdown tables, display LaTeX formulas and numbered references, with watermarks removed, delivered as a folder plus a zip.
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
- Figures, infographics and graphical abstracts are saved as PNG in `images/` and linked relatively. A short description written from the image sits directly under each one.
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

Read `_worklist.json`. For each entry in `figures`, open `images/<id>.png` with the Read tool (up to about six per turn), then replace the matching `<!-- MDC:FIG:<id> -->` placeholder in the Markdown so the block reads:

```
![Fig 2](images/fig-p03-02.png)

_<u>Fig 2. Confocal images of RVFV antigen in ovarian tissue.</u>_

**Figure description.** Two to six sentences: what kind of graphic it is, the axes and their units, the series or groups shown, the direction and size of the main effect, and any annotated statistics. Describe multi-panel figures panel by panel (A, B, C).
```

For a graphical abstract or infographic, also transcribe its text labels in reading order. Describe only what is legible. Never infer a value that is not printed or readable off the axis. If a faint watermark still shows across a crop, ignore it: describe the figure only, and never mention the watermark in the description.

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
- Write `<slug>_conversion_log.md` beside the folder: source filename, page count, counts of figures, tables, equations and references, what was stripped as page chrome and front matter, the watermarks removed (from `watermarks` in the worklist), row-label columns recovered, and every unresolved warning. Nothing of this goes inside the Markdown.
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
- The `warnings` list is the repair worklist. Caption counts are compared against extracted assets, and the reference sequence is checked for gaps, so systematic misses surface instead of passing silently.
