#!/usr/bin/env python3
"""
Smoke tests for scripts/mdconvert_extract.py against a generated fixture.

    python3 -m unittest discover -s tests -v
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXTRACT = os.path.join(ROOT, "scripts", "mdconvert_extract.py")
MAKE_FIXTURE = os.path.join(ROOT, "tests", "make_fixture.py")


def run(args):
    return subprocess.run([sys.executable] + args, capture_output=True, text=True)


class TwoColumnArticle(unittest.TestCase):
    """The fixture is a two-column article with known ground truth."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="mdconvert-")
        cls.pdf = os.path.join(cls.tmp, "fixture.pdf")
        cls.out = os.path.join(cls.tmp, "out")
        r = run([MAKE_FIXTURE, cls.pdf])
        assert r.returncode == 0, r.stderr
        r = run([EXTRACT, cls.pdf, cls.out])
        assert r.returncode == 0, r.stderr
        with open(os.path.join(cls.out, "fixture.md"), encoding="utf-8") as f:
            cls.md = f.read()
        with open(os.path.join(cls.out, "_worklist.json"), encoding="utf-8") as f:
            cls.work = json.load(f)

    def test_single_h1_is_the_title(self):
        h1 = re.findall(r"^# (.+)$", self.md, re.M)
        self.assertEqual(len(h1), 1)
        self.assertIn("Layout aware conversion", h1[0])

    def test_page_chrome_removed(self):
        self.assertNotIn("Journal of Synthetic Vector Biology", self.md)
        self.assertNotIn("Vol. 12, No. 3", self.md)
        self.assertNotRegex(self.md, r"(?m)^\s*\d\s*$")

    def test_column_reading_order(self):
        """Left column must be emitted before the right column of the same band."""
        left = self.md.index("Arboviral surveillance depends")
        right = self.md.index("Vector competence was summarised")
        self.assertLess(left, right)
        methods = self.md.index("The proportion of positive tissues rose")
        figure = self.md.index("Fig 1. Disseminated infection")
        self.assertLess(methods, figure)

    def test_paragraph_not_fragmented(self):
        """A body paragraph survives as one block, not as broken lines."""
        para = [b for b in self.md.split("\n\n") if b.startswith("Arboviral surveillance")]
        self.assertEqual(len(para), 1)
        self.assertTrue(para[0].rstrip().endswith("ground truth."))

    def test_captions_italic_and_underlined(self):
        self.assertRegex(self.md, r"_<u>Fig 1\..*</u>_")
        self.assertRegex(self.md, r"_<u>Table 1\..*</u>_")

    def test_table_is_a_markdown_table(self):
        self.assertIn("| Day | Tested | Positive |", self.md)
        self.assertIn("| 28 | 25 | 22 |", self.md)
        self.assertGreaterEqual(self.work["tables"], 1)

    def test_figure_extracted_and_linked(self):
        self.assertEqual(len(self.work["figures"]), 1)
        link = re.search(r"!\[[^\]]*\]\((images/[^)]+)\)", self.md)
        self.assertIsNotNone(link)
        self.assertTrue(os.path.exists(os.path.join(self.out, link.group(1))))

    def test_equation_placeholder_emitted(self):
        self.assertIn("<!-- MDC:EQ:", self.md)
        self.assertEqual(len(self.work["equations"]), 1)
        self.assertTrue(os.path.exists(
            os.path.join(self.out, self.work["equations"][0]["file"])))

    def test_references_numbered_and_sequential(self):
        tail = self.md[self.md.index("## References"):]
        nums = [int(n) for n in re.findall(r"(?m)^(\d+)\. ", tail)]
        self.assertEqual(nums, [1, 2, 3, 4])
        self.assertIn("Wilson EB. Probable inference", tail)

    def test_no_reference_number_invented(self):
        self.assertEqual(self.work["reference_range"], [1, 4])


class ScannedPdf(unittest.TestCase):
    def test_image_only_pdf_is_refused(self):
        import pymupdf
        tmp = tempfile.mkdtemp(prefix="mdconvert-scan-")
        pdf = os.path.join(tmp, "scan.pdf")
        doc = pymupdf.open()
        page = doc.new_page()
        pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 600, 800))
        pix.clear_with(210)
        page.insert_image(page.rect, pixmap=pix)
        doc.save(pdf)
        doc.close()

        r = run([EXTRACT, pdf, os.path.join(tmp, "out")])
        self.assertEqual(r.returncode, 3)
        self.assertTrue(json.loads(r.stdout.strip().splitlines()[-1])["scanned"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
