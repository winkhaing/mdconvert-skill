# Troubleshooting

Symptom, cause, fix. Most fixes are a threshold at the top of `scripts/mdconvert_extract.py` or in its per-page section.

## Installation and running

**`ModuleNotFoundError: No module named 'pymupdf'`**
`pip install -r requirements.txt`. On a system-managed Python, add `--break-system-packages` or use a virtual environment.

**`import fitz` deprecation warning**
Harmless, and it comes from another package. This extractor imports `pymupdf` directly.

**"Consider using the pymupdf_layout package" on stderr**
An upstream notice, not an error. The summary JSON is on stdout, so parse stdout alone: `python3 scripts/mdconvert_extract.py in.pdf out 2>/dev/null | jq .`

**Exit code 3 on a PDF that clearly has text**
The text layer is behind an image overlay, or the pages are images with a thin OCR layer. Check with `python3 -c "import pymupdf; print(len(pymupdf.open('in.pdf')[0].get_text()))"`. If the count is genuinely low but the document is usable, lower the 120 characters per page gate in the scanned check.

**The skill does not appear in Claude**
For a filesystem install the folder must be `~/.claude/skills/mdconvert/` with `SKILL.md` at its top level, and the client needs a restart. For an uploaded bundle, check that the zip contains `mdconvert/SKILL.md` and not `SKILL.md` at the archive root.

## Reading order and text

**Columns interleaved**
The gutter was not detected, usually because a figure, a table or a wide equation spans both columns and no vertical whitespace runs the full height of that band. Raise or lower `gutter_min`, currently `max(11, 0.022 * page width)`. A narrow gutter with wide word spacing is the common cause.

**A single-column page split into two**
`gutter_min` is too small for a layout with wide internal spacing, such as a definition list or a table of contents. Raise it.

**Paragraphs broken into fragments**
The PDF emits one block per line, which happens with some typesetting engines. The rejoin pass repairs continuations, not wholesale fragmentation. Check whether the fragments are separate blocks in `page.get_text("dict")`; if so, the file needs a pre-merge step and is worth an issue with the DOI.

**Running head still present**
It changes between sections, so it never reaches the 35 percent recurrence threshold. Lower the threshold in the page chrome pass, or remove it in the repair pass.

**Text missing from the output**
Most often it was inside a figure crop and dropped as an axis label, or inside a table bbox. Search `_worklist.json` for that page, and compare the crop against the page image. The figure text-coverage check (`cov > 0.78`) and the prose check (`nchar > 130`) exist to prevent this; if a body paragraph was swallowed, the figure region was wrong.

## Figures

**A figure is missing**
Below the vector cluster size threshold, or its caption prefix was not recognised. The caption count warning flags it. Lower the cluster minimum, or crop it in the repair pass.

**One figure came out as several images**
The panels did not share a detected caption, so they were not grouped. Check that the caption sits within 130 points of the panels and overlaps them horizontally.

**The crop includes the caption**
The caption block was not recognised as a caption, so it was not excluded. Check the caption prefix against `CAPTION_RE`. Non-English prefixes such as "Abbildung" or "Figura" need adding.

**The crop is blank or nearly blank**
A drawing cluster of invisible or white strokes. Delete it in the repair pass. The blank check only catches uniformly coloured crops.

## Tables

**A plot came out as a table**
Text coverage inside the region was above 0.40, which happens with a dense legend or many annotations. Raise the threshold.

**A real table came out as a figure**
Text coverage was below 0.40, which happens with a sparse numeric table and wide cells. Lower the threshold.

**The stub column is missing**
The detector did not include the row-label column in the grid, usually because it is unruled. Transcribe the table in the repair pass.

**A table split across pages appears twice, partially**
Expected. Join them by hand; this is on the roadmap.

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

Open a conversion issue with the DOI or a link to the open-access PDF, the page and region, what the output looked like, what it should have been, and the `warnings` array from `_worklist.json`. Please do not attach paywalled files.
