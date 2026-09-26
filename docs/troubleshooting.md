# Troubleshooting

Symptom, cause, fix. Most fixes are a threshold in `scripts/mdconvert_extract.py`.

## Installation and running

**`ModuleNotFoundError: No module named 'pymupdf'`**
`pip install -r requirements.txt`. On a system-managed Python, add `--break-system-packages` or use a virtual environment.

**"Consider using the pymupdf_layout package" on stderr**
An upstream notice, not an error. The summary JSON is on stdout, so parse stdout alone: `python3 scripts/mdconvert_extract.py in.pdf out 2>/dev/null | jq .`

**Exit code 3 on a PDF that clearly has text**
The text layer is behind an image overlay, or the pages are images with a thin OCR layer. Check with `python3 -c "import pymupdf; print(len(pymupdf.open('in.pdf')[0].get_text()))"`. If the count is genuinely low but the document is usable, lower the 120 characters per page gate in the scanned check.

**Exit code 4**
The PDF has a user password. Rerun with `--password "..."`. A PDF that only restricts printing or copying (an owner password) opens without one and does not trigger this.

**Exit code 5**
The file is not a PDF (often an HTML error page saved with a `.pdf` name by a download that failed), or it is truncated. Check with `file in.pdf` and download it again.

**The skill does not appear in Claude**
For a filesystem install the folder must be `~/.claude/skills/mdconvert/` with `SKILL.md` at its top level, and the client needs a restart. For an uploaded bundle, check that the zip contains `mdconvert/SKILL.md` and not `SKILL.md` at the archive root.

## Watermarks

**A watermark is still in the Markdown**
Check which kind it is. Open the page in a viewer: if the stamp is horizontal, opaque, normal-sized and appears on one page only, none of the rules applies to it. Remove it in the repair pass, and open a conversion issue with the DOI so a rule can be added.

**A watermark is still visible inside a figure image**
The watermark is not declared by the PDF, so its ink cannot be separated from the figure's. The text is still kept out of the Markdown. If the crop matters, re-crop it from a copy of the PDF with the watermark removed in a PDF editor.

**Genuine text disappeared**
Look under `watermarks` in `_worklist.json`: `text_removed` counts every span removed by reason, and `samples` shows examples. A light-grey banner heading points to the large light rule (raise the 2.5 times body size factor); a label repeated in the same place on every page points to the recurrence rule (raise the 60 percent share); a rotated table header points to the rotation rule, which cannot be relaxed without letting diagonal stamps back in, so restore it in the repair pass.

**A logo or stamp appears as a figure**
It recurred on fewer than 60 percent of pages, or at slightly different positions. Delete the crop and its link in the repair pass.

## Reading order and text

**Columns interleaved**
The gutter was not detected, usually because a figure, a table or a wide equation spans both columns and no vertical whitespace runs the full height of that band. Raise or lower `gutter_min`, currently `max(11, 0.022 * page width)`. A narrow gutter with wide word spacing is the common cause.

**A single-column page split into two**
`gutter_min` is too small for a layout with wide internal spacing, such as a definition list or a table of contents. Raise it.

**Paragraphs broken into fragments**
The PDF emits one block per line and the lines end with full stops, which happens with some typesetting engines. The rejoin pass repairs continuations that end mid-sentence. Check whether the fragments are separate blocks in `page.get_text("dict")`; if so, the file needs a pre-merge step and is worth an issue with the DOI.

**A compound lost its hyphen, or a split word kept one**
The document's vocabulary decides first. Add the first element to `COMPOUND_FIRST` to keep hyphens it forms, or check whether the unhyphenated spelling occurs elsewhere in the paper.

**Running head still present**
It changes between sections, so it never reaches the recurrence threshold. Lower the threshold in the page chrome pass, or remove it in the repair pass.

**Text missing from the output**
Most often it was inside a figure crop and dropped as an axis label, inside a table bbox, or removed as a watermark or front-matter notice. Search `_worklist.json` for that text under `watermarks` and `front_matter_removed`, and compare the crop against the page image.

## Figures

**A figure is missing**
Below the vector cluster size threshold and with no caption within 60 points, or its caption prefix was not recognised. The caption count warning flags it. Lower the cluster minimum, or crop it in the repair pass.

**One figure came out as several images**
The panels did not share a detected caption, so they were not grouped. Check that the caption sits within 130 points of the panels and overlaps them horizontally.

**The crop includes the caption**
The caption block was not recognised as a caption, so it was not excluded. Check the caption prefix against `CAPTION_RE`. Non-English prefixes such as "Abbildung" or "Figura" need adding.

**`text_items` is 0 for a figure that clearly has labels**
The figure is an embedded raster image, so there is no text to read. Describe it from the crop. If the figure is vector but the labels still did not appear, they sit further out than the collection pad (10 to 26 points, 10 percent of the figure), or they fall inside a neighbouring prose block's box, which is excluded on purpose.

**A tick row was not detected**
Fewer than three numeric labels, or they do not run one way across the axis, or they span less than a quarter of it. Two-tick axes and axes labelled only at their ends are missed by design.

**`scale` says `unknown`**
The tick values are not monotonic in position, usually because several panels share a row and their runs were interleaved. The longest single run is reported as the axis and `repeats` counts the runs; read the panels individually from the crop.

**An axis title is wrong or missing**
The y title is the longest rotated string in the figure, and is only claimed when the figure holds at most eight rotated strings. An attention map or correlation matrix therefore reports no title, which is intended. The x title is the first non-numeric line below the x tick row, near the horizontal centre; a title set flush left is missed.

**A short line near a figure disappeared from the Markdown**
It was taken as a figure label. That needs all three: inside the figure's padded box, under 50 characters, and no larger than the body font. Raise the size test if a small subheading beside a figure is being swallowed.

**The crop is blank or nearly blank**
A drawing cluster of invisible or white strokes. Delete it in the repair pass. The blank check only catches uniformly coloured crops.

## Tables

**A plot came out as a table**
The plot has no curves or diagonal strokes (a bar chart drawn only with rectangles) and most of its grid cells hold text. Delete it in the repair pass and crop the chart as a figure.

**A real table came out as a figure**
Its cells are mostly empty and it covers little text, or it contains diagonal rules. Transcribe it in the repair pass.

**The row-label column is missing**
The labels are not left-aligned within 25 points of each other, sit more than 80 points from the grid, or fewer than half of the body rows have one. Transcribe the table in the repair pass.

**A table split across pages appears twice, partially**
Expected. Join them by hand; this is on the roadmap.

**A borderless table is missing**
Expected for tables set with whitespace alone. The caption count warning flags it; transcribe it from the page image.

## References

**Far fewer references than the PDF has**
The number sequence broke early. Sequential matching accepts a number only in ascending order and within three of the previous one. If an entry's first line was lost, the sequence stalls. Check `reference_range` in `_worklist.json` against the last number in the PDF.

**Reference entries merged into one long line**
The bibliography is unnumbered and the fallback split on block boundaries. Check the log for `numbered by block order`.

**An appendix ended up inside the reference list**
The post-reference heading was not recognised. Add its wording to `POST_REF_HEAD_RE`.

## Output quality

**Placeholders left in the delivered file**
`grep -c "MDC:" file.md` must return 0. The figure or formula pass was not completed; run it.

**Headings at the wrong level**
Level assignment uses document-wide font size clusters. A document that uses the same size for sections and subsections, distinguished only by numbering or colour, will flatten. Fix in the repair pass.

**The title is wrong or missing**
The title is the largest text block on page 1 above the body size. A cover page, a large journal banner or a full-page graphical abstract can outrank it. Set the `#` heading by hand.

## Reporting a problem

Open a conversion issue with the DOI or a link to the open-access PDF, the page and region, what the output looked like, what it should have been, and the `warnings` and `watermarks` entries from `_worklist.json`. Please do not attach paywalled files.
