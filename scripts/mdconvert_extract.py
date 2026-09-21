#!/usr/bin/env python3
"""
mdconvert_extract.py - layout-aware scientific PDF -> Markdown (deterministic stage).

Usage:
    python3 mdconvert_extract.py INPUT.pdf OUTDIR [--dpi 220]

Writes OUTDIR/<stem>.md, OUTDIR/images/*.png, OUTDIR/equations/*.png,
OUTDIR/_worklist.json  (figures + equations awaiting VLM passes).

Exits with code 3 and prints {"scanned": true, ...} if the PDF has no usable text layer.
"""
import argparse, json, os, re, sys
from collections import Counter

import pymupdf

# ---------------------------------------------------------------- patterns
CAPTION_RE = re.compile(
    r"^\s*(?:(Fig(?:ure|s)?|Table|Scheme|Chart|Box|Panel|Exhibit|Appendix\s+Table|Supplementary\s+(?:Fig(?:ure)?|Table))\s*\.?\s*"
    r"(S?\d+[A-Za-z]?|[IVXLC]+)\b|(Graphical\s+abstract|Central\s+illustration)\b)", re.I)
REF_HEAD_RE = re.compile(r"^\s*(references?(\s+and\s+notes)?|bibliography|literature\s+cited|reference\s+list)\s*:?\s*$", re.I)
SECTION_WORDS = re.compile(
    r"^\s*(?:\d+\.?\d*\.?\s+)?(abstract|summary|introduction|background|methods?|materials\s+and\s+methods|"
    r"patients\s+and\s+methods|study\s+design|results?|findings|discussion|conclusions?|limitations|"
    r"acknowledg(?:e)?ments?|funding|author\s+contributions|conflicts?\s+of\s+interest|"
    r"competing\s+interests|data\s+availability|ethics\s+statement|supplementary\s+material|"
    r"references?|bibliography)\s*:?\s*$", re.I)
NUMBERED_HEAD_RE = re.compile(r"^\s*(\d{1,2}(?:\.\d{1,2}){0,3})\.?\s+[A-Z]")
POST_REF_HEAD_RE = re.compile(r"^\s*(appendix|supplement|supporting\s+information|author\s+biograph)", re.I)
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
FIGCAP_RE = re.compile(r"^\s*(Fig|Scheme|Chart|Graphical\s+abstract|Central\s+illustration)", re.I)
BULLET_RE = re.compile(r"^\s*([•·▪◦‣–\-\*]|\(?[a-z]\)|\(?\d{1,2}[\.\)])\s+")


def norm_chrome(s):
    s = re.sub(r"\d+", "#", s)
    return re.sub(r"\s+", " ", s).strip().lower()


def rect_of(b):
    return pymupdf.Rect(b["bbox"])


def area(r):
    return max(0.0, r.width) * max(0.0, r.height)


def overlap_frac(a, b):
    inter = a & b
    return area(inter) / area(a) if area(a) > 0 else 0.0


# ---------------------------------------------------------------- text helpers
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
        if out.endswith("-") and not out.endswith("--") and re.match(r"^[a-z]", t):
            out = out[:-1] + t
        elif out.endswith("­"):
            out = out[:-1] + t
        else:
            out += " " + t
    return re.sub(r"\s+", " ", out).strip()


def block_lines(block):
    res = []
    for ln in block.get("lines", []):
        txt = "".join(sp["text"] for sp in ln.get("spans", []))
        if txt.strip():
            res.append(txt)
    return res


def block_font_profile(block):
    sizes, flags, fonts, nchar = Counter(), Counter(), Counter(), 0
    for ln in block.get("lines", []):
        for sp in ln.get("spans", []):
            n = len(sp["text"].strip())
            if not n:
                continue
            sizes[round(sp["size"], 1)] += n
            flags[sp["flags"]] += n
            fonts[sp["font"]] += n
            nchar += n
    size = sizes.most_common(1)[0][0] if sizes else 0.0
    font = fonts.most_common(1)[0][0] if fonts else ""
    bold = sum(n for f, n in flags.items() if f & 16) / nchar if nchar else 0.0
    ital = sum(n for f, n in flags.items() if f & 2) / nchar if nchar else 0.0
    mathfrac = sum(n for f, n in fonts.items() if MATH_FONT_RE.search(f) or "Ital" in f or "Obli" in f) / nchar if nchar else 0.0
    return size, font, bold, ital, nchar, mathfrac


def is_rotated(block):
    for ln in block.get("lines", []):
        d = ln.get("dir", (1.0, 0.0))
        if abs(d[0] - 1.0) > 0.02 or abs(d[1]) > 0.02:
            return True
    return False


# ---------------------------------------------------------------- reading order
def xy_cut(units, page_width, depth=0):
    """Recursive XY-cut. units: list of dicts with 'rect'. Returns reading-ordered list."""
    if len(units) <= 1 or depth > 12:
        return sorted(units, key=lambda u: (round(u["rect"].y0, 1), u["rect"].x0))

    # vertical cut (column gutter) -------------------------------------
    xs = sorted(units, key=lambda u: u["rect"].x0)
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

    # horizontal cut ---------------------------------------------------
    ys = sorted(units, key=lambda u: u["rect"].y0)
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


# ---------------------------------------------------------------- tables
def md_table(rows):
    rows = [["" if c is None else re.sub(r"\s+", " ", str(c)).replace("|", "\\|").strip() for c in r] for r in rows]
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    # drop fully empty columns
    keep = [i for i in range(width) if any(r[i] for r in rows)]
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


# ---------------------------------------------------------------- main extraction
def extract(pdf_path, outdir, dpi=220):
    doc = pymupdf.open(pdf_path)
    npages = doc.page_count
    os.makedirs(outdir, exist_ok=True)
    img_dir, eq_dir = os.path.join(outdir, "images"), os.path.join(outdir, "equations")

    # ---- scanned-PDF gate
    total_chars = sum(len(doc[i].get_text("text").strip()) for i in range(min(npages, 12)))
    sampled = min(npages, 12)
    if total_chars / max(sampled, 1) < 120:
        print(json.dumps({"scanned": True, "chars_per_page": round(total_chars / max(sampled, 1), 1),
                          "pages": npages}))
        return 3

    # ---- pass 1: page chrome (headers / footers / page numbers / watermarks)
    band_counter = Counter()
    for pno in range(npages):
        page = doc[pno]
        h = page.rect.height
        for b in page.get_text("blocks"):
            x0, y0, x1, y1, txt = b[0], b[1], b[2], b[3], b[4]
            if not txt.strip():
                continue
            if y1 < 0.09 * h or y0 > 0.91 * h:
                band_counter[norm_chrome(txt)] += 1
    chrome = {k for k, v in band_counter.items() if v >= max(2, int(0.35 * npages)) and len(k) < 200}

    units = []          # ordered document units
    figures, equations, warnings = [], [], []
    fig_seq = eq_seq = 0
    size_hist = Counter()

    for pno in range(npages):
        page = doc[pno]
        pr, pw, ph = page.rect, page.rect.width, page.rect.height
        page_units = []

        # ---- text blocks first: their geometry scores tables and figures
        allb = []
        for b in page.get_text("dict")["blocks"]:
            if b.get("type") != 0:
                continue
            lines = block_lines(b)
            if not lines:
                continue
            text = join_lines(lines)
            if not text:
                continue
            size, font, bold, ital, nchar, mathfrac = block_font_profile(b)
            allb.append({"rect": rect_of(b), "text": text, "size": size, "font": font,
                         "bold": bold, "ital": ital, "nchar": nchar, "mathfrac": mathfrac,
                         "page": pno + 1, "rot": is_rotated(b),
                         "caption": bool(CAPTION_RE.match(text))})

        def textcov(rect):
            a = area(rect)
            return sum(area(x["rect"] & rect) for x in allb) / a if a else 0.0

        # ---- tables. A candidate whose area is mostly graphics is a chart, not a table.
        table_rects, chart_rects = [], []
        try:
            for t in page.find_tables().tables:
                r = pymupdf.Rect(t.bbox)
                if area(r) < 100:
                    continue
                if textcov(r) < 0.40:
                    chart_rects.append(r)                  # plot axes misread as a grid
                    continue
                try:
                    rows = t.extract()
                except Exception:
                    continue
                if not rows or len(rows) < 2 or max(len(x) for x in rows) < 2:
                    continue
                if sum(1 for x in rows for c in x if c and str(c).strip()) < 4:
                    continue
                md = md_table(rows)
                if not md:
                    continue
                table_rects.append(r)
                page_units.append({"kind": "table", "rect": r, "md": md, "page": pno + 1})
        except Exception as e:
            warnings.append(f"page {pno+1}: table detection failed ({e})")

        # ---- keep the prose blocks
        tblocks = []
        for tb in allb:
            r, text = tb["rect"], tb["text"]
            if tb["rot"]:
                continue                                   # rotated watermark / spine label
            if norm_chrome(text) in chrome:
                continue
            if JUNK_RE.match(re.sub(r"\s+", "", text)):
                continue                                   # decorative rule / marker row
            if (r.y1 < 0.09 * ph or r.y0 > 0.91 * ph) and len(re.sub(r"[^\w]", "", text)) <= 6:
                continue                                   # bare page number
            if any(overlap_frac(r, tr) > 0.55 for tr in table_rects):
                continue                                   # swallowed by a table
            size_hist[tb["size"]] += tb["nchar"]
            tblocks.append(tb)

        caption_rects = [tb["rect"] for tb in tblocks if tb["caption"]]

        # ---- figure regions: raster placements, vector clusters, misread charts
        cand = list(chart_rects)
        for im in page.get_images(full=True):
            try:
                for r in page.get_image_rects(im[0]):
                    if area(r) > 0.012 * area(pr) and overlap_frac(r, pr) > 0.4 and area(r) < 0.96 * area(pr):
                        cand.append(pymupdf.Rect(r))
            except Exception:
                pass
        try:
            for r in page.cluster_drawings(x_tolerance=6, y_tolerance=6):
                r = pymupdf.Rect(r)
                if area(r) > 0.012 * area(pr) and r.width > 45 and r.height > 35 and area(r) < 0.92 * area(pr):
                    cand.append(r)
        except Exception:
            pass

        # iterative merge: grow regions until stable, but never across a caption
        merged = [pymupdf.Rect(r) for r in cand]
        changed = True
        while changed and merged:
            changed = False
            for i in range(len(merged)):
                for j in range(len(merged) - 1, i, -1):
                    a, b = merged[i], merged[j]
                    near = area(a & b) > 0 or (
                        (a + (-12, -12, 12, 12)) & b).is_valid and area((a + (-12, -12, 12, 12)) & b) > 0
                    if not near:
                        continue
                    u = pymupdf.Rect(a) | b
                    blocked = any(area(cr & u) > 0.5 * area(cr) and area(cr & a) < 0.2 * area(cr)
                                  and area(cr & b) < 0.2 * area(cr) for cr in caption_rects)
                    if blocked:
                        continue
                    merged[i] = u
                    merged.pop(j)
                    changed = True

        figs = []
        for m in merged:
            if any(overlap_frac(m, tr) > 0.5 for tr in table_rects):
                continue
            prose_in = any(tb["nchar"] > 130 and overlap_frac(tb["rect"], m) > 0.5
                           for tb in tblocks if not tb["caption"])
            cov = sum(area(tb["rect"] & m) for tb in tblocks if not tb["caption"]) / max(area(m), 1)
            if cov > 0.78 or prose_in:
                continue
            for cr in caption_rects:                       # never swallow the caption
                if area(cr & m) > 0.3 * area(cr):
                    if cr.y0 >= m.y0 + 0.5 * m.height:
                        m.y1 = min(m.y1, cr.y0 - 2)
                    else:
                        m.y0 = max(m.y0, cr.y1 + 2)
            if m.width > 40 and m.height > 40:
                figs.append(m)

        # caption-anchored fallback: a figure caption whose graphic was not detected
        for tb in tblocks:
            if not tb["caption"] or not FIGCAP_RE.match(tb["text"]):
                continue
            cr = tb["rect"]
            if any(min(f.x1, cr.x1) - max(f.x0, cr.x0) > 0.35 * cr.width and
                   (0 <= cr.y0 - f.y1 < 95 or 0 <= f.y0 - cr.y1 < 95) for f in figs):
                continue
            same_col = [t for t in tblocks if t is not tb and
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
                if page.get_pixmap(clip=band & pr, dpi=72).is_unicolor:
                    continue
                figs.append(band)
                break

        # one caption = one figure: union the panels that share a caption
        fcaps = [tb["rect"] for tb in tblocks if tb["caption"] and FIGCAP_RE.match(tb["text"])]
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

        for m in figs:
            fig_seq += 1
            fid = f"fig-p{pno+1:02d}-{fig_seq:02d}"
            os.makedirs(img_dir, exist_ok=True)
            clip = (pymupdf.Rect(m) + (-3, -3, 3, 3)) & pr
            page.get_pixmap(clip=clip, dpi=dpi).save(os.path.join(img_dir, fid + ".png"))
            page_units.append({"kind": "figure", "rect": pymupdf.Rect(m), "id": fid, "page": pno + 1})
            figures.append({"id": fid, "page": pno + 1, "file": f"images/{fid}.png"})

        fig_rects = [u["rect"] for u in page_units if u["kind"] == "figure"]

        for tb in tblocks:
            if not tb["caption"] and any(overlap_frac(tb["rect"], fr) > 0.6 for fr in fig_rects):
                continue                                   # axis tick / panel label
            tb["kind"] = "text"
            page_units.append(tb)

        units.extend(xy_cut(page_units, pw))

    # ---- attach nearest caption text to each figure (helps the VLM pass)
    for i, u in enumerate(units):
        if u.get("kind") != "figure":
            continue
        cap = None
        for j in list(range(i + 1, min(i + 4, len(units)))) + list(range(max(0, i - 2), i))[::-1]:
            v = units[j]
            if v.get("kind") == "text" and v.get("caption") and FIGCAP_RE.match(v["text"]):
                cap = v["text"][:300]
                break
        if cap:
            u["cap"] = cap
            for f in figures:
                if f["id"] == u["id"]:
                    f["caption"] = cap

    # ---------------------------------------------------------------- body font
    body_size = size_hist.most_common(1)[0][0] if size_hist else 10.0
    for s, n in size_hist.most_common(6):
        if n > 0.25 * sum(size_hist.values()):
            body_size = s
            break

    # ---------------------------------------------------------------- equations
    for u in units:
        if u.get("kind") != "text" or u.get("caption"):
            continue
        t = u["text"]
        alnum = sum(1 for c in t if c.isalnum())
        if len(t) > 300 or len(t.split()) > 30 or alnum < 3:
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
            page.get_pixmap(clip=clip, dpi=max(dpi, 260)).save(os.path.join(eq_dir, eid + ".png"))
            equations.append({"id": eid, "page": u["page"], "file": f"equations/{eid}.png",
                              "raw_text": u["text"]})

    # ---------------------------------------------------------------- title
    p1 = [u for u in units if u.get("kind") == "text" and u["page"] == 1 and not u.get("caption")
          and u["nchar"] > 15 and "@" not in u["text"]]
    if p1:
        cand = max(p1, key=lambda u: (round(u["size"], 1), u["nchar"]))
        if cand["size"] >= body_size + 0.8 and len(cand["text"]) < 400:
            cand["text"] = JOURNAL_LABEL_RE.sub("", cand["text"]).strip()
            cand["kind"], cand["level"] = "heading", 1

    # ---------------------------------------------------------------- headings
    head_sizes = []
    for u in units:
        if u.get("kind") != "text" or u.get("level"):
            continue
        t = u["text"]
        if u.get("caption") or len(t) > 120 or len(t.split()) > 14 or "@" in t:
            continue
        if re.search(r"\[\d{1,3}\]", t) or t.endswith(","):
            continue
        looks = (u["size"] > body_size + 0.4) or (u["bold"] > 0.6 and u["size"] >= body_size - 0.2)
        titleish = SECTION_WORDS.match(t) or NUMBERED_HEAD_RE.match(t)
        endsclean = not t.endswith((".", ";", ",")) or bool(SECTION_WORDS.match(t))
        if (looks or titleish) and endsclean and not t.endswith(":"):
            u["kind"] = "heading"
            head_sizes.append(u["size"])
    order = sorted({round(s, 1) for s in head_sizes}, reverse=True)
    level_of = {s: min(i + 1, 4) for i, s in enumerate(order)}
    for u in units:
        if u.get("kind") == "heading" and not u.get("level"):
            lvl = level_of.get(round(u["size"], 1), 2)
            if SECTION_WORDS.match(u["text"]):
                lvl = max(lvl, 2)
            if any(x.get("level") == 1 for x in units):
                lvl = max(lvl, 2)
            u["level"] = max(1, min(lvl, 4))

    # ---------------------------------------------------------------- rejoin interrupted paragraphs
    def open_ended(t):
        return bool(t) and not re.search(r"[.!?:;\)\]”\"]\s*$", t) or t.endswith("-")

    def continues(t):
        return bool(re.match(r"^[a-z\(\[]", t)) or bool(re.match(r"^[0-9]+[a-z%]", t))

    i = 0
    while i < len(units):
        u = units[i]
        if u.get("kind") == "text" and not u.get("caption") and open_ended(u["text"]):
            j, moved = i + 1, []
            while j < len(units) and units[j].get("kind") in ("figure", "table", "equation") or \
                  (j < len(units) and units[j].get("kind") == "text" and units[j].get("caption")):
                moved.append(units[j]); j += 1
                if len(moved) > 4:
                    break
            if moved and j < len(units) and units[j].get("kind") == "text" and not units[j].get("caption") \
               and continues(units[j]["text"]):
                nxt = units.pop(j)
                u["text"] = join_lines([u["text"], nxt["text"]])
                u["rect"] = u["rect"] | nxt["rect"]
        i += 1

    # ---------------------------------------------------------------- references
    ref_start = None
    for idx, u in enumerate(units):
        if u.get("kind") == "heading" and REF_HEAD_RE.match(u["text"]):
            ref_start = idx
            break
    ref_entries, ref_warn = [], []
    if ref_start is not None:
        tail = []
        for u in units[ref_start + 1:]:
            if u.get("kind") == "heading" and POST_REF_HEAD_RE.match(u["text"]):
                break
            if u.get("kind") in ("text", "heading", "equation") and not u.get("caption"):
                tail.append(u)
        blob = " ".join(u["text"] for u in tail)
        pats = [re.compile(r"\[(\d{1,3})\]\s*"),
                re.compile(r"(?:^|\s)(\d{1,3})\.\s+(?=[A-Z\u00c0-\u017e])"),
                re.compile(r"(?:^|\s)(\d{1,3})\s+(?=[A-Z][a-z]+[, ])")]
        best = []
        for pat in pats:
            spans, last = [], 0
            for m in pat.finditer(blob):
                n = int(m.group(1))
                if last < n <= last + 3:            # sequential, tolerant of <=2 missing
                    spans.append((n, m.start(), m.end()))
                    last = n
            if len(spans) > len(best):
                best = spans
        if len(best) >= 3:
            for k, (n, st, en) in enumerate(best):
                end = best[k + 1][1] if k + 1 < len(best) else len(blob)
                txt = re.sub(r"\s+", " ", blob[en:end]).strip(" ;,")
                if txt:
                    ref_entries.append((n, txt))
            nums = [n for n, _ in ref_entries]
            missing = [i for i in range(nums[0], nums[-1] + 1) if i not in nums]
            if missing:
                ref_warn.append(f"reference numbers not found in text: {missing}")
        elif tail:
            n = 0
            for u in tail:
                t = re.sub(r"^\s*\[?(\d{1,3})\]?[\.\)]?\s+", "", u["text"]).strip()
                if len(t) > 25:
                    n += 1
                    ref_entries.append((n, t))
            ref_warn.append("references had no reliable numbering; numbered by block order")
        if ref_entries:
            consumed = {id(u) for u in tail}
            units = units[:ref_start] + [u for u in units[ref_start + 1:]
                                         if id(u) not in consumed]
    warnings.extend(ref_warn)

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
        elif k == "text":
            t = u["text"]
            if u.get("caption"):
                t = re.sub(r"\s+", " ", t).strip()
                out.append(f"_<u>{t}</u>_")
            elif BULLET_RE.match(t) and len(t) < 400:
                out.append(re.sub(BULLET_RE, "- ", t, count=1))
            else:
                out.append(t)
    if ref_entries:
        out.append("## References")
        out.extend(f"{n}. {t}" for n, t in ref_entries)

    md = "\n\n".join(x for x in out if x and x.strip())
    md = re.sub(r"\n{3,}", "\n\n", md).strip() + "\n"

    stem = os.path.splitext(os.path.basename(pdf_path))[0]
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem)[:80]
    md_path = os.path.join(outdir, stem + ".md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)

    cap_fig = sum(1 for u in units if u.get("kind") == "text" and u.get("caption") and FIGCAP_RE.match(u["text"]))
    cap_tab = sum(1 for u in units if u.get("kind") == "text" and u.get("caption")
                  and re.match(r"^\s*(Table|Appendix\s+Table|Supplementary\s+Table)", u["text"], re.I))
    n_tab = sum(1 for u in units if u.get("kind") == "table")
    if cap_fig != len(figures):
        warnings.append(f"figure captions={cap_fig} but figure images={len(figures)}: check pages against the PDF")
    if cap_tab != n_tab:
        warnings.append(f"table captions={cap_tab} but markdown tables={n_tab}: check pages against the PDF")

    worklist = {"scanned": False, "pdf": os.path.basename(pdf_path), "pages": npages,
                "markdown": os.path.basename(md_path), "body_font_size": body_size,
                "figures": figures, "equations": equations,
                "tables": n_tab, "figure_captions": cap_fig, "table_captions": cap_tab,
                "references": len(ref_entries),
                "reference_range": ([ref_entries[0][0], ref_entries[-1][0]] if ref_entries else None), "chrome_removed": sorted(chrome)[:20],
                "warnings": warnings}
    with open(os.path.join(outdir, "_worklist.json"), "w", encoding="utf-8") as f:
        json.dump(worklist, f, indent=1)
    print(json.dumps({k: v for k, v in worklist.items() if k != "chrome_removed"}, indent=1)[:4000])
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf"); ap.add_argument("outdir"); ap.add_argument("--dpi", type=int, default=220)
    a = ap.parse_args()
    sys.exit(extract(a.pdf, a.outdir, a.dpi))
