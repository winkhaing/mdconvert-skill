#!/usr/bin/env python3
"""
Build a self-contained SKILL.md with the extractor inlined.

Some skill interfaces accept a single file rather than a folder. This script
takes SKILL.md plus scripts/mdconvert_extract.py and writes dist/SKILL.single.md,
in which the extractor is an appendix the agent writes to disk before running.

    python3 scripts/build_single_file_skill.py
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(ROOT, "SKILL.md")
EXTRACT = os.path.join(ROOT, "scripts", "mdconvert_extract.py")
OUT = os.path.join(ROOT, "dist", "SKILL.single.md")

BUNDLED = "The extractor ships with this skill at `scripts/mdconvert_extract.py`."
INLINED = ("Write the extractor from the appendix at the end of this file to "
           "`mdconvert_extract.py` in your working directory.")


def main():
    with open(SKILL, encoding="utf-8") as f:
        skill = f.read()
    with open(EXTRACT, encoding="utf-8") as f:
        code = f.read()

    if BUNDLED not in skill:
        sys.exit("anchor sentence not found in SKILL.md; update BUNDLED in this script")

    skill = skill.replace(BUNDLED, INLINED)
    skill = skill.replace("python3 scripts/mdconvert_extract.py",
                          "python3 mdconvert_extract.py")
    skill = skill.rstrip() + "\n\n## Appendix: the extractor\n\n```python\n" + code.rstrip() + "\n```\n"

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(skill)
    print(f"wrote {OUT} ({len(skill):,} characters)")


if __name__ == "__main__":
    main()
