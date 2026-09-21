# Limitations

The short list is in the README. This is the long form, with the reason and the workaround for each.

## Scanned and image-only PDFs

**Refused by design.** A PDF averaging fewer than 120 characters per page over its first twelve pages exits with code 3 and writes nothing.

*Why:* every downstream decision in this pipeline reads the text layer's geometry: font size, block boundaries, baseline direction. With no text layer there is nothing to reason over, and an OCR pass bolted on in front would produce a plausible-looking file whose errors are invisible to the reader.

*Workaround:* OCR the document yourself (`ocrmypdf --force-ocr in.pdf out.pdf`) and convert the result. Accuracy then depends on the OCR, and the reference and formula passes in particular will need heavier repair.

## Layouts outside the target range

Tuned for one and two-column scientific articles in Latin script on A4 or US Letter.

Out of scope: vertical CJK text, right-to-left scripts, three or more columns with unequal widths, newspaper layouts, slide decks exported to PDF, posters, and dense chemistry schemes where structures and text are interleaved at small scale.

*Why:* the XY-cut gutter threshold and the caption regular expressions encode assumptions about column geometry and English caption prefixes.

*Workaround:* MinerU (`mineru -p in.pdf -o out -b pipeline`) handles a wider range of scripts and layouts. Reformat its output to the output contract before using it.

## Small vector figures

A diagram drawn as a few vector strokes covering less than about 1.2 percent of the page may not be detected as a figure.

*Why:* the same threshold that catches a small inline diagram also catches horizontal rules, logos, table borders and decorative marks, and a file full of spurious crops is worse than one missing figure.

*Detection:* the caption count check reports it as `figure captions=N but figure images=M`.

*Workaround:* the repair pass crops it by hand from the page image. To change the default, lower the vector cluster minimum in the per-page section of the extractor.

## Complex tables

Merged cells, spanning or nested headers, multi-row stubs, and tables continued across a page break are flattened or partially recovered. A table whose columns are separated only by whitespace, with no ruling and inconsistent alignment, may not be detected at all.

*Why:* the detector returns a rectangular grid. Rectangular grids cannot express a merged cell, and nothing in the geometry says that the grid on page 4 continues the grid on page 3.

*Detection:* the table caption count check.

*Workaround:* the repair pass transcribes the table from the page image. For a table that matters, check the column count and the header row by eye before using the numbers.

## Formulas

Display equations are converted from a rendered crop, which is reliable for ordinary inline-sized mathematics and unreliable for long multi-line derivations, matrices, commutative diagrams and expressions with heavy annotation above and below the line.

Inline mathematics inside a sentence is left as extracted text, which means Unicode symbols and italic variable names, not LaTeX.

*Why:* PDF carries glyph positions, not mathematical structure. Reconstructing structure from positions is the same problem as reading the image, so the image is read instead.

*Workaround:* a formula that cannot be read confidently is kept as a PNG and linked. Check every converted formula that will be reused in a manuscript.

## Reference styles

Numbered styles (`[1]`, `1.`) are handled well. Author-year bibliographies with no numbers fall back to splitting on block boundaries, which merges two short entries when the PDF puts them in one block, and splits one entry when the PDF breaks it across a column.

*Why:* without numbers there is no unambiguous separator. Splitting on "surname, initial" patterns produces more errors than it fixes.

*Detection:* the log records `references had no reliable numbering; numbered by block order`.

*Workaround:* check the reference count against the PDF. For a bibliography that matters, export it from the publisher or a reference manager instead of recovering it from the layout.

## What is not checked at all

- **Meaning.** The tool preserves what the PDF says. It does not verify claims, resolve citations to a database, or reconcile numbers in the text with numbers in the tables.
- **Completeness against the publisher's version.** Supplementary files, interactive content, embedded video, and anything living outside the PDF are not fetched.
- **Accessibility metadata.** Alt text is the figure description; it is not derived from the PDF's tagged structure, which is often absent or wrong in scientific PDFs anyway.

## Operational limits

- One document per run, interactively. There is no unattended batch queue.
- The figure and formula passes need a vision model, so the command line alone stops at the placeholders.
- Memory and time scale with page count and figure count. A 40-page review with 30 figures is slow, mostly in the vision passes.
- Figure descriptions describe. They are not a substitute for the underlying data, and they should not be quoted as if they were measurements.
