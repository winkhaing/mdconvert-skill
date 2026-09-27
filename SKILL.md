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

These rules are not negotiable. Check every one of them in step 8.

- One `#` title. Section headings use `##`, subsections `###`. Heading level comes from document-wide font evidence, applied consistently. Author names and affiliations under the title are plain text, never headings.
- Running heads, journal name, volume/issue lines, per-page DOI strips, copyright footers, page numbers, licence and permission notices, and journal metadata blocks (Citation, Editor, Received/Accepted, Copyright) are removed. So is a publisher's cover sheet, such as the Elsevier pre-proof front page carrying the banner, the PII and the citation notice.
- **Watermarks never reach the Markdown**: diagonal or rotated stamps, transparent text, text on a watermark layer, watermarks the PDF declares as such, large light-grey stamps such as DRAFT, text repeated at the same spot on every page, and recurring logo or stamp images.
- Reading order follows the columns, not the raster lines. Nothing from column 2 interleaves into column 1.
- A paragraph split by a figure, a table, a footnote, a column break or a page break is rejoined into one paragraph; the interrupting block is then placed after that paragraph, never inside it.
- Line-end hyphens are resolved: "classi-" + "fication" becomes "classification", while "high-" + "level" stays "high-level". Ligatures and TeX-style accents are repaired ("ﬁ" to "fi", "M¨uller" to "Müller").
- A section heading that the PDF ran into the body block (common in accepted manuscripts written in a word processor, where "References" is the fortieth line of a paragraph) is split back out into a heading of its own, so the section is found.
- No paragraph ends mid-sentence where the source does not. A block cut by the layout is rejoined to the next one even when the continuation begins with a capital, which it often does: an acronym, a trial name, a proper noun.
- Mathematics is left exactly as printed: a raised run in an expression is an exponent, not a marker, so "1/M" stays "1/M". Display equations still go through the formula pass in step 6.
- Greek from an unmapped Symbol font is repaired ("a", "b", "q" become alpha, beta, theta). A glyph with no Unicode mapping is dropped, counted under `glyphs` in the worklist, and warned about, never written into the file as a control character.
- Superscripts and subscripts are kept, not flattened: "ScD¹,⁴", "kg/m²", "CO₂", "previously.¹²", "Merative™". Unicode is the default because it renders everywhere, Notion included. `--sup-style latex` writes `$^{1,4}$` for Obsidian, Quarto or Pandoc, `html` writes `<sup>1,4</sup>` for GitHub, `plain` flattens. Whatever the style, do not retype a marker by hand in the repair pass.
- Figure and table captions are italic and underlined, exactly: `_<u>Figure 1. Caption as printed.</u>_`
- Tables are pipe tables, including a row-label column that sits outside the ruled grid. Never a screenshot of a table.
- Figures, infographics and graphical abstracts are saved as PNG in `images/` and linked relatively. A short description sits directly under each one, with every label, unit and printed statistic taken from the PDF's own text rather than read off the picture.
- Display formulas become `$$ ... $$` LaTeX.
- References are one numbered entry per line, carrying the PDF's own numbering, in the position where the reference section stands. Never invent a number that is not in the source.
- The Markdown body carries no editorial notes, no provenance text, no conversion commentary. All of that belongs in the separate log file written in step 9.
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

Superscripts and subscripts come out as Unicode by default, which is what the user wants unless they say where the file is going. Add `--sup-style latex` for Obsidian, Quarto or Pandoc, `html` for GitHub, `plain` to flatten. If the user later says the markers show as literal `$^{1,4}$` in Notion or Word, they are on `latex`: rerun on `unicode`.

| Exit | Meaning | What to do |
| --- | --- | --- |
| 0 | Converted | Continue with step 5 |
| 3 | Scanned or image-only PDF | Step 4 |
| 4 | Encrypted, password needed or wrong | Ask for the password, then rerun with `--password` |
| 5 | Not a PDF, or damaged | Tell the user the file cannot be opened and ask for another copy |
| 6 | Pre-proof or all-rights-reserved copy | Step 3: ask the user, then rerun with `--confirm-restricted` |

### 3. Restricted copy: ask before converting

Exit code 6 means the PDF is a journal pre-proof, an accepted manuscript, or carries an all-rights-reserved notice with no open licence. A full conversion reproduces the whole of a copyrighted article, so that is the user's call, not yours. Nothing has been written at this point.

Tell them what the file is, in one short message, using the `document` block the extractor printed: title, journal, DOI and status. Then ask whether to convert their copy for their own use.

- **Yes**: rerun the same command with `--confirm-restricted` and carry on from step 4.
- **No, or no answer**: do not convert. Offer what does not reproduce the work, such as a summary, the figure and table inventory, the reference list, or the specific numbers they need.

Do not question their access to the file and do not ask them to prove it. Say once, without lecturing, that the converted file is for their own use rather than for redistribution. An openly licensed article (`status: open-licence`, for example CC-BY) never reaches this step and converts straight through.

### 4. Scanned PDF: stop

On exit 3, do not OCR, do not deliver a partial file. Reply with one line:

> This is a scanned PDF with no text layer. Please provide the original (born-digital) PDF and I will convert it.

### 5. Figure pass

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
- Keep a list of what you could not read (an illegible tick row, a legend hidden behind ink, an unresolvable panel). It goes in the log in step 9 as `unreadable`. Saying nothing is worse than saying a label could not be read.
- For a graphical abstract or infographic, transcribe its labels in reading order, from `text` where possible.
- If a faint watermark still shows across a crop, ignore it: describe the figure only, and never mention the watermark.

If a crop is blank, or is clearly a fragment of a figure, or duplicates another, delete the PNG, remove its link and placeholder, and add it to the repair list for step 7.

### 6. Formula pass

For each entry in `equations`, read `equations/<id>.png` and replace `<!-- MDC:EQ:<id> -->` with display LaTeX:

```
$$
\mathcal{L} = \frac{1}{N}\sum_{i=1}^{N} (y_i - \hat{y}_i)^2 \tag{1}
$$
```

Keep the printed equation number with `\tag{n}`. Leave inline math inside sentences as it is unless it is garbled. Delete the `equations/` folder afterwards; keep only a PNG for a formula you could not read, and link it in place.

### 7. Repair pass

Work through `warnings` in `_worklist.json`, plus anything you flagged in step 5.

Render the pages involved and look at them:

```bash
python3 -c "import pymupdf,sys; d=pymupdf.open(sys.argv[1]); [d[i-1].get_pixmap(dpi=140).save(f'page{i}.png') for i in [3,7]]" "<input.pdf>"
```

- Caption count above image count: crop the missing figure yourself with `page.get_pixmap(clip=pymupdf.Rect(x0,y0,x1,y1), dpi=220, annots=False)`, save it into `images/`, and insert the link plus description at the right anchor.
- Caption count above table count: transcribe the missed table from the page image as a pipe table.
- Reference gaps: open the reference pages and insert the missing entries at their numbered positions.
- A paragraph that still ends mid-sentence: check it against the page image and join it. Run `grep -c "[a-z,]$" "<slug>.md"` for a quick count; a handful is normal (an email address, a URL ending a reference), dozens means the rejoin failed and is worth an issue with the DOI.
- A warning about dropped glyphs: open `glyphs.samples` in the worklist for the page and font, render that page, and type the missing symbols in by hand. Greek where Latin letters appear in a formula is the common case.
- A flat marker inside a table that the page's prose does not also carry ("kg/m2" where no sentence prints "kg/m²"): raise it by hand. Check `scripts.lines_marked` in the worklist first; zero on a document full of citation markers means the typesetter raised them without shrinking them, and none were detected.

Never invent content. If the PDF does not show it, leave it out and record it in the log.

### 8. Verify before delivering

```bash
grep -c "MDC:" "<slug>.md"                      # must be 0
grep -o "images/[^)]*" "<slug>.md" | sort -u    # each must exist in images/
ls images/                                      # each must be linked
grep -c "^# " "<slug>.md"                        # must be 1
python3 -c "import json,sys; w=json.load(open('_worklist.json'))['watermarks']['samples']; md=open(sys.argv[1]).read(); print([s for s in w if s in md])" "<slug>.md"   # must print []
```

Then confirm by eye: page 1 and the most figure-heavy page rendered as images, read side by side with the Markdown. Check reading order, paragraph integrity, caption formatting, table column counts, reference sequence, and that no running head, page number or watermark survived.

### 9. Package and deliver

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
- A pre-proof cover sheet is detected from the banner plus the PII or citation block and dropped whole, so its banner cannot win the title and its PII block cannot be emitted as body text.
- The title comes from the PDF's own metadata when that title appears in the text: the matching blocks are merged, which also repairs a title set over two lines. The size rule is the fallback.
- When every heading in a document is set in one size, as in an accepted manuscript, the standard sections sit at level 2 and the rest at level 3, since size gives no evidence.
- A caption whose figure sits alone on the next page, as in a manuscript with the figures appended, is matched to that page. A candidate band carrying almost no ink is discarded, so a faint watermark is not cropped as a figure.
- A line is treated as mathematics, and left untouched by the script pass, when it uses a mathematics font, carries two or more distinct mathematical symbols, or is short and built mostly of operators rather than words. An unmapped Symbol font is remapped from its own encoding, so Greek survives.
- A raised or lowered run is recognised from its type size and its baseline, because PDF carries no markup for either: under 13 characters, at most 0.82 times the line's dominant size, and at least a tenth of that size off its baseline, which leaves small capitals alone. Table cell text is rebuilt by the table extractor without span information, so each page's own substitutions are replayed into its cells with three characters of preceding context.
- A tick row is accepted only when at least three numeric labels run one way across the axis, and the scale is decided by measuring which of linear or log fits the tick positions. Numbers inside a diagram, such as layer widths, produce no axis.
- A reference list with no heading of its own is bounded by where the entries stop looking like entries: no number, no DOI, no year and volume, no URL, or the first table or figure. That is what stops the back matter being absorbed into the last entry.
- A bibliography whose numbering cannot be read is split on its hanging indent instead, the boundary a reader uses, and the log says so.
- The `warnings` list is the repair worklist. Caption counts are compared against extracted assets, and the reference sequence is checked for gaps, so systematic misses surface instead of passing silently.
