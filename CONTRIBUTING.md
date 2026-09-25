# Contributing

Thanks for taking the time. Conversion bugs are the most valuable contribution: every real layout that breaks the pipeline is a rule that needs fixing.

## Reporting a conversion problem

Open an issue using the **Conversion issue** template and include:

- the DOI, or a link to an **open-access** PDF (please do not attach paywalled files)
- the page and the region: which column, which figure, which table
- what the output looked like, and what it should have been
- the `warnings` array from `_worklist.json`
- Python version, PyMuPDF version, operating system

## Development setup

```bash
git clone https://github.com/winkhaing/mdconvert-skill.git
cd mdconvert-skill
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 -m unittest discover -s tests -v
```

## Ground rules for changes

1. **Fix the general rule, not the document.** A change conditioned on a publisher name, a title string or a specific page number will be declined. If a rule cannot be made general, it belongs in the repair pass, not in the extractor.
2. **Add a fixture case.** A layout behaviour that was wrong should become a test. Extend `tests/make_fixture.py` with the smallest page construct that reproduces it (the English fixture in `build`, the Chinese one in `build_cjk`), and assert the corrected output in `tests/test_extractor.py`. The fixture is generated, so no third-party document is ever committed.
3. **Never remove content silently.** Anything a rule strips (watermarks, notices, furniture) must be counted and sampled in the worklist so it can be reviewed.
4. **Never invent content.** No inferred values, no renumbered references to close a gap, no reconstructed table cells. When something cannot be recovered, it belongs in `warnings` so the repair pass can see it.
5. **Prefer a warning to a silent guess.** If a heuristic fires at low confidence, emit the conservative output and record the doubt.
6. **Keep the output contract.** Changes that alter caption formatting, heading rules, reference numbering or the placeholder syntax need a matching update to `docs/output-contract.md`, the tests, and `SKILL.md`.
7. **Keep `SKILL.md` and the extractor in step.** The single-file build inlines the extractor into the skill, so a change to either may need `python3 scripts/build_single_file_skill.py` re-run.

## Style

- Standard library plus PyMuPDF only. New runtime dependencies need a reason.
- Python that reads plainly: descriptive names, short functions, a comment on every threshold explaining what it protects against.
- Thresholds go at the top of their section as named values, not buried in an expression.
- No em-dashes in documentation prose.

## Pull requests

- One concern per pull request.
- Tests pass on the supported Python versions (CI runs 3.9 to 3.12).
- Say in the description which real documents you checked the change against, and what the counts were before and after.
