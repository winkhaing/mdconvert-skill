#!/usr/bin/env python3
"""
mdconvert_extract.py - layout-aware scientific PDF -> Markdown (deterministic stage).

Usage:
    python3 mdconvert_extract.py INPUT.pdf OUTDIR [--dpi 220] [--password PW]

Writes OUTDIR/<stem>.md, OUTDIR/images/*.png, OUTDIR/equations/*.png and
OUTDIR/_worklist.json (figures and equations awaiting the vision passes).

Exit codes
    0  converted
    3  scanned or image-only PDF: no usable text layer
    4  encrypted PDF that needs a password (pass --password)
    5  the file cannot be opened as a PDF
"""
import argparse
import json
import math
import os
import re
import sys
import unicodedata
from collections import Counter

import pymupdf

__version__ = "0.3.0"

# ================================================================ patterns

# A caption is a label plus a number followed by punctuation, an uppercase word or
# the end of the block. "Fig. 6 (middle) shows ..." is body text, not a caption.
CAPTION_RE = re.compile(
    r"^\s*(?:"
    r"(?:Fig(?:ure|s)?|Table|Scheme|Chart|Box|Panel|Exhibit|Appendix\s+Table|"
    r"Supplementary\s+(?:Fig(?:ure)?|Table))\s*\.?\s*(?:S?\d+[A-Za-z]?|(?-i:[IVXLC]+))"
    r"(?=\s*[.:|\u2013\u2014-]|\s+(?-i:[A-Z])|\s*$)"
    r"|(?:Graphical\s+abstract|Central\s+illustration)\b"
    r"|[圖图図表]\s*[0-9０-９一二三四五六七八九十]+"
    r"|(?:ပုံ|ဇယား)\s*[0-9၀-၉]+"
    r")", re.I)
FIGCAP_RE = re.compile(
    r"^\s*(?:Fig|Scheme|Chart|Graphical\s+abstract|Central\s+illustration|"
    r"Supplementary\s+Fig|[圖图図]|ပုံ)", re.I)
TABCAP_RE = re.compile(r"^\s*(?:Table|Appendix\s+Table|Supplementary\s+Table|表|ဇယား)", re.I)

REF_HEAD_RE = re.compile(
    r"^\s*(?:(?:\d+\.?\s*)?(?:references?(?:\s+and\s+notes)?|bibliography|literature\s+cited|"
    r"reference\s+list|works\s+cited)|參考文獻|参考文献|參考資料|参考资料|引用文獻|"
    r"ကိုးကား(?:ချက်များ)?)\s*[:：]?\s*$", re.I)
SECTION_WORDS = re.compile(
    r"^\s*(?:\d+\.?\d*\.?\s+|[一二三四五六七八九十]+[、.．]\s*)?"
    r"(abstract|summary|introduction|background|methods?|materials\s+and\s+methods|"
    r"patients\s+and\s+methods|study\s+design|results?|findings|discussion|conclusions?|limitations|"
    r"acknowledg(?:e)?ments?|funding|author\s+contributions|conflicts?\s+of\s+interest|"
    r"competing\s+interests|data\s+availability|ethics\s+statement|supplementary\s+material|"
    r"references?|bibliography|keywords?"
    r"|摘要|前言|引言|緒論|绪论|背景|方法|研究方法|材料與方法|材料和方法|材料与方法|結果|结果|"
    r"討論|讨论|結論|结论|致謝|致谢|參考文獻|参考文献|關鍵詞|关键词)"
    r"\s*[:：]?\s*$", re.I)
NUMBERED_HEAD_RE = re.compile(r"^\s*(\d{1,2}(?:\.\d{1,2}){0,3})\.?\s+[A-Z]")
POST_REF_HEAD_RE = re.compile(
    r"^\s*(?:appendix|supplement|supporting\s+information|author\s+biograph|附錄|附录)", re.I)
EQ_NUM_RE = re.compile(r"\(\s*\d+[a-z]?\s*\)\s*$")
MATH_FONT_RE = re.compile(r"(CMMI|CMSY|CMEX|MSAM|MSBM|MathematicalPi|Symbol|Math|Euclid|AdvP4|LucidaMath|STIX)", re.I)
MATH_OPS = set("=\u2264\u2265\u2248\u2260\u221d\u2261\u2192\u2211\u222b\u221a")
MATH_CHARS = set("∑∫∏√±×÷≤≥≠≈∞∂∇∈∉⊂⊆∪∩→←↔αβγδεζηθικλμνξπρστυφχψωΓΔΘΛΞΠΣΦΨΩ⟨⟩‖∥⊗⊕∀∃¬∧∨")

JOURNAL_LABEL_RE = re.compile(
    r"^\s*(research\s+article|original\s+(research|article|investigation)|review(\s+article)?|"
    r"brief\s+report|short\s+communication|case\s+report|systematic\s+review|editorial|"
    r"open\s+access|article)\b[:\s|-]*", re.I)
SPLIT_HEAD_RE = re.compile(
    r"^(Materials\s+and\s+methods|Methods|Results|Discussion|Introduction|Background|"
    r"Conclusions?|Patients\s+and\s+methods)\s+([A-Z].{3,})$")
JUNK_RE = re.compile(r"^(.)\1{7,}$")
BULLET_RE = re.compile(r"^\s*([•·▪◦‣–\-\*]|\(?[a-z]\)|\(?\d{1,2}[\.\)])\s+")
FOOTNOTE_RE = re.compile(r"^\s*(?:\d{1,2}|[*†‡§¶∗])\s*\S")

# Licence, permission and download notices, and journal metadata blocks. Removed only when
# they are short and sit on the first or last page, in a page band, or in small print.
NOISE_RE = re.compile(
    r"provided proper attribution is provided|hereby grants? permission|downloaded from\s|"
    r"this is an open[ -]access article|this article is licensed under|"
    r"distributed under the terms of the creative commons|creative commons attribution|"
    r"all rights reserved|for personal use only|not for (?:re)?distribution|check for updates|"
    r"^\s*(?:citation|how to cite(?: this article)?)\s*:|^\s*(?:academic\s+)?editor\s*:|"
    r"^\s*received\s*:.*accepted\s*:|^\s*copyright\s*[:©]|^\s*©\s*\d{4}|^\s*\(c\)\s*\d{4}|"
    r"^\s*arxiv:\s*\d{4}\.\d{4,5}v\d+\s*\[", re.I)
REF_ENTRY_RE = re.compile(r"^\s*\[?\d{1,3}[\].)]?\s+\S")

# Optional content groups (layers) with these names are treated as watermarks.
WM_LAYER_RE = re.compile(r"water\s*mark|draft|confidential|do\s*not\s*copy|sample|stamp|background", re.I)

# Text printed inside a figure: axis ticks, panel letters, statistics printed on the plot.
NUM_LABEL_RE = re.compile(r"^[+\-−]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:[.]\d+)?\s*%?$")
PANEL_LABEL_RE = re.compile(r"^[(\[]?([A-Ha-h])[)\].:]?$")
PVAL_RE = re.compile(r"(?i)\bp\s*(?:value)?\s*[<>=≤≥]\s*"
                     r"(?:0?\.\d+|\d(?:\.\d+)?\s*(?:[x×]\s*10|e)\s*[-−]?\s*\d+|\d+)")
NEQ_RE = re.compile(r"(?i)\bn\s*=\s*\d[\d,]*")
CI_RE = re.compile(r"(?i)\d{2}\s*%\s*(?:CI|confidence interval)")
SIG_RE = re.compile(r"^(?:\*{1,4}|n\.?s\.?|†|‡)$", re.I)
FIG_LABEL_NUM_RE = re.compile(r"(?:fig(?:ure)?\.?|圖|图|図)\s*"
                              r"([0-9]{1,3}|[IVX]{1,5})", re.I)

LIGATURES = {"\ufb00": "ff", "\ufb01": "fi", "\ufb02": "fl", "\ufb03": "ffi",
             "\ufb04": "ffl", "\ufb05": "st", "\ufb06": "st"}
# TeX-produced PDFs often emit a spacing accent before its letter: "M¨uller", "Doll´ar".
SPACING_ACCENTS = {"\u00a8": "\u0308", "\u00b4": "\u0301", "\u02c6": "\u0302", "\u02dc": "\u0303",
                   "\u02c7": "\u030c", "\u02d8": "\u0306", "\u02d9": "\u0307", "\u02da": "\u030a",
                   "\u02dd": "\u030b"}
ACCENT_RE = re.compile(r"(?<![0-9])([\u00a8\u00b4\u02c6\u02dc\u02c7\u02d8\u02d9\u02da\u02dd])([A-Za-z\u0131])")

# First elements that usually form hyphenated compounds; consulted only when the document's
# own vocabulary says nothing about a line-end hyphen.
COMPOUND_FIRST = {
    "high", "low", "well", "self", "long", "short", "large", "small", "full", "half", "cross",
    "open", "fine", "deep", "wide", "first", "second", "third", "one", "two", "three", "four",
    "five", "all", "non", "anti", "state", "time", "dose", "age", "sex", "case", "cell", "end",
    "real", "world", "follow", "vector", "mosquito", "virus", "host", "data", "risk", "cost",
    "health", "life", "population", "community", "hospital", "treatment", "drug", "gene",
    "model", "sample", "region", "multi", "inter", "intra", "post", "pre", "co", "sub", "semi"}

CJK_TERMINAL = "。！？；：」』）．"
_VOCAB = Counter()          # document vocabulary, filled in pass 1


# ================================================================ small helpers
def is_cjk(ch):
    o = ord(ch)
    return (0x3000 <= o <= 0x30FF or 0x3400 <= o <= 0x4DBF or 0x4E00 <= o <= 0x9FFF
            or 0xF900 <= o <= 0xFAFF or 0xFF00 <= o <= 0xFFEF or 0xAC00 <= o <= 0xD7AF)


def cjk_ratio(s):
    chars = [c for c in s if not c.isspace()]
    return sum(is_cjk(c) for c in chars) / len(chars) if chars else 0.0


def clean_text(s):
    """Expand ligatures, recombine spacing accents, normalise to NFC."""
    if not s:
        return s
    for k, v in LIGATURES.items():
        if k in s:
            s = s.replace(k, v)
    s = ACCENT_RE.sub(lambda m: ("i" if m.group(2) == "\u0131" else m.group(2)) + SPACING_ACCENTS[m.group(1)], s)
    return unicodedata.normalize("NFC", s)


def norm_chrome(s):
    s = re.sub(r"\d+", "#", s)
    return re.sub(r"\s+", " ", s).strip().lower()


def area(r):
    return max(0.0, r.width) * max(0.0, r.height)


def overlap_frac(a, b):
    inter = a & b
    return area(inter) / area(a) if area(a) > 0 else 0.0


def luminance(color_int):
    r, g, b = (color_int >> 16) & 255, (color_int >> 8) & 255, color_int & 255
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255.0


def horizontal(line):
    d = line.get("dir", (1.0, 0.0))
    return abs(d[0] - 1.0) <= 0.02 and abs(d[1]) <= 0.02


# ================================================================ hyphenation and joining
WORD_RE = re.compile(r"[A-Za-z][A-Za-z'\-]*[A-Za-z]")


def add_vocab(text):
    for line in text.splitlines():
        s = clean_text(line).rstrip()
        tokens = WORD_RE.findall(s)
        if s.endswith("-") and tokens:
            tokens = tokens[:-1]                      # line-end fragment, not a word
        for t in tokens:
            _VOCAB[t.lower()] += 1


def keep_hyphen(a, b):
    """Decide whether a line-end hyphen between a and b belongs to a compound word."""
    if any(c.isdigit() for c in a):
        return True                                   # 2-year, NS1-positive
    if sum(c.isupper() for c in a) >= 2:
        return True                                   # IgG-, SARS-
    if a.lower().endswith("ly") and len(a) >= 5:
        return True                                   # deeply-supervised
    joined, hyph = (a + b).lower(), (a + "-" + b).lower()
    jc, hc = _VOCAB.get(joined, 0), _VOCAB.get(hyph, 0)
    if hc > jc:
        return True
    if jc > 0:
        return False
    return a.lower() in COMPOUND_FIRST


def join_lines(lines):
    """Join physical lines into one paragraph string, repairing hyphenation."""
    out = ""
    for ln in lines:
        t = ln.strip()
        if not t:
            continue
        if not out:
            out = t
            continue
        if out.endswith("\u00ad"):
            out = out[:-1] + t
        elif out.endswith("-") and not out.endswith("--") and re.search(r"[A-Za-z0-9]-$", out):
            m = re.search(r"([A-Za-z0-9]+)-$", out)
            n = re.match(r"[A-Za-z]+", t)
            if re.match(r"^[A-Z0-9]", t):
                out += t                                  # SARS- + CoV-2, COVID- + 19
            elif n and not keep_hyphen(m.group(1), n.group(0)):
                out = out[:-1] + t                        # dependen- + cies
            else:
                out += t                                  # high- + level
        elif is_cjk(out[-1]) and is_cjk(t[0]):
            out += t
        else:
            out += " " + t
    return re.sub(r"\s+", " ", out).strip()


# ================================================================ declared watermarks
_WS = b" \t\r\n\f\x00"
_DELIM = b"()<>[]{}/%"
_EI_RE = re.compile(rb"\sEI(?=\s|$)")


def _skip_string(data, i):
    depth, n = 0, len(data)
    while i < n:
        c = data[i]
        if c == 0x5C:
            i += 2
            continue
        if c == 0x28:
            depth += 1
        elif c == 0x29:
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return n


def _skip_dict(data, i):
    depth, n = 0, len(data)
    while i < n:
        if data.startswith(b"<<", i):
            depth += 1
            i += 2
            continue
        if data.startswith(b">>", i):
            depth -= 1
            i += 2
            if depth == 0:
                return i
            continue
        if data[i] == 0x28:
            i = _skip_string(data, i)
            continue
        i += 1
    return n


def strip_marked(data, is_target):
    """Remove marked-content sections (BDC/BMC ... EMC) for which is_target(tag, props) holds.

    A small tokenizer walks the content stream so that strings, hex strings, dictionaries,
    comments and inline image data can never be mistaken for operators.
    Returns (new_bytes, sections_removed).
    """
    n, i = len(data), 0
    operands, stack, cuts = [], [], []
    while i < n:
        c = data[i]
        if c in _WS:
            i += 1
            continue
        start = i
        if c == 0x25:                                     # % comment
            j = data.find(b"\n", i)
            i = n if j < 0 else j + 1
            continue
        if c == 0x28:                                     # (string)
            i = _skip_string(data, i)
            operands.append((b"", start))
            continue
        if data.startswith(b"<<", i):
            i = _skip_dict(data, i)
            operands.append((data[start:i], start))
            continue
        if c == 0x3C:                                     # <hex string>
            j = data.find(b">", i)
            i = n if j < 0 else j + 1
            operands.append((b"", start))
            continue
        if c in b"[]{}":
            i += 1
            operands.append((b"", start))
            continue
        if c == 0x2F:                                     # /Name
            i += 1
            while i < n and data[i] not in _WS and data[i] not in _DELIM:
                i += 1
            operands.append((data[start:i], start))
            continue
        while i < n and data[i] not in _WS and data[i] not in _DELIM:
            i += 1
        tok = data[start:i]
        if not tok:
            i += 1
            continue
        if tok[0] in b"0123456789+-.":
            operands.append((tok, start))
            continue
        first = operands[0][1] if operands else start      # operator reached
        if tok == b"BI":
            j = data.find(b"ID", i)
            m = _EI_RE.search(data, j + 3) if j >= 0 else None
            i = n if m is None else m.end()
        elif tok in (b"BDC", b"BMC"):
            tag = operands[0][0] if operands else b""
            props = operands[1][0] if len(operands) > 1 else b""
            stack.append((first, bool(is_target(tag, props))))
        elif tok == b"EMC" and stack:
            s, hit = stack.pop()
            if hit and not any(h for _, h in stack):
                cuts.append((s, i))
        operands = []
    if not cuts:
        return data, 0
    parts, last = [], 0
    for s, e in cuts:
        parts.append(data[last:s])
        last = e
    parts.append(data[last:])
    return b"\n".join(parts), len(cuts)


def _props_map(doc, xref):
    """Map marked-content property names (/MC0) to OCG xrefs for one resource owner."""
    try:
        kind, val = doc.xref_get_key(xref, "Resources/Properties")
    except Exception:
        return {}
    if kind == "xref":
        val = doc.xref_object(int(val.split()[0]), compressed=True)
    elif kind != "dict":
        return {}
    return {m.group(1).encode(): int(m.group(2))
            for m in re.finditer(r"/([^\s/<>\[\]()]+)\s+(\d+)\s+0\s+R", val)}


def _target_fn(props, wm_ocgs):
    def is_target(tag, prop):
        if tag == b"/Artifact" and b"/Watermark" in prop:
            return True
        if tag == b"/OC" and wm_ocgs:
            if prop.startswith(b"/"):
                return props.get(prop[1:]) in wm_ocgs
            if prop.startswith(b"<<"):
                return any(int(x) in wm_ocgs for x in re.findall(rb"(\d+)\s+0\s+R", prop))
        return False
    return is_target


def strip_declared_watermarks(doc, wm_ocgs):
    """Delete watermark sections the PDF declares itself: /Artifact <</Subtype /Watermark>>
    marked content, and content tagged with a watermark layer. Works on the in-memory copy."""
    removed, seen, samples = 0, set(), []
    for page in doc:
        raw = page.read_contents()
        props = _props_map(doc, page.xref)
        if b"/Watermark" in raw or (wm_ocgs and any(v in wm_ocgs for v in props.values())):
            new, k = strip_marked(raw, _target_fn(props, wm_ocgs))
            if k:
                before = set(page.get_text().splitlines())
                nx = doc.get_new_xref()
                doc.update_object(nx, "<<>>")
                doc.update_stream(nx, new)
                page.set_contents(nx)
                removed += k
                for line in sorted(before - set(page.get_text().splitlines())):
                    if line.strip() and line.strip() not in samples and len(samples) < 8:
                        samples.append(line.strip()[:80])
        for xo in page.get_xobjects():
            x = xo[0]
            if x in seen:
                continue
            seen.add(x)
            try:
                s = doc.xref_stream(x)
            except Exception:
                continue
            if not s:
                continue
            px = _props_map(doc, x)
            if b"/Watermark" in s or (wm_ocgs and any(v in wm_ocgs for v in px.values())):
                new, k = strip_marked(s, _target_fn(px, wm_ocgs))
                if k:
                    doc.update_stream(x, new)
                    removed += k
    return removed, samples


# ================================================================ reading order
def xy_cut(units, page_width, depth=0):
    """Recursive XY-cut. units: list of dicts with 'rect'. Returns reading-ordered list."""
    if len(units) <= 1 or depth > 12:
        return sorted(units, key=lambda u: (round(u["rect"].y0, 1), u["rect"].x0))

    xs = sorted(units, key=lambda u: u["rect"].x0)           # vertical cut (column gutter)
    gutter_min = max(11.0, 0.022 * page_width)
    edge, best = xs[0]["rect"].x1, None
    for u in xs[1:]:
        gap = u["rect"].x0 - edge
        if gap >= gutter_min and (best is None or gap > best[1]):
            best = (u["rect"].x0, gap)
        edge = max(edge, u["rect"].x1)
    if best:
        cut = best[0]
        left = [u for u in units if u["rect"].x1 <= cut + 0.5]
        right = [u for u in units if u["rect"].x1 > cut + 0.5]
        if left and right:
            return xy_cut(left, page_width, depth + 1) + xy_cut(right, page_width, depth + 1)

    ys = sorted(units, key=lambda u: u["rect"].y0)           # horizontal cut
    edge, best = ys[0]["rect"].y1, None
    for u in ys[1:]:
        gap = u["rect"].y0 - edge
        if gap >= 2.0 and (best is None or gap > best[1]):
            best = (u["rect"].y0, gap)
        edge = max(edge, u["rect"].y1)
    if best:
        cut = best[0]
        top = [u for u in units if u["rect"].y1 <= cut + 0.5]
        bot = [u for u in units if u["rect"].y1 > cut + 0.5]
        if top and bot:
            return xy_cut(top, page_width, depth + 1) + xy_cut(bot, page_width, depth + 1)

    return sorted(units, key=lambda u: (round(u["rect"].y0, 1), u["rect"].x0))


# ================================================================ tables
def md_table(rows):
    rows = [["" if c is None else clean_text(re.sub(r"\s+", " ", str(c))).replace("|", "\\|").strip()
             for c in r] for r in rows]
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    keep = [i for i in range(width) if any(r[i] for r in rows)]    # drop fully empty columns
    rows = [[r[i] for i in keep] for r in rows]
    if not rows or not rows[0]:
        return None
    head = rows[0]
    if not any(head):
        head = [f"Col {i+1}" for i in range(len(rows[0]))]
        body = rows
    else:
        body = rows[1:]
    out = ["| " + " | ".join(head) + " |", "| " + " | ".join(["---"] * len(head)) + " |"]
    for r in body:
        if any(r):
            out.append("| " + " | ".join(r) + " |")
    return "\n".join(out)


def rows_from_words(table, words):
    """Rebuild cell text from watermark-filtered words, using the detected cell grid."""
    rows = []
    for row in table.rows:
        cells = []
        for cb in row.cells:
            if cb is None:
                cells.append(None)
                continue
            r = pymupdf.Rect(cb)
            ws = [w for w in words if r.contains(pymupdf.Point((w[0] + w[2]) / 2, (w[1] + w[3]) / 2))]
            ws.sort(key=lambda w: (round(w[1]), w[0]))
            cells.append(" ".join(w[4] for w in ws))
        rows.append(cells)
    return rows


def recover_stub(table, rect, words, prose_blocks):
    """Find an unruled row-label column sitting just left of a detected table.

    Returns (stub_texts_per_row, stub_rect) or None. Needs at least half of the body rows
    to carry a label, the labels to be left-aligned, and the column to sit close to the grid.
    """
    left = [w for w in words
            if w[2] <= rect.x0 + 1.5 and w[0] >= rect.x0 - 220
            and w[1] >= rect.y0 - 1 and w[3] <= rect.y1 + 1 and w[5] not in prose_blocks]
    if not left:
        return None
    stubs, starts = [], []
    for row in table.rows:
        rb = pymupdf.Rect(row.bbox)
        ws = [w for w in left if rb.y0 - 1 <= (w[1] + w[3]) / 2 <= rb.y1 + 1]
        ws.sort(key=lambda w: (round(w[1]), w[0]))
        stubs.append(clean_text(" ".join(w[4] for w in ws)))
        if ws:
            starts.append(min(w[0] for w in ws))
    body = max(1, len(stubs) - 1)
    if sum(1 for s in stubs[1:] if s) < max(1, 0.5 * body):
        return None
    if max(starts) - min(starts) > 25:                   # not a left-aligned column
        return None
    if max(w[2] for w in left) < rect.x0 - 80:           # too far from the grid
        return None
    box = pymupdf.Rect(min(w[0] for w in left), min(w[1] for w in left),
                       max(w[2] for w in left), max(w[3] for w in left))
    return stubs, box


# ================================================================ main extraction
def label_value(t):
    """Numeric value of an axis label, or None. Handles 1,000 / 25% / minus sign."""
    s = t.strip().replace("−", "-").replace("%", "").replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def _r2(xs, ys):
    """Squared correlation. 1.0 means the points sit on a straight line."""
    k = len(xs)
    if k < 3:
        return 0.0
    mx, my = sum(xs) / k, sum(ys) / k
    sxy = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    sxx = sum((a - mx) ** 2 for a in xs)
    syy = sum((b - my) ** 2 for b in ys)
    if sxx <= 1e-9 or syy <= 1e-9:
        return 0.0
    return (sxy * sxy) / (sxx * syy)


def axis_scale(values, positions):
    """Linear or log, decided by which one fits the tick positions better.

    Reading a log axis as linear is the error that silently multiplies a reported
    value by an order of magnitude, so the fit is measured rather than assumed.
    """
    if len(values) < 3:
        return "unknown"
    lin = _r2(positions, values)
    log = _r2(positions, [math.log10(v) for v in values]) if all(v > 0 for v in values) else 0.0
    if log > 0.995 and log > lin + 0.02:
        return "log"
    if lin >= 0.98:
        return "linear"
    if log >= 0.98:
        return "log"
    return "unknown"                              # ticks not monotonic in position


def axis_from(cands, rect, which):
    """A row (x) or column (y) of numeric tick labels, with its scale and range."""
    vals = [(it, label_value(it["t"])) for it in cands if NUM_LABEL_RE.match(it["t"])]
    vals = [(it, v) for it, v in vals if v is not None]
    if len(vals) < 3:
        return None
    if which == "x":
        keys = [lambda it: round(((it["b"][1] + it["b"][3]) / 2) / 4.0)]
        pos = lambda it: (it["b"][0] + it["b"][2]) / 2
        reach, extent = 0.25 * rect.width, rect.width
    else:
        keys = [lambda it: round(it["b"][2] / 4.0),
                lambda it: round(((it["b"][0] + it["b"][2]) / 2) / 4.0)]
        pos = lambda it: (it["b"][1] + it["b"][3]) / 2
        reach, extent = 0.25 * rect.height, rect.height
    best = None
    for key in keys:
        groups = {}
        for it, v in vals:
            groups.setdefault(key(it), []).append((it, v))
        for grp in groups.values():
            if len(grp) < 3:
                continue
            spread = max(pos(it) for it, _ in grp) - min(pos(it) for it, _ in grp)
            if spread < reach or spread > 3 * extent:
                continue
            if best is None or len(grp) > len(best):
                best = grp
    if not best:
        return None
    best.sort(key=lambda c: pos(c[0]))
    # a real axis runs one way. Side-by-side panels give several runs of the same
    # ticks; numbers inside a diagram (layer widths, node labels) give none.
    runs, cur = [], [best[0]]
    for prev, nxt in zip(best, best[1:]):
        up = len(cur) < 2 or cur[1][1] > cur[0][1]
        down = len(cur) < 2 or cur[1][1] < cur[0][1]
        if (nxt[1] > prev[1] and up) or (nxt[1] < prev[1] and down):
            cur.append(nxt)
        else:
            runs.append(cur)
            cur = [nxt]
    runs.append(cur)
    runs = [r for r in runs if len(r) >= 3]
    if not runs:
        return None
    grp = max(runs, key=len)
    v = [x for _, x in grp]
    p = [pos(it) for it, _ in grp]
    cross = [(it["b"][1] + it["b"][3]) / 2 if which == "x" else (it["b"][0] + it["b"][2]) / 2
             for it, _ in grp]
    out = {"labels": [it["t"] for it, _ in grp], "values": v,
           "scale": axis_scale(v, p), "range": [min(v), max(v)],
           "at": round(sum(cross) / len(cross), 1)}
    if len(runs) > 1:
        out["repeats"] = len(runs)                 # the same axis on each panel
    return out


def figure_labels(pdict, words, rect, dropped, exclude, body_size, max_items=120):
    """Text printed inside a figure: tick labels, axis titles, legend entries, annotations.

    A born-digital PDF carries these as vector text, so they are read verbatim here
    instead of being guessed from the crop. Two rules matter:
      - the box is padded, because tick labels and axis titles usually sit just
        outside the drawing that defines the figure;
      - a rotated span inside a figure is an axis title, not a watermark, so it is
        kept here even though the watermark rule dropped it from the prose.
    """
    pad = min(26.0, max(10.0, 0.10 * max(rect.width, rect.height)))
    box = pymupdf.Rect(rect) + (-pad, -pad, pad, pad)

    def wanted(r):
        c = pymupdf.Point((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2)
        return box.contains(c) and not any(x.contains(c) for x in exclude)

    items, rotated_kept, used = [], 0, set()
    for bi, b in enumerate(pdict["blocks"]):
        if b.get("type") != 0:
            continue
        taken = whole = 0
        btext, bsize = "", 0.0
        for l in b.get("lines", []):
            rot = not horizontal(l)
            keep = []
            for s in l["spans"]:
                if not s["text"].strip():
                    continue
                whole += 1
                btext += s["text"]
                bsize = max(bsize, s["size"])
                sr = pymupdf.Rect(s["bbox"])
                if not wanted(sr):
                    continue
                reason = dropped.get((round(sr.x0, 1), round(sr.y0, 1), s["text"].strip()))
                if reason and reason != "rotated":
                    continue                       # genuine watermark ink, stays out
                if reason == "rotated":
                    rotated_kept += 1
                taken += 1
                keep.append(s)
            if not keep:
                continue
            t = clean_text("".join(s["text"] for s in keep)).strip()
            if not t:
                continue
            r = pymupdf.Rect()
            for s in keep:
                r |= pymupdf.Rect(s["bbox"])
            it = {"t": t, "b": [round(x, 1) for x in (r.x0, r.y0, r.x1, r.y1)],
                  "s": round(max(s["size"] for s in keep), 1)}
            if rot:
                it["rot"] = True
            items.append(it)
        # a short block entirely inside the figure, in label-sized type, is a label and
        # not a paragraph of its own. The size test protects a heading that happens to
        # sit next to the figure.
        if whole and taken == whole and len(btext.strip()) < 50 and bsize <= body_size + 0.2:
            used.add(bi)
    items.sort(key=lambda it: (it["b"][1], it["b"][0]))

    out = {"text": items[:max_items], "text_items": len(items)}
    if len(items) > max_items:
        out["text_truncated"] = True
    if items:                                      # so the crop keeps its own tick labels
        lab = pymupdf.Rect(rect)
        for it in items:
            lab |= pymupdf.Rect(it["b"])
        out["label_box"] = [round(x, 1) for x in (lab.x0, lab.y0, lab.x1, lab.y1)]

    # ticks come from words, not lines: a row of tick numbers is often one text line
    wcands = [{"t": clean_text(w[4]).strip(), "b": [round(x, 1) for x in w[:4]]}
              for w in words if w[4].strip() and wanted(pymupdf.Rect(w[:4]))]
    ticks = {}
    for which in ("x", "y"):
        a = axis_from(wcands, rect, which)
        if a:
            ticks[which] = a
    if ticks:
        out["ticks"] = ticks

    titles = {}
    rots = [it for it in items if it.get("rot") and len(it["t"]) > 2]
    # a chart carries one or two rotated strings (its y titles). Dozens of them mean
    # rotated data labels, as in an attention or correlation map, and no title at all.
    if 1 <= len(rots) <= 8:
        titles["y"] = max(rots, key=lambda it: len(it["t"]))["t"]
    if "x" in ticks:
        mid = (rect.x0 + rect.x1) / 2
        below = [it for it in items if not it.get("rot") and it["b"][1] > ticks["x"]["at"]
                 and len(it["t"]) > 2 and not NUM_LABEL_RE.match(it["t"])
                 and abs((it["b"][0] + it["b"][2]) / 2 - mid) < 0.3 * rect.width]
        if below:
            titles["x"] = min(below, key=lambda it: it["b"][1])["t"]
    if titles:
        out["axis_titles"] = titles

    panels = [{"label": PANEL_LABEL_RE.match(it["t"]).group(1).upper(), "b": it["b"]}
              for it in items if PANEL_LABEL_RE.match(it["t"]) and it["s"] >= 0.9 * body_size]
    if len(panels) >= 2:                           # a lone letter is not a panel grid
        out["panels"] = panels

    stats = []
    for it in items:
        for rx in (PVAL_RE, NEQ_RE, CI_RE):
            for m in rx.finditer(it["t"]):
                s = re.sub(r"\s+", " ", m.group(0)).strip()
                if s not in stats:
                    stats.append(s)
        if SIG_RE.match(it["t"]) and it["t"] not in stats:
            stats.append(it["t"])
    if stats:
        out["printed_stats"] = stats[:12]
    return out, rotated_kept, used


def extract(pdf_path, outdir, dpi=220, password=None):
    global _VOCAB
    _VOCAB = Counter()

    # ---- open, decrypt
    try:
        doc = pymupdf.open(pdf_path)
    except Exception as e:
        print(json.dumps({"error": "cannot_open", "detail": str(e)[:200]}))
        return 5
    if not doc.is_pdf or doc.page_count == 0:
        print(json.dumps({"error": "cannot_open", "detail": "not a PDF or no pages"}))
        return 5
    if doc.needs_pass:
        ok = bool(password) and doc.authenticate(password)
        if not ok and not doc.authenticate(""):
            print(json.dumps({"encrypted": True,
                              "detail": "password required" if not password else "wrong password"}))
            return 4

    n = doc.page_count
    os.makedirs(outdir, exist_ok=True)
    img_dir, eq_dir = os.path.join(outdir, "images"), os.path.join(outdir, "equations")
    flags = pymupdf.TEXTFLAGS_DICT & ~pymupdf.TEXT_PRESERVE_LIGATURES & ~pymupdf.TEXT_PRESERVE_IMAGES
    warnings = []

    # ---- declared watermarks: layers and /Artifact /Watermark sections
    try:
        ocgs = doc.get_ocgs() or {}
    except Exception:
        ocgs = {}
    wm_ocgs = {x for x, o in ocgs.items() if WM_LAYER_RE.search(o.get("name") or "")}
    try:
        declared, declared_samples = strip_declared_watermarks(doc, wm_ocgs)
    except Exception as e:
        declared, declared_samples = 0, []
        warnings.append(f"declared watermark removal skipped ({e})")
    if wm_ocgs:
        try:
            doc.set_layer(-1, off=list(wm_ocgs))
        except Exception:
            pass

    # ---- scanned-PDF gate
    sampled = min(n, 12)
    total_chars = sum(len(doc[i].get_text("text", flags=flags).strip()) for i in range(sampled))
    if total_chars / sampled < 120:
        print(json.dumps({"scanned": True, "chars_per_page": round(total_chars / sampled, 1), "pages": n}))
        return 3

    # ---- pass 1: statistics across the whole document
    rec_min = max(2, math.ceil(0.6 * n)) if n >= 2 else 10 ** 9
    dicts, clusters, img_infos, layer_rects = [], [], [], []
    size_hist, line_pages, img_pages, clu_pages = Counter(), Counter(), Counter(), Counter()
    for pno in range(n):
        page = doc[pno]
        d = page.get_text("dict", flags=flags)
        dicts.append(d)
        keys = set()
        for b in d["blocks"]:
            for l in b.get("lines", []):
                hz = horizontal(l)
                for s in l["spans"]:
                    k = len(s["text"].strip())
                    if k and hz and s.get("alpha", 255) >= 200:
                        size_hist[round(s["size"], 1)] += k
                txt = "".join(s["text"] for s in l["spans"]).strip()
                if txt and len(txt) < 100:
                    r = pymupdf.Rect(l["bbox"])
                    keys.add((norm_chrome(txt), round(r.x0 / 15), round(r.y0 / 15)))
        line_pages.update(keys)
        add_vocab(page.get_text("text", flags=flags))
        infos = page.get_image_info(xrefs=True)
        img_infos.append(infos)
        img_pages.update({i["xref"] for i in infos if i.get("xref")})
        try:
            cl = [pymupdf.Rect(r) for r in page.cluster_drawings(x_tolerance=6, y_tolerance=6)]
        except Exception:
            cl = []
        clusters.append(cl)
        clu_pages.update({(round(r.x0 / 10), round(r.y0 / 10), round(r.x1 / 10), round(r.y1 / 10)) for r in cl})
        lr = []
        if wm_ocgs:
            try:
                for tr in page.get_texttrace():
                    if WM_LAYER_RE.search(tr.get("layer") or ""):
                        lr.append(pymupdf.Rect(tr["bbox"]))
            except Exception:
                pass
        layer_rects.append(lr)

    body_prelim = size_hist.most_common(1)[0][0] if size_hist else 10.0
    recurring_lines = {k for k, v in line_pages.items() if v >= rec_min}
    wm_images = {x for x, v in img_pages.items() if v >= rec_min}
    recurring_clusters = {k for k, v in clu_pages.items() if v >= rec_min}

    # recurring images (logos, stamps, page backgrounds) are hidden from figure crops
    for x in wm_images:
        for pno in range(n):
            if any(i.get("xref") == x for i in img_infos[pno]):
                try:
                    doc[pno].delete_image(x)
                except Exception:
                    pass
                break

    # ---- pass 1b: watermark-filtered text blocks
    wm_counts, wm_samples = Counter(), {}

    def record(reason, text, size):
        wm_counts[reason] += 1
        t = re.sub(r"\s+", " ", text).strip()
        if reason == "rotated" and size < 1.3 * body_prelim:
            return                                   # axis labels and spine text, not logged
        if len(t) >= 3:
            wm_samples.setdefault(reason, [])
            if t not in wm_samples[reason] and len(wm_samples[reason]) < 8:
                wm_samples[reason].append(t[:80])

    def span_key(rect_like, text):
        return (round(rect_like[0], 1), round(rect_like[1], 1), text.strip())

    blocks, removed_lines, wm_rects, dropped_maps = [], [], [], []
    for pno in range(n):
        page = doc[pno]
        ph = page.rect.height
        pblocks, rl, rr = [], set(), []
        dmap = {}                                    # span -> why it was dropped
        for bi, b in enumerate(dicts[pno]["blocks"]):
            if b.get("type") != 0:
                continue
            kept = []
            for li, l in enumerate(b.get("lines", [])):
                raw = "".join(s["text"] for s in l["spans"])
                r = pymupdf.Rect(l["bbox"])
                key = (norm_chrome(raw.strip()), round(r.x0 / 15), round(r.y0 / 15))
                if raw.strip() and len(raw.strip()) < 100 and key in recurring_lines:
                    band = r.y1 < 0.09 * ph or r.y0 > 0.91 * ph
                    reason = "chrome" if band else "recurring"
                    record(reason, raw, max(s["size"] for s in l["spans"]))
                    for s in l["spans"]:
                        if s["text"].strip():
                            dmap[span_key(s["bbox"], s["text"])] = reason
                    rl.add((bi, li))
                    rr.append(r)
                    continue
                hz = horizontal(l)
                spans = []
                for s in l["spans"]:
                    if not s["text"].strip():
                        spans.append(s)
                        continue
                    sr = pymupdf.Rect(s["bbox"])
                    c = pymupdf.Point((sr.x0 + sr.x1) / 2, (sr.y0 + sr.y1) / 2)
                    reason = None
                    if not hz:
                        reason = "rotated"
                    elif s.get("alpha", 255) < 200:
                        reason = "transparent"
                    elif layer_rects[pno] and any(x.contains(c) for x in layer_rects[pno]):
                        reason = "layer"
                    elif s["size"] >= 2.5 * body_prelim and luminance(s["color"]) >= 0.6:
                        reason = "large-light"
                    if reason:
                        record(reason, s["text"], s["size"])
                        dmap[span_key(s["bbox"], s["text"])] = reason
                        rr.append(sr)
                        continue
                    spans.append(s)
                if not any(s["text"].strip() for s in spans):
                    rl.add((bi, li))
                    continue
                text = clean_text("".join(s["text"] for s in spans))
                lrect = pymupdf.Rect()
                for s in spans:
                    if s["text"].strip():
                        lrect |= pymupdf.Rect(s["bbox"])
                kept.append((text, lrect, spans))
            if not kept:
                continue
            sizes, flg, fonts, nchar = Counter(), Counter(), Counter(), 0
            for _, _, spans in kept:
                for s in spans:
                    k = len(s["text"].strip())
                    if not k:
                        continue
                    sizes[round(s["size"], 1)] += k
                    flg[s["flags"]] += k
                    fonts[s["font"]] += k
                    nchar += k
            if not nchar:
                continue
            text = join_lines([t for t, _, _ in kept])
            if not text:
                continue
            rect = pymupdf.Rect()
            for _, lr_, _ in kept:
                rect |= lr_
            font = fonts.most_common(1)[0][0]
            pblocks.append({
                "rect": rect, "text": text, "lines": [t for t, _, _ in kept],
                "size": sizes.most_common(1)[0][0], "font": font,
                "bold": sum(v for f, v in flg.items() if f & 16) / nchar,
                "ital": sum(v for f, v in flg.items() if f & 2) / nchar,
                "mathfrac": sum(v for f, v in fonts.items()
                                if MATH_FONT_RE.search(f) or "Ital" in f or "Obli" in f) / nchar,
                "nchar": nchar, "page": pno + 1, "ph": ph, "bno": bi,
                "caption": bool(CAPTION_RE.match(text))})
        blocks.append(pblocks)
        removed_lines.append(rl)
        wm_rects.append(rr)
        dropped_maps.append(dmap)

    # ---- page chrome: recurring text in the top and bottom bands
    band_counter = Counter()
    for pno in range(n):
        ph = doc[pno].rect.height
        for tb in blocks[pno]:
            if tb["rect"].y1 < 0.09 * ph or tb["rect"].y0 > 0.91 * ph:
                band_counter[norm_chrome(tb["text"])] += 1
    chrome = {k for k, v in band_counter.items() if v >= max(2, int(0.35 * n)) and len(k) < 200}

    units = []
    figures, equations, front_removed, stub_pages = [], [], [], []
    fig_seq = eq_seq = axis_recovered = 0
    size_hist2 = Counter()

    # ---- pass 2: per-page layout
    for pno in range(n):
        page = doc[pno]
        pr, pw, ph = page.rect, page.rect.width, page.rect.height
        page_units = []
        allb = blocks[pno]
        words = [w for w in page.get_text("words", flags=flags) if (w[5], w[6]) not in removed_lines[pno]]
        prose_bnos = {tb["bno"] for tb in allb if tb["nchar"] > 150}

        def textcov(rect):
            a = area(rect)
            return sum(area(x["rect"] & rect) for x in allb) / a if a else 0.0

        # ---- tables. A candidate whose area is mostly graphics is a chart, not a table.
        try:
            paths = page.get_drawings()
        except Exception:
            paths = []

        def curve_ink(rect):
            """Count curves and diagonal strokes inside rect: plot data, never table rules."""
            k = 0
            for pth in paths:
                pr_ = pymupdf.Rect(pth["rect"])
                if area(pr_ & rect) < 0.5 * max(area(pr_), 1.0):
                    continue                                  # mostly outside, or a straight rule
                for it in pth["items"]:
                    if it[0] == "c":
                        k += 1
                    elif it[0] == "l" and abs(it[1].x - it[2].x) > 0.3 and abs(it[1].y - it[2].y) > 0.3:
                        k += 1
            return k

        table_rects, chart_rects = [], []
        try:
            for t in page.find_tables().tables:
                r = pymupdf.Rect(t.bbox)
                if area(r) < 100:
                    continue
                try:
                    rows = rows_from_words(t, words) if wm_rects[pno] else t.extract()
                except Exception:
                    continue
                cells = [c for x in (rows or []) for c in x if c is not None]
                filled = sum(1 for c in cells if str(c).strip()) / len(cells) if cells else 0.0
                if curve_ink(r) >= 3 or (textcov(r) < 0.40 and filled < 0.5):
                    chart_rects.append(r)                     # plot axes misread as a grid
                    continue
                if not rows or len(rows) < 2 or max(len(x) for x in rows) < 2:
                    continue
                if sum(1 for x in rows for c in x if c and str(c).strip()) < 4:
                    continue
                others = [c for c in clusters[pno] if area(c & r) < 0.2 * area(c)]
                stub_words = [w for w in words if not any(
                    c.contains(pymupdf.Point((w[0] + w[2]) / 2, (w[1] + w[3]) / 2)) for c in others)]
                stub = recover_stub(t, r, stub_words, prose_bnos)
                if stub and len(stub[0]) == len(rows):
                    rows = [[s] + list(row) for s, row in zip(stub[0], rows)]
                    r = r | stub[1]
                    stub_pages.append(pno + 1)
                md = md_table(rows)
                if not md:
                    continue
                table_rects.append(r)
                page_units.append({"kind": "table", "rect": r, "md": md, "page": pno + 1})
        except Exception as e:
            warnings.append(f"page {pno+1}: table detection failed ({e})")

        # ---- keep the prose blocks
        tblocks = []
        last_page = pno == n - 1
        for tb in allb:
            r, text = tb["rect"], tb["text"]
            if norm_chrome(text) in chrome:
                continue
            if JUNK_RE.match(re.sub(r"\s+", "", text)):
                continue                                       # decorative rule / marker row
            if (r.y1 < 0.09 * ph or r.y0 > 0.91 * ph) and len(re.sub(r"[^\w]", "", text)) <= 6:
                continue                                       # bare page number
            if any(overlap_frac(r, tr) > 0.55 for tr in table_rects):
                continue                                       # swallowed by a table
            edge = r.y1 < 0.12 * ph or r.y0 > 0.88 * ph
            small = tb["size"] <= body_prelim - 0.8
            if (len(text) < 700 and NOISE_RE.search(text) and not REF_ENTRY_RE.match(text)
                    and (pno == 0 or last_page or edge or small)):
                front_removed.append(re.sub(r"\s+", " ", text)[:100])
                continue                                       # licence, permission, metadata
            size_hist2[tb["size"]] += tb["nchar"]
            tblocks.append(tb)

        caption_rects = [tb["rect"] for tb in tblocks if tb["caption"]]
        fcap_blocks = [tb for tb in tblocks if tb["caption"] and FIGCAP_RE.match(tb["text"])]

        def near_fig_caption(r, gap=60):
            for tb in fcap_blocks:
                cr = tb["rect"]
                xo = min(r.x1, cr.x1) - max(r.x0, cr.x0)
                if xo > 0.3 * min(r.width, cr.width) and (0 <= cr.y0 - r.y1 < gap or 0 <= r.y0 - cr.y1 < gap):
                    return True
            return False

        # ---- figure regions: raster placements, vector clusters, misread charts
        cand = list(chart_rects)
        for info in img_infos[pno]:
            if info.get("xref") in wm_images:
                continue                                       # recurring logo / watermark image
            r = pymupdf.Rect(info["bbox"])
            if area(r) > 0.012 * area(pr) and overlap_frac(r, pr) > 0.4 and area(r) < 0.96 * area(pr):
                cand.append(r & pr)
        for r in clusters[pno]:
            if (round(r.x0 / 10), round(r.y0 / 10), round(r.x1 / 10), round(r.y1 / 10)) in recurring_clusters:
                continue                                       # recurring vector mark
            frac = area(r) / area(pr)
            if r.width > 45 and r.height > 35 and frac < 0.92:
                # small drawings count only when a figure caption sits right next to them
                if frac > 0.012 or (frac > 0.003 and near_fig_caption(r)):
                    cand.append(pymupdf.Rect(r))

        # iterative merge: grow regions until stable, but never across a caption
        merged = [pymupdf.Rect(r) for r in cand]
        changed = True
        while changed and merged:
            changed = False
            for i in range(len(merged)):
                for j in range(len(merged) - 1, i, -1):
                    a, b = merged[i], merged[j]
                    grown = a + (-12, -12, 12, 12)
                    if not (area(a & b) > 0 or area(grown & b) > 0):
                        continue
                    u = pymupdf.Rect(a) | b
                    blocked = any(area(cr & u) > 0.5 * area(cr) and area(cr & a) < 0.2 * area(cr)
                                  and area(cr & b) < 0.2 * area(cr) for cr in caption_rects)
                    if blocked:
                        continue
                    merged[i] = u
                    merged.pop(j)
                    changed = True
                    break
                if changed:
                    break

        figs = []
        for m in merged:
            if any(overlap_frac(m, tr) > 0.5 for tr in table_rects):
                continue
            prose_in = any(tb["nchar"] > 130 and overlap_frac(tb["rect"], m) > 0.5
                           for tb in tblocks if not tb["caption"])
            cov = sum(area(tb["rect"] & m) for tb in tblocks if not tb["caption"]) / max(area(m), 1)
            if cov > 0.78 or prose_in:
                continue
            for cr in caption_rects:                           # never swallow the caption
                if area(cr & m) > 0.3 * area(cr):
                    if cr.y0 >= m.y0 + 0.5 * m.height:
                        m.y1 = min(m.y1, cr.y0 - 2)
                    else:
                        m.y0 = max(m.y0, cr.y1 + 2)
            if m.width > 40 and m.height > 40:
                figs.append(m)

        # caption-anchored fallback: a figure caption whose graphic was not detected
        for tb in fcap_blocks:
            cr = tb["rect"]
            if any(min(f.x1, cr.x1) - max(f.x0, cr.x0) > 0.35 * cr.width and
                   (0 <= cr.y0 - f.y1 < 95 or 0 <= f.y0 - cr.y1 < 95) for f in figs):
                continue
            # only prose blocks bound the band; short labels inside the figure do not
            same_col = [t for t in tblocks if t is not tb and t["nchar"] >= 50 and
                        min(t["rect"].x1, cr.x1) - max(t["rect"].x0, cr.x0) > 0.35 * cr.width]
            above = [t["rect"].y1 for t in same_col if t["rect"].y1 <= cr.y0 - 2]
            below = [t["rect"].y0 for t in same_col if t["rect"].y0 >= cr.y1 + 2]
            for band in (pymupdf.Rect(cr.x0, (max(above) if above else 0.06 * ph) + 3, cr.x1, cr.y0 - 3),
                         pymupdf.Rect(cr.x0, cr.y1 + 3, cr.x1, (min(below) if below else 0.94 * ph) - 3)):
                if band.height < 45 or band.width < 45:
                    continue
                if any(t["nchar"] > 110 and overlap_frac(t["rect"], band) > 0.25 for t in tblocks):
                    continue
                if sum(area(t["rect"] & band) for t in tblocks) > 0.62 * area(band):
                    continue
                if any(overlap_frac(band, tr) > 0.4 for tr in table_rects):
                    continue
                if page.get_pixmap(clip=band & pr, dpi=72, annots=False).is_unicolor:
                    continue
                figs.append(band)
                break

        # one caption = one figure: union the panels that share a caption
        fcaps = [tb["rect"] for tb in fcap_blocks]
        if fcaps and len(figs) > 1:
            groups, loose = {}, []
            for m in figs:
                best, bestd = None, 1e9
                for k, cr in enumerate(fcaps):
                    xo = min(m.x1, cr.x1) - max(m.x0, cr.x0)
                    if xo <= 0.25 * min(m.width, cr.width):
                        continue
                    dist = cr.y0 - m.y1 if cr.y0 >= m.y1 else (m.y0 - cr.y1 if m.y0 >= cr.y1 else 0)
                    if 0 <= dist < 130 and dist < bestd:
                        best, bestd = k, dist
                if best is None:
                    loose.append(m)
                else:
                    groups.setdefault(best, []).append(m)
            for g in groups.values():
                box = pymupdf.Rect(g[0])
                for m in g[1:]:
                    box |= m
                loose.append(box)
            figs = loose

        label_exclude = caption_rects + [tb["rect"] for tb in tblocks
                                         if not tb["caption"] and tb["nchar"] >= 50]
        label_bnos = set()
        for m in figs:
            fig_seq += 1
            fid = f"fig-p{pno+1:02d}-{fig_seq:02d}"
            os.makedirs(img_dir, exist_ok=True)
            entry = {"id": fid, "page": pno + 1, "file": f"images/{fid}.png"}
            try:
                labels, kept, used = figure_labels(dicts[pno], words, pymupdf.Rect(m),
                                                   dropped_maps[pno], label_exclude, body_prelim)
                entry.update(labels)
                axis_recovered += kept
                label_bnos |= used
            except Exception as e:
                warnings.append(f"{fid}: label text not read ({e})")
            # the crop stays the figure itself. label_box says where the labels around it
            # are, for a wider re-crop in the repair pass when one is cut off.
            clip = (pymupdf.Rect(m) + (-3, -3, 3, 3)) & pr
            page.get_pixmap(clip=clip, dpi=dpi, annots=False).save(os.path.join(img_dir, fid + ".png"))
            page_units.append({"kind": "figure", "rect": pymupdf.Rect(m), "id": fid, "page": pno + 1})
            figures.append(entry)

        fig_rects = [u["rect"] for u in page_units if u["kind"] == "figure"]
        for tb in tblocks:
            if not tb["caption"] and (tb["bno"] in label_bnos
                                      or any(overlap_frac(tb["rect"], fr) > 0.6 for fr in fig_rects)):
                continue                                       # axis label, panel letter, annotation
            tb["kind"] = "text"
            page_units.append(tb)

        units.extend(xy_cut(page_units, pw))

    # ---- attach nearest caption text to each figure (helps the vision pass)
    for i, u in enumerate(units):
        if u.get("kind") != "figure":
            continue
        for j in list(range(i + 1, min(i + 4, len(units)))) + list(range(max(0, i - 2), i))[::-1]:
            v = units[j]
            if v.get("kind") == "text" and v.get("caption") and FIGCAP_RE.match(v["text"]):
                for f in figures:
                    if f["id"] == u["id"]:
                        f["caption"] = v["text"][:300]
                break

    # ---- sentences in the body that cite each figure, so the description can be checked
    body_sents = []
    for u in units:
        if u.get("kind") == "text" and not u.get("caption") and u.get("nchar", 0) >= 40:
            body_sents.extend(re.split(r"(?<=[.!?。])\s+", u["text"]))
    for f in figures:
        m = FIG_LABEL_NUM_RE.search(f.get("caption", ""))
        if not m:
            continue
        pat = re.compile(r"(?:fig(?:ure)?s?\.?|圖|图|図)\s*" + re.escape(m.group(1))
                         + r"(?![0-9])", re.I)
        cited = []
        for sent in body_sents:
            if len(sent) > 15 and pat.search(sent):
                s = re.sub(r"\s+", " ", sent).strip()
                if s not in cited:
                    cited.append(s[:400])
            if len(cited) >= 3:
                break
        if cited:
            f["cited_by"] = cited

    # rotated text recovered as an axis title is not a watermark: correct the count
    if axis_recovered and wm_counts.get("rotated"):
        wm_counts["rotated"] = max(0, wm_counts["rotated"] - axis_recovered)
        if not wm_counts["rotated"]:
            del wm_counts["rotated"]

    # ---------------------------------------------------------------- body font
    body_size = size_hist2.most_common(1)[0][0] if size_hist2 else body_prelim
    for s, cnt in size_hist2.most_common(6):
        if cnt > 0.25 * sum(size_hist2.values()):
            body_size = s
            break

    # ---------------------------------------------------------------- footnotes
    for u in units:
        if (u.get("kind") == "text" and not u.get("caption") and u["size"] <= body_size - 1.0
                and u["rect"].y0 > 0.75 * u["ph"] and FOOTNOTE_RE.match(u["text"])):
            u["footnote"] = True

    # ---------------------------------------------------------------- equations
    for u in units:
        if u.get("kind") != "text" or u.get("caption"):
            continue
        t = u["text"]
        alnum = sum(1 for c in t if c.isalnum())
        if len(t) > 300 or len(t.split()) > 30 or alnum < 3 or cjk_ratio(t) > 0.3:
            continue
        mathy = (bool(MATH_FONT_RE.search(u["font"])) or u.get("mathfrac", 0) > 0.30
                 or sum(1 for ch in set(t) if ch in MATH_CHARS) >= 2)
        has_op = any(ch in MATH_OPS for ch in t) or bool(EQ_NUM_RE.search(t))
        if mathy and has_op and not SECTION_WORDS.match(t):
            u["kind"] = "equation"

    eq_units = [u for u in units if u.get("kind") == "equation"]
    if eq_units:
        os.makedirs(eq_dir, exist_ok=True)
        for u in eq_units:
            eq_seq += 1
            eid = f"eq-{eq_seq:03d}"
            u["id"] = eid
            page = doc[u["page"] - 1]
            clip = (pymupdf.Rect(u["rect"]) + (-4, -4, 4, 4)) & page.rect
            page.get_pixmap(clip=clip, dpi=max(dpi, 260), annots=False).save(os.path.join(eq_dir, eid + ".png"))
            equations.append({"id": eid, "page": u["page"], "file": f"equations/{eid}.png",
                              "raw_text": u["text"]})

    # ---------------------------------------------------------------- title and front matter
    p1 = [u for u in units if u.get("kind") == "text" and u["page"] == 1 and not u.get("caption")
          and (u["nchar"] > 15 or (u["nchar"] >= 4 and cjk_ratio(u["text"]) > 0.3))
          and "@" not in u["text"]]
    title_idx = None
    if p1:
        cand = max(p1, key=lambda u: (round(u["size"], 1), u["nchar"]))
        if cand["size"] >= body_size + 0.8 and len(cand["text"]) < 400:
            cand["text"] = JOURNAL_LABEL_RE.sub("", cand["text"]).strip()
            cand["kind"], cand["level"] = "heading", 1
            title_idx = next(i for i, u in enumerate(units) if u is cand)
    # between the title and the first section heading: authors, affiliations, notes
    if title_idx is not None:
        for u in units[title_idx + 1:]:
            if u["page"] != 1:
                break
            if u.get("kind") != "text" or u.get("caption"):
                continue
            t = u["text"]
            if SECTION_WORDS.match(t) or NUMBERED_HEAD_RE.match(t) or u["nchar"] > 400:
                break
            u["front"] = True

    # ---------------------------------------------------------------- headings
    head_sizes = []
    for u in units:
        if u.get("kind") != "text" or u.get("level") or u.get("front") or u.get("footnote"):
            continue
        t = u["text"]
        if u.get("caption") or "@" in t:
            continue
        if cjk_ratio(t) > 0.3:
            if len(t) > 30:
                continue
        elif len(t) > 120 or len(t.split()) > 14:
            continue
        if re.search(r"\[\d{1,3}\]", t) or t.endswith(","):
            continue
        looks = (u["size"] > body_size + 0.4) or (u["bold"] > 0.6 and u["size"] >= body_size - 0.2)
        titleish = SECTION_WORDS.match(t) or NUMBERED_HEAD_RE.match(t)
        endsclean = not t.endswith((".", ";", ",", "。", "，", "；")) or bool(SECTION_WORDS.match(t))
        if (looks or titleish) and endsclean and not t.endswith((":", "：")):
            u["kind"] = "heading"
            head_sizes.append(u["size"])
    order = sorted({round(s, 1) for s in head_sizes}, reverse=True)
    level_of = {s: min(i + 1, 4) for i, s in enumerate(order)}
    has_title = any(x.get("level") == 1 for x in units)
    for u in units:
        if u.get("kind") == "heading" and not u.get("level"):
            lvl = level_of.get(round(u["size"], 1), 2)
            if SECTION_WORDS.match(u["text"]) or has_title:
                lvl = max(lvl, 2)
            u["level"] = max(1, min(lvl, 4))

    # ---------------------------------------------------------------- rejoin split paragraphs
    def open_ended(t):
        t = t.rstrip()
        if not t:
            return False
        if t.endswith("-") and not t.endswith("--"):
            return True
        return not re.search(r"[.!?:;)\]”\"'" + CJK_TERMINAL + r"]$", t)

    def continues(t):
        return (bool(re.match(r"^[a-z(\[]", t)) or bool(re.match(r"^[0-9]+[a-z%]", t))
                or (bool(t) and is_cjk(t[0]) and t[0] not in "「『（【《"))

    def movable(v):
        return v.get("kind") in ("figure", "table", "equation") or (
            v.get("kind") == "text" and (v.get("caption") or v.get("footnote")))

    i = 0
    while i < len(units):
        u = units[i]
        if (u.get("kind") == "text" and not u.get("caption") and not u.get("footnote")
                and not u.get("front") and u["nchar"] >= 40 and open_ended(u["text"])):
            j, hops = i + 1, 0
            while j < len(units) and movable(units[j]) and hops < 5:
                j, hops = j + 1, hops + 1
            if j < len(units):
                v = units[j]
                if (v.get("kind") == "text" and not v.get("caption") and not v.get("footnote")
                        and not v.get("front") and continues(v["text"])):
                    units.pop(j)
                    u["text"] = join_lines([u["text"], v["text"]])
                    u["nchar"] += v["nchar"]
                    continue                                   # the next break may follow
        i += 1

    # ---------------------------------------------------------------- references
    ref_start = None
    for idx, u in enumerate(units):
        if u.get("kind") == "heading" and REF_HEAD_RE.match(u["text"]):
            ref_start = idx
            break
    ref_entries = []
    if ref_start is not None:
        tail = []
        for u in units[ref_start + 1:]:
            if u.get("kind") == "heading" and POST_REF_HEAD_RE.match(u["text"]):
                break
            if u.get("kind") in ("text", "heading", "equation") and not u.get("caption"):
                tail.append(u)
        blob = join_lines([u["text"] for u in tail])            # repairs hyphens across blocks
        pats = [re.compile(r"\[(\d{1,3})\]\s*"),
                re.compile(r"(?:^|\s)(\d{1,3})\.\s+(?=[A-Z\u00c0-\u017e\u4e00-\u9fff])"),
                re.compile(r"(?:^|\s)(\d{1,3})\s+(?=[A-Z][a-z]+[, ])")]
        best = []
        for pat in pats:
            spans, last = [], 0
            for m in pat.finditer(blob):
                num = int(m.group(1))
                if last < num <= last + 3:                      # sequential, tolerant of <=2 missing
                    spans.append((num, m.start(), m.end()))
                    last = num
            if len(spans) > len(best):
                best = spans
        if len(best) >= 3:
            for k, (num, st, en) in enumerate(best):
                end = best[k + 1][1] if k + 1 < len(best) else len(blob)
                txt = re.sub(r"\s+", " ", blob[en:end]).strip(" ;,")
                if txt:
                    ref_entries.append((num, txt))
            nums = [x for x, _ in ref_entries]
            missing = [x for x in range(nums[0], nums[-1] + 1) if x not in nums]
            if missing:
                warnings.append(f"reference numbers not found in text: {missing}")
        elif tail:
            num = 0
            for u in tail:
                t = re.sub(r"^\s*\[?(\d{1,3})\]?[\.\)]?\s+", "", u["text"]).strip()
                if len(t) > 25:
                    num += 1
                    ref_entries.append((num, t))
            warnings.append("references had no reliable numbering; numbered by block order")
        if ref_entries:
            consumed = {id(u) for u in tail}
            head = units[ref_start]
            refs_unit = {"kind": "refs", "title": head["text"], "entries": ref_entries,
                         "page": head["page"], "rect": head["rect"]}
            units = units[:ref_start] + [refs_unit] + [u for u in units[ref_start + 1:]
                                                       if id(u) not in consumed]

    # ---------------------------------------------------------------- emit markdown
    out = []
    for u in units:
        k = u.get("kind")
        if k == "heading":
            lvl = u.get("level", 2)
            m = SPLIT_HEAD_RE.match(u["text"])
            if m and lvl > 1:
                out.append(f"{'#' * lvl} {m.group(1)}")
                out.append(f"{'#' * min(lvl + 1, 6)} {m.group(2)}")
            else:
                out.append(f"{'#' * lvl} {u['text']}")
        elif k == "figure":
            out.append(f"![{u['id']}](images/{u['id']}.png)\n\n<!-- MDC:FIG:{u['id']} -->")
        elif k == "equation":
            out.append(f"<!-- MDC:EQ:{u['id']} -->")
        elif k == "table":
            out.append(u["md"])
        elif k == "refs":
            title = u["title"] if not re.match(r"^\s*\d", u["title"]) else "References"
            out.append(f"## {title}")
            out.extend(f"{num}. {t}" for num, t in u["entries"])
        elif k == "text":
            t = u["text"]
            if u.get("caption"):
                cap = re.sub(r"\s+", " ", t).strip()
                out.append(f"_<u>{cap}</u>_")
            elif BULLET_RE.match(t) and len(t) < 400:
                out.append(re.sub(BULLET_RE, "- ", t, count=1))
            else:
                out.append(t)

    md = "\n\n".join(x for x in out if x and x.strip())
    md = re.sub(r"\n{3,}", "\n\n", md).strip() + "\n"

    stem = os.path.splitext(os.path.basename(pdf_path))[0]
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem)[:80] or "document"
    md_path = os.path.join(outdir, stem + ".md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)

    cap_fig = sum(1 for u in units if u.get("kind") == "text" and u.get("caption") and FIGCAP_RE.match(u["text"]))
    cap_tab = sum(1 for u in units if u.get("kind") == "text" and u.get("caption") and TABCAP_RE.match(u["text"]))
    n_tab = sum(1 for u in units if u.get("kind") == "table")
    if cap_fig != len(figures):
        warnings.append(f"figure captions={cap_fig} but figure images={len(figures)}: check pages against the PDF")
    if cap_tab != n_tab:
        warnings.append(f"table captions={cap_tab} but markdown tables={n_tab}: check pages against the PDF")

    samples = list(declared_samples)
    for reason in ("declared", "layer", "transparent", "large-light", "recurring", "rotated"):
        samples.extend(wm_samples.get(reason, []))
    worklist = {
        "version": __version__, "scanned": False, "pdf": os.path.basename(pdf_path), "pages": n,
        "markdown": os.path.basename(md_path), "body_font_size": body_size,
        "figures": figures, "equations": equations,
        "tables": n_tab, "figure_captions": cap_fig, "table_captions": cap_tab,
        "table_stub_columns_recovered": stub_pages,
        "references": len(ref_entries),
        "reference_range": ([ref_entries[0][0], ref_entries[-1][0]] if ref_entries else None),
        "chrome_removed": sorted(chrome)[:20],
        "front_matter_removed": front_removed[:12],
        "watermarks": {
            "declared_sections_removed": declared,
            "hidden_layers": sorted(ocgs[x].get("name") for x in wm_ocgs),
            "text_removed": dict(wm_counts),
            "samples": samples[:20],
            "images_hidden": len(wm_images),
            "recurring_vector_marks_ignored": len(recurring_clusters),
            "axis_text_recovered": axis_recovered,
        },
        "warnings": warnings}
    with open(os.path.join(outdir, "_worklist.json"), "w", encoding="utf-8") as f:
        json.dump(worklist, f, indent=1, ensure_ascii=False)
    summary = {k: v for k, v in worklist.items() if k not in ("chrome_removed", "front_matter_removed")}
    # the label text belongs in the worklist file, not on stdout
    summary["figures"] = [{k: v for k, v in f.items() if k not in ("text", "cited_by")}
                          for f in figures]
    print(json.dumps(summary, indent=1, ensure_ascii=False)[:4000])
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Layout aware conversion of a scientific PDF to Markdown.")
    ap.add_argument("pdf")
    ap.add_argument("outdir")
    ap.add_argument("--dpi", type=int, default=220, help="resolution of figure crops (default 220)")
    ap.add_argument("--password", default=None, help="password for an encrypted PDF")
    ap.add_argument("--version", action="version", version=f"mdconvert {__version__}")
    a = ap.parse_args()
    sys.exit(extract(a.pdf, a.outdir, a.dpi, a.password))
