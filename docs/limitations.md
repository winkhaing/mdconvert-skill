# Limitations

The short list is in the README. This is the long form, with the reason and the workaround for each.

## Scanned and image-only PDFs

**Refused by design.** A PDF averaging fewer than 120 characters per page over its first twelve pages exits with code 3 and writes nothing.

*Why:* every downstream decision in this pipeline reads the text layer's geometry: font size, block boundaries, baseline direction. With no text layer there is nothing to reason over, and an OCR pass bolted on in front would produce a plausible-looking file whose errors are invisible to the reader.

*Workaround:* OCR the document yourself (`ocrmypdf --force-ocr in.pdf out.pdf`) and convert the result. Accuracy then depends on the OCR, and the reference and formula passes in particular will need heavier repair.

## Layouts outside the target range

Tuned for one and two-column scientific articles on A4 or US Letter, in Latin script or horizontal Chinese.

Out of scope: vertical CJK text, right-to-left scripts, three or more columns with unequal widths, newspaper layouts, slide decks exported to PDF, posters, and dense chemistry schemes where structures and text are interleaved at small scale. Japanese and Korean share the Chinese line-joining rule but have no caption or section vocabulary yet.

*Why:* the XY-cut gutter threshold and the caption and section vocabularies encode assumptions about column geometry and label words.

*Workaround:* MinerU (`mineru -p in.pdf -o out -b pipeline`) handles a wider range of scripts and layouts. Reformat its output to the output contract before using it.

## Watermarks

**Declared watermarks** (`/Artifact <</Subtype /Watermark>>` marked content, and content on a watermark layer) are removed exactly: from the text and from every figure crop.

**Undeclared watermarks** are removed from the text by rule: rotated, transparent, large and light, on a watermark layer, or recurring at one position. Two consequences follow.

- *Ink can remain in a crop.* When an undeclared transparent stamp is drawn across a chart, the stamp's pixels cannot be separated from the chart's own. The text never reaches the Markdown; a faint trace may remain in that figure's PNG. The figure pass is instructed to ignore it.
- *A rule can catch genuine text.* A heading printed in very large light grey, deliberately transparent text, or a label repeated at the identical position on most pages would be removed. Rotated table headers and rotated axis labels outside figures are also dropped. Everything removed is counted and sampled in the worklist and the conversion log, so it can be reviewed.

*Workaround:* if genuine text went missing, find it under `watermarks` in the worklist, and raise the matching threshold (see Tuning in the README) or restore the text in the repair pass.

## Small vector figures

A diagram covering less than 1.2 percent of the page is taken only when a figure caption sits within 60 points of it. A small uncaptioned diagram is still missed.

*Why:* the same threshold that catches a small inline diagram also catches horizontal rules, logos, table borders and decorative marks, and a file full of spurious crops is worse than one missing figure.

*Detection:* the caption count check reports `figure captions=N but figure images=M`.

*Workaround:* the repair pass crops it by hand from the page image.

## Tables

**Borderless tables are often missed.** A table set with whitespace alone and no rules may not be found by the grid detector. In validation, the Transformer paper yielded 2 of its 4 tables and ResNet 13 of 14.

**Complex tables lose structure.** Merged cells, spanning or nested headers, multi-row stubs, and tables continued across a page break are flattened or partially recovered.

*Why:* the detector returns a rectangular grid built from rules. Rectangular grids cannot express a merged cell, nothing in the geometry says that the grid on page 4 continues the grid on page 3, and without rules there may be no grid at all.

*Detection:* the table caption count check.

*Workaround:* the repair pass transcribes the table from the page image. For a table that matters, check the column count and the header row by eye before using the numbers.

## Formulas

Display equations are converted from a rendered crop, which is reliable for ordinary mathematics and unreliable for long multi-line derivations, matrices, commutative diagrams and expressions with heavy annotation above and below the line.

Inline mathematics inside a sentence is left as extracted text, which means Unicode symbols and italic variable names, not LaTeX.

*Why:* PDF carries glyph positions, not mathematical structure. Reconstructing structure from positions is the same problem as reading the image, so the image is read instead.

*Workaround:* a formula that cannot be read confidently is kept as a PNG and linked. Check every converted formula that will be reused in a manuscript.

## Hyphenation

A line-end hyphen is resolved from the document's own vocabulary first, then from a short list of compound elements. When a word appears only once, broken across a line, and its first half is on the compound list, the hyphen is kept even if the author meant a single word ("non-" + "structural" stays "non-structural" unless "nonstructural" occurs elsewhere in the text).

## Reference styles

Numbered styles (`[1]`, `1.`) are handled well. Author-year bibliographies with no numbers fall back to splitting on block boundaries, which merges two short entries when the PDF puts them in one block, and splits one entry when the PDF breaks it across a column.

*Detection:* the log records `references had no reliable numbering; numbered by block order`.

*Workaround:* check the reference count against the PDF. For a bibliography that matters, export it from the publisher or a reference manager instead of recovering it from the layout.

## What is not checked at all

- **Meaning.** The tool preserves what the PDF says. It does not verify claims, resolve citations to a database, or reconcile numbers in the text with numbers in the tables.
- **Completeness against the publisher's version.** Supplementary files, interactive content, embedded video, and anything living outside the PDF are not fetched.
- **Accessibility metadata.** Alt text is the figure description; it is not derived from the PDF's tagged structure, which is often absent or wrong in scientific PDFs anyway.

## Operational limits

- One document per run, interactively. There is no unattended batch queue.
- The figure and formula passes need a vision model, so the command line alone stops at the placeholders.
- Memory and time scale with page count and figure count. The extractor itself takes about 3 to 4 seconds for a 12 to 15 page paper; the vision passes take longer.
- Figure descriptions describe. They are not a substitute for the underlying data, and they should not be quoted as if they were measurements.
