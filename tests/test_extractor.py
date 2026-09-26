#!/usr/bin/env python3
"""
Tests for scripts/mdconvert_extract.py against generated fixtures.

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
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "tests"))

import make_fixture  # noqa: E402
import mdconvert_extract as mx  # noqa: E402


def run(args):
    return subprocess.run([sys.executable, EXTRACT] + args, capture_output=True, text=True)


def convert(pdf, out, *extra):
    r = run([pdf, out, *extra])
    stem = os.path.splitext(os.path.basename(pdf))[0]
    md, work = None, None
    if r.returncode == 0:
        with open(os.path.join(out, stem + ".md"), encoding="utf-8") as f:
            md = f.read()
        with open(os.path.join(out, "_worklist.json"), encoding="utf-8") as f:
            work = json.load(f)
    return r, md, work


class TwoColumnArticle(unittest.TestCase):
    """The English fixture: a two-column article with known ground truth."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="mdconvert-")
        cls.pdf = os.path.join(cls.tmp, "fixture.pdf")
        cls.out = os.path.join(cls.tmp, "out")
        make_fixture.build(cls.pdf)
        r, cls.md, cls.work = convert(cls.pdf, cls.out)
        assert r.returncode == 0, r.stderr

    # ---- structure
    def test_single_h1_is_the_title(self):
        h1 = re.findall(r"^# (.+)$", self.md, re.M)
        self.assertEqual(len(h1), 1)
        self.assertIn("Layout aware conversion", h1[0])

    def test_author_and_affiliation_are_plain_text(self):
        self.assertIn("\nA. Author*, B. Coauthor*\n", self.md)
        self.assertNotRegex(self.md, r"(?m)^#+ .*Author")
        self.assertNotRegex(self.md, r"(?m)^#+ Department")

    def test_page_chrome_removed(self):
        self.assertNotIn("Journal of Synthetic Vector Biology", self.md)
        self.assertNotIn("Vol. 12, No. 3", self.md)
        self.assertNotRegex(self.md, r"(?m)^\s*\d\s*$")

    def test_licence_notice_removed(self):
        self.assertNotIn("hereby grants permission", self.md)
        self.assertTrue(any("Provided proper attribution" in x for x in self.work["front_matter_removed"]))

    def test_column_reading_order(self):
        left = self.md.index("Arboviral surveillance depends")
        right = self.md.index("Vector competence was summarised")
        self.assertLess(left, right)
        self.assertLess(self.md.index("The proportion of positive tissues rose"),
                        self.md.index("Fig 1. Disseminated infection"))

    def test_paragraph_not_fragmented(self):
        para = [b for b in self.md.split("\n\n") if b.startswith("Arboviral surveillance")]
        self.assertEqual(len(para), 1)
        self.assertTrue(para[0].rstrip().endswith("ground truth."))

    def test_paragraph_rejoined_across_column_break(self):
        self.assertIn("the sensitivity analysis was repeated with a stricter positivity threshold", self.md)

    # ---- hyphenation
    def test_compound_hyphen_kept(self):
        self.assertIn("A high-level summary", self.md)
        self.assertNotIn("highlevel", self.md)

    def test_syllable_hyphen_joined(self):
        self.assertIn("a classification rule", self.md)
        self.assertIn("adult mosquitoes after ingestion", self.md)
        self.assertNotRegex(self.md, r"[a-z]- [a-z]")

    # ---- captions, tables, figures, equations
    def test_captions_italic_and_underlined(self):
        self.assertRegex(self.md, r"_<u>Fig 1\..*</u>_")
        self.assertRegex(self.md, r"_<u>Table 1\..*</u>_")

    def test_table_row_labels_recovered(self):
        self.assertIn("|  | Tested | Positive |", self.md)
        self.assertIn("| Legs & Wings | 25 | 12 |", self.md)
        self.assertIn("| Ovaries | 25 | 1 |", self.md)
        self.assertEqual(self.work["table_stub_columns_recovered"], [2])
        self.assertNotRegex(self.md, r"(?m)^Legs & Wings")      # not left behind as prose

    def test_figure_extracted_and_linked(self):
        self.assertEqual(len(self.work["figures"]), 1)
        link = re.search(r"!\[[^\]]*\]\((images/[^)]+)\)", self.md)
        self.assertIsNotNone(link)
        self.assertTrue(os.path.exists(os.path.join(self.out, link.group(1))))

    def test_equation_placeholder_emitted(self):
        self.assertIn("<!-- MDC:EQ:", self.md)
        self.assertEqual(len(self.work["equations"]), 1)

    def test_counts_reconcile(self):
        self.assertEqual(self.work["warnings"], [])

    # ---- references
    def test_references_numbered_and_sequential(self):
        tail = self.md[self.md.index("## References"):self.md.index("## Appendix")]
        nums = [int(n) for n in re.findall(r"(?m)^(\d+)\. ", tail)]
        self.assertEqual(nums, [1, 2, 3, 4])
        self.assertEqual(self.work["reference_range"], [1, 4])

    def test_accents_recombined(self):
        self.assertIn("Müller K, Dollár P.", self.md)
        self.assertNotIn("¨", self.md)
        self.assertNotIn("´", self.md)

    def test_content_after_references_kept_in_order(self):
        self.assertLess(self.md.index("## References"), self.md.index("## Appendix"))
        self.assertIn("Sensitivity analyses used the same tissue panel", self.md)

    # ---- watermarks
    def test_watermark_text_absent(self):
        for mark in ("CONFIDENTIAL", "DRAFT", "DO NOT COPY", "Internal review copy"):
            self.assertNotIn(mark, self.md, mark)

    def test_watermarks_recorded(self):
        wm = self.work["watermarks"]
        self.assertGreaterEqual(wm["declared_sections_removed"], 2)     # artifact + layer
        self.assertEqual(wm["hidden_layers"], ["Watermark"])
        self.assertEqual(wm["images_hidden"], 1)
        for mark in ("CONFIDENTIAL", "DRAFT", "DO NOT COPY", "Internal review copy"):
            self.assertIn(mark, wm["samples"])

    def test_watermark_image_not_extracted_as_figure(self):
        self.assertEqual([f["page"] for f in self.work["figures"]], [1])

    def test_body_text_under_watermark_survives(self):
        self.assertIn("largest between day 7 and day 14, after which the curve flattened", self.md)

    # ---- figure label text (read from the PDF, not from the crop)
    def test_axis_ticks_read_verbatim(self):
        t = self.work["figures"][0]["ticks"]
        self.assertEqual(t["x"]["labels"], ["7", "14", "21", "28"])
        self.assertEqual(t["x"]["scale"], "linear")
        self.assertEqual(t["y"]["values"], [100.0, 75.0, 50.0, 25.0, 0.0])
        self.assertEqual(t["y"]["range"], [0.0, 100.0])

    def test_axis_titles_read(self):
        titles = self.work["figures"][0]["axis_titles"]
        self.assertEqual(titles["y"], "Positive tissues (%)")     # rotated on the page
        self.assertEqual(titles["x"], "Days post exposure")

    def test_printed_statistics_captured(self):
        self.assertEqual(self.work["figures"][0]["printed_stats"], ["p = 0.003", "n = 25"])

    def test_citing_sentence_attached(self):
        cited = self.work["figures"][0]["cited_by"]
        self.assertTrue(any("As Fig 1 shows" in s for s in cited), cited)

    def test_figure_labels_not_left_as_prose(self):
        for stray in ("\n100\n", "\n75\n", "\nDays post exposure\n",
                      "Positive tissues (%)", "p = 0.003"):
            self.assertNotIn(stray, self.md, stray)

    def test_rotated_axis_title_is_not_a_watermark(self):
        wm = self.work["watermarks"]
        self.assertGreaterEqual(wm["axis_text_recovered"], 1)
        self.assertEqual(wm["text_removed"].get("rotated"), 1)    # the diagonal stamp only
        self.assertNotIn("Positive tissues (%)", wm["samples"])


class ChineseArticle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tmp = tempfile.mkdtemp(prefix="mdconvert-zh-")
        pdf = os.path.join(tmp, "zh.pdf")
        make_fixture.build_cjk(pdf)
        r, cls.md, cls.work = convert(pdf, os.path.join(tmp, "out"))
        assert r.returncode == 0, r.stderr

    def test_title_and_sections(self):
        self.assertRegex(self.md, r"(?m)^# 登革熱病媒蚊監測資料之版面分析$")
        self.assertRegex(self.md, r"(?m)^## 摘要$")
        self.assertRegex(self.md, r"(?m)^## 結果$")
        self.assertNotRegex(self.md, r"(?m)^#+ 王小明")

    def test_lines_joined_without_spaces(self):
        self.assertIn("用於將病媒蚊監測報告轉為可檢索的文字。", self.md)
        self.assertNotRegex(self.md, r"[一-鿿] [一-鿿]")

    def test_cjk_captions(self):
        self.assertIn("_<u>圖1 監測流程與每週捕獲趨勢</u>_", self.md)
        self.assertIn("_<u>表1 各週捕獲數與陽性數</u>_", self.md)
        self.assertEqual(self.work["warnings"], [])

    def test_cjk_references(self):
        self.assertRegex(self.md, r"(?m)^## 參考文獻$")
        self.assertEqual(self.work["reference_range"], [1, 3])


class FileProblems(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="mdconvert-files-")

    def test_image_only_pdf_is_refused(self):
        import pymupdf
        pdf = os.path.join(self.tmp, "scan.pdf")
        doc = pymupdf.open()
        page = doc.new_page()
        pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 600, 800))
        pix.clear_with(210)
        page.insert_image(page.rect, pixmap=pix)
        doc.save(pdf)
        r = run([pdf, os.path.join(self.tmp, "out")])
        self.assertEqual(r.returncode, 3)
        self.assertTrue(json.loads(r.stdout.strip().splitlines()[-1])["scanned"])

    def test_encrypted_pdf_needs_password(self):
        plain, locked = os.path.join(self.tmp, "p.pdf"), os.path.join(self.tmp, "locked.pdf")
        make_fixture.build(plain)
        make_fixture.build_encrypted(plain, locked, "secret")
        r = run([locked, os.path.join(self.tmp, "o1")])
        self.assertEqual(r.returncode, 4)
        self.assertTrue(json.loads(r.stdout.strip().splitlines()[-1])["encrypted"])
        r = run([locked, os.path.join(self.tmp, "o2"), "--password", "wrong"])
        self.assertEqual(r.returncode, 4)
        r, md, _ = convert(locked, os.path.join(self.tmp, "o3"), "--password", "secret")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Layout aware conversion", md)

    def test_damaged_file_is_reported(self):
        bad = os.path.join(self.tmp, "bad.pdf")
        with open(bad, "wb") as f:
            f.write(b"this is not a pdf at all")
        r = run([bad, os.path.join(self.tmp, "out")])
        self.assertEqual(r.returncode, 5)
        self.assertEqual(json.loads(r.stdout.strip().splitlines()[-1])["error"], "cannot_open")


class TextHelpers(unittest.TestCase):
    def test_ligatures_expanded(self):
        self.assertEqual(mx.clean_text("classiﬁcation eﬃcient ﬂow"),
                         "classification efficient flow")

    def test_spacing_accents_recombined(self):
        self.assertEqual(mx.clean_text("M¨uller, Doll´ar, Mont´ı"), "Müller, Dollár, Montí")

    def test_prime_after_digit_untouched(self):
        self.assertEqual(mx.clean_text("5´UTR"), "5´UTR")

    def test_hyphen_rules(self):
        mx._VOCAB.clear()
        self.assertTrue(mx.keep_hyphen("2", "year"))
        self.assertTrue(mx.keep_hyphen("IgG", "positive"))
        self.assertTrue(mx.keep_hyphen("deeply", "supervised"))
        self.assertTrue(mx.keep_hyphen("high", "level"))
        self.assertFalse(mx.keep_hyphen("dependen", "cies"))
        mx._VOCAB.update({"nonstructural": 3})
        self.assertFalse(mx.keep_hyphen("non", "structural"))    # the document's own spelling wins
        mx._VOCAB.clear()

    def test_join_lines(self):
        self.assertEqual(mx.join_lines(["SARS-", "CoV-2 infection"]), "SARS-CoV-2 infection")
        self.assertEqual(mx.join_lines(["病媒蚊監測", "報告"]), "病媒蚊監測報告")

    def test_caption_requires_caption_shape(self):
        self.assertTrue(mx.CAPTION_RE.match("Figure 2. Residual learning"))
        self.assertTrue(mx.CAPTION_RE.match("Table 1 Baseline characteristics"))
        self.assertTrue(mx.CAPTION_RE.match("Fig 3: Kaplan-Meier curves"))
        self.assertIsNone(mx.CAPTION_RE.match("Fig. 6 (middle) shows the behaviour"))
        self.assertIsNone(mx.CAPTION_RE.match("Table 1 shows the results"))

    # ---- axis reading
    def test_label_value(self):
        self.assertEqual(mx.label_value("1,000"), 1000.0)
        self.assertEqual(mx.label_value("25%"), 25.0)
        self.assertEqual(mx.label_value("−3.5"), -3.5)
        self.assertIsNone(mx.label_value("d7"))

    def test_axis_scale_measured_not_assumed(self):
        pos = [100.0, 200.0, 300.0, 400.0]
        self.assertEqual(mx.axis_scale([1.0, 10.0, 100.0, 1000.0], pos), "log")
        self.assertEqual(mx.axis_scale([0.0, 25.0, 50.0, 75.0], pos), "linear")
        self.assertEqual(mx.axis_scale([1.0, 50.0, 2.0, 60.0], pos), "unknown")

    def test_axis_from_row_and_column(self):
        rect = mx.pymupdf.Rect(308, 372, 539, 482)
        xs = [{"t": t, "b": [c - 4, 474, c + 4, 481]}
              for t, c in zip(("7", "14", "21", "28"), (330, 372, 414, 456))]
        ys = [{"t": t, "b": [292, c - 3, 302, c + 3]}
              for t, c in zip(("100", "75", "50", "25", "0"), (374, 399, 424, 449, 474))]
        x = mx.axis_from(xs + ys, rect, "x")
        y = mx.axis_from(xs + ys, rect, "y")
        self.assertEqual((x["labels"], x["scale"]), (["7", "14", "21", "28"], "linear"))
        self.assertEqual((y["values"], y["range"]), ([100.0, 75.0, 50.0, 25.0, 0.0], [0.0, 100.0]))
        self.assertIsNone(mx.axis_from(xs[:2], rect, "x"))        # two labels are not an axis

    def test_statistics_patterns(self):
        self.assertTrue(mx.PVAL_RE.search("P < 0.001 versus baseline"))
        self.assertTrue(mx.PVAL_RE.search("p = 1.2 x 10-4"))
        self.assertTrue(mx.NEQ_RE.search("Severe (n = 41)"))
        self.assertTrue(mx.CI_RE.search("95% CI 1.2 to 3.4"))
        self.assertTrue(mx.PANEL_LABEL_RE.match("(B)"))
        self.assertIsNone(mx.PANEL_LABEL_RE.match("Body"))

    def test_marked_content_stripper(self):
        data = (b"q BT (keep) Tj ET Q\n/Artifact <</Subtype /Watermark>> BDC q BT (drop (nested)) Tj ET Q EMC\n"
                b"/Span <</ActualText (x)>> BDC BT (also keep) Tj ET EMC")
        new, k = mx.strip_marked(data, lambda tag, props: tag == b"/Artifact" and b"/Watermark" in props)
        self.assertEqual(k, 1)
        self.assertIn(b"(keep)", new)
        self.assertIn(b"(also keep)", new)
        self.assertNotIn(b"drop", new)


if __name__ == "__main__":
    unittest.main(verbosity=2)
