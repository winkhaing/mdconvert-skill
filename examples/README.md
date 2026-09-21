# Examples

## two-column-article.md

The finished conversion of the test fixture, after all three stages.

The source is generated, not borrowed: `tests/make_fixture.py` draws a two-page, two-column article with a running header, a page number on every page, a title band spanning both columns, a display equation, a bar chart with its caption, a ruled table with its caption, and a numbered reference list. Nothing from a published paper is redistributed here.

Regenerate it:

```bash
python3 tests/make_fixture.py /tmp/fixture.pdf
python3 scripts/mdconvert_extract.py /tmp/fixture.pdf /tmp/out
```

`/tmp/out/fixture.md` is the deterministic stage. It matches this example except for two placeholders:

- `<!-- MDC:EQ:eq-001 -->` becomes the `$$ ... $$` block, written by the formula pass
- `<!-- MDC:FIG:fig-p01-01 -->` becomes the **Figure description** paragraph, written by the figure pass

Both passes need a vision model, so the command line alone stops at the placeholders. That is the intended behaviour, not a failure.

## What to look for

| In the source PDF | In the Markdown |
| --- | --- |
| `Journal of Synthetic Vector Biology \| Vol. 12, No. 3, 2026` on every page | absent |
| page numbers 1 and 2 centred in the footer | absent |
| title spanning both columns | single `#` heading, emitted before either column |
| Abstract in column 1, Introduction in column 2 | Abstract in full, then Introduction in full, not interleaved |
| bar chart drawn as vector strokes | `images/fig-p01-01.png`, cropped without its caption |
| caption below the chart | `_<u>Fig 1. ...</u>_`, italic and underlined |
| ruled table in column 2 of page 2 | pipe table with the header row preserved |
| `p = k / n x 100  (1)` set in italic | `$$ p = \frac{k}{n} \times 100 \tag{1} $$` |
| four references numbered 1 to 4 | four numbered lines, same numbers |
