#!/usr/bin/env python3
"""
Build the synthetic PDFs used by the test suite and the example.

No third-party document is redistributed: everything here is generated.

    python3 tests/make_fixture.py fixture.pdf            # English two-column article
    python3 tests/make_fixture.py --cjk fixture_zh.pdf   # Traditional Chinese article

The English fixture carries every layout trap the extractor must handle: a running
header and page numbers, a licence notice above the title, an author line, columns,
controlled line-end hyphens, a display equation, a figure, a table whose row labels sit
outside the ruled grid, a reference list with a split word and a TeX-style accent,
content after the references, a paragraph that continues across a column break, and
five kinds of watermark.
"""
import sys

import pymupdf

PAGE = pymupdf.paper_rect("a4")
M = 56                      # page margin
GUT = 22                    # column gutter
COLW = (PAGE.width - 2 * M - GUT) / 2
LH = 11                     # body line height for hand-set lines

BODY1 = ("Arboviral surveillance depends on converting printed reports into machine readable "
         "text. Layout aware extraction preserves the reading order of multi-column pages, "
         "which a naive line sort destroys, and gives a high-level view of each document. "
         "This synthetic article carries a running header, page numbers, a display equation, "
         "one table, one figure and several watermarks, so that a converter can be checked "
         "against a known ground truth.")
BODY2 = ("Vector competence was summarised as the proportion of exposed mosquitoes with "
         "disseminated infection. Confidence intervals were obtained by the Wilson method. "
         "Each tissue received a classification before analysis, and the code needed to "
         "regenerate every number is distributed with the manuscript.")
METHODS = [                                   # hand-set so that the line breaks are known
    "The proportion of positive tissues rose with incubation",
    "time in every experimental group. A high-",
    "level summary was computed with a classi-",
    "fication rule described previously. The effect was",
    "largest between day 7 and day 14, after which the curve",
    "flattened. Sample sizes were fixed at 25 mosquitoes per",
    "group, which gives adequate precision.",
]
BODY4 = ("Vertical transmission is difficult to demonstrate in the field because progeny "
         "cannot be linked to a known parent. A laboratory design removes that ambiguity, "
         "at the cost of generalisability.")
REFS = [
    ["1. Meegan JM, Bailey CL. Rift Valley fever. In: Monath TP, editor. The",
     "arboviruses. Boca Raton: CRC Press; 1989. p. 51-76."],
    ["2. Turell MJ, Linthicum KJ, Beaman JR. Transmission of Rift Valley fever virus by",
     "adult mos-",
     "quitoes after ingestion of virus as larvae. Am J Trop Med Hyg. 1990;43(6):677-680."],
    ["3. M¨uller K, Doll´ar P. Recombining accents in extracted text. J Synth",
     "Doc. 2021;4(2):11-19."],
    ["4. Lumley S, Horton DL, Hernandez-Triana LLM. Rift Valley fever virus: strategies",
     "for maintenance, survival and vertical transmission. J Gen Virol. 2017;98(5):875-887."],
]
APPX_LEFT = ["Sensitivity analyses used the same tissue panel and the",
             "same laboratory protocol. To check robustness, the",
             "sensitivity analysis was"]
APPX_RIGHT = ["repeated with a stricter positivity threshold, and the",
              "ranking of the groups did not change."]


def header(page, pno):
    page.insert_text((M, 34), "Journal of Synthetic Vector Biology  |  Vol. 12, No. 3, 2026",
                     fontsize=7.5, fontname="helv", color=(0.35, 0.35, 0.35))
    page.insert_text((PAGE.width / 2 - 4, PAGE.height - 30), str(pno), fontsize=8.5, fontname="helv")
    page.draw_line((M, 40), (PAGE.width - M, 40), color=(0.6, 0.6, 0.6), width=0.4)


def centred(page, y, text, size, font="helv"):
    w = pymupdf.Font(font).text_length(text, fontsize=size)
    page.insert_text(((PAGE.width - w) / 2, y), text, fontsize=size, fontname=font)


def col_rect(i, top, bottom):
    x0 = M + i * (COLW + GUT)
    return pymupdf.Rect(x0, top, x0 + COLW, bottom)


def lines(page, x, y, rows, size=9, font="tiro"):
    for k, row in enumerate(rows):
        page.insert_text((x, y + k * LH), row, fontsize=size, fontname=font)


def declared_watermark(doc, page, text, pos):
    """Draw text wrapped in /Artifact <</Subtype /Watermark>> marked content, as Acrobat does."""
    page.insert_text(pos, text, fontsize=22, fontname="helv", color=(0.75, 0.75, 0.75))
    xref = page.get_contents()[-1]
    data = doc.xref_stream(xref)
    doc.update_stream(xref, b"/Artifact <</Type /Pagination /Subtype /Watermark>> BDC\n" + data + b"\nEMC\n")


def stamp_image():
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 80, 80), True)
    pix.clear_with(170)
    return pix


def build(path):
    doc = pymupdf.open()
    layer = doc.add_ocg("Watermark", on=True)
    stamp, stamp_xref = stamp_image(), 0

    def watermark_image(page):
        nonlocal stamp_xref
        r = pymupdf.Rect(6, 690, 86, 770)            # same place on every page
        if stamp_xref:
            page.insert_image(r, xref=stamp_xref)
        else:
            stamp_xref = page.insert_image(r, pixmap=stamp)

    # ---------------------------------------------------------- page 1
    p = doc.new_page(width=PAGE.width, height=PAGE.height)
    header(p, 1)
    p.insert_text((M, 50), "Provided proper attribution is provided, the publisher hereby grants "
                  "permission to reproduce the tables and figures for scholarly use.",
                  fontsize=6.5, fontname="helv")
    p.insert_textbox(pymupdf.Rect(M, 62, PAGE.width - M, 110),
                     "Layout aware conversion of two-column articles to Markdown",
                     fontsize=16, fontname="hebo", align=1)
    centred(p, 122, "A. Author*, B. Coauthor*", 9.5)
    centred(p, 135, "Department of Vector Biology, Synthetic University, Taipei", 8)

    p.insert_text((M, 160), "Abstract", fontsize=11, fontname="hebo")
    p.insert_textbox(col_rect(0, 166, 350), BODY1, fontsize=9, fontname="tiro")
    p.insert_text((M + COLW + GUT, 160), "Introduction", fontsize=11, fontname="hebo")
    p.insert_textbox(col_rect(1, 166, 350), BODY2, fontsize=9, fontname="tiro")

    p.insert_text((M, 372), "Methods", fontsize=11, fontname="hebo")
    lines(p, M, 386, METHODS)

    p.insert_textbox(pymupdf.Rect(M, 540, M + COLW, 570),
                     "p = k / n × 100        (1)", fontsize=10, fontname="tiit", align=1)

    fx = col_rect(1, 372, 520)                        # figure: bar chart, right column
    p.draw_rect(pymupdf.Rect(fx.x0, fx.y0, fx.x1, fx.y0 + 110), color=(0.2, 0.2, 0.2), width=0.7)
    for i, h in enumerate([28, 52, 76, 88]):
        bx = fx.x0 + 18 + i * 42
        p.draw_rect(pymupdf.Rect(bx, fx.y0 + 100 - h, bx + 24, fx.y0 + 100),
                    color=(0.1, 0.1, 0.1), fill=(0.45, 0.55, 0.75), width=0.4)
        p.insert_text((bx + 4, fx.y0 + 108), f"d{7 * (i + 1)}", fontsize=6, fontname="helv")
    p.insert_textbox(pymupdf.Rect(fx.x0, fx.y0 + 116, fx.x1, fx.y0 + 150),
                     "Fig 1. Disseminated infection by day post exposure. Bars show the "
                     "percentage of tissues testing positive in each group.",
                     fontsize=8, fontname="tiro")

    # watermarks: transparent diagonal text across the Methods paragraph, a declared
    # watermark, text on a watermark layer, and a recurring stamp image
    p.insert_text((60, 470), "CONFIDENTIAL", fontsize=30, fontname="hebo", color=(0.6, 0.6, 0.6),
                  morph=(pymupdf.Point(60, 470), pymupdf.Matrix(-30)), fill_opacity=0.25)
    declared_watermark(doc, p, "DO NOT COPY", (330, 700))
    p.insert_text((330, 740), "Internal review copy", fontsize=11, fontname="helv", oc=layer)
    watermark_image(p)

    # ---------------------------------------------------------- page 2
    p2 = doc.new_page(width=PAGE.width, height=PAGE.height)
    header(p2, 2)
    p2.insert_text((M, 60), "Results", fontsize=11, fontname="hebo")
    p2.insert_textbox(col_rect(0, 66, 300), BODY4, fontsize=9, fontname="tiro")

    tx = col_rect(1, 66, 300)                          # table: labels outside the ruled grid
    p2.insert_textbox(pymupdf.Rect(tx.x0, tx.y0, tx.x1, tx.y0 + 28),
                      "Table 1. Positive tissues by tissue type.", fontsize=8, fontname="tiro")
    grid_x0, cw, rh, y = tx.x0 + 80, (tx.width - 80) / 2, 18, tx.y0 + 30
    rows = [("", "Tested", "Positive"), ("Body", "25", "18"), ("Legs & Wings", "25", "12"),
            ("Saliva", "25", "10"), ("Ovaries", "25", "1")]
    for ri, (stub, a, b) in enumerate(rows):
        if stub:
            p2.insert_text((tx.x0, y + 12), stub, fontsize=8, fontname="tiro")
        for ci, cell in enumerate((a, b)):
            cr = pymupdf.Rect(grid_x0 + ci * cw, y, grid_x0 + (ci + 1) * cw, y + rh)
            p2.draw_rect(cr, color=(0.25, 0.25, 0.25), width=0.5)
            p2.insert_text((cr.x0 + 4, cr.y0 + 12), cell, fontsize=8,
                           fontname="hebo" if ri == 0 else "tiro")
        y += rh

    p2.insert_text((M, 330), "References", fontsize=11, fontname="hebo")
    y = 346
    for ref in REFS:
        lines(p2, M, y, ref, size=8)
        y += LH * len(ref) + 6

    p2.insert_text((tx.x0 + 10, tx.y0 + 105), "DRAFT", fontsize=60, fontname="hebo",
                   color=(0.86, 0.86, 0.86))          # large light text across the table
    watermark_image(p2)

    # ---------------------------------------------------------- page 3
    p3 = doc.new_page(width=PAGE.width, height=PAGE.height)
    header(p3, 3)
    p3.insert_text((M, 60), "Appendix", fontsize=11, fontname="hebo")
    lines(p3, M, 80, APPX_LEFT)                        # paragraph continues in column 2
    lines(p3, M + COLW + GUT, 80, APPX_RIGHT)
    watermark_image(p3)

    doc.save(path)
    doc.close()


def build_cjk(path):
    doc = pymupdf.open()
    p = doc.new_page(width=PAGE.width, height=PAGE.height)
    f = "china-t"
    centred(p, 72, "登革熱病媒蚊監測資料之版面分析", 16, f)
    centred(p, 92, "王小明, 李大華", 9.5, f)
    p.insert_text((M, 130), "摘要", fontsize=11.5, fontname=f)
    lines(p, M, 146, ["本研究描述一種雙欄版面的轉換方法，",
                      "用於將病媒蚊監測報告轉為可檢索的",
                      "文字。結果顯示閱讀順序得以保留。"], font=f)
    p.insert_text((M, 200), "結果", fontsize=11.5, fontname=f)
    lines(p, M, 216, ["各週捕獲數與陽性數如表一所示，",
                      "趨勢與圖一一致。"], font=f)

    fx = col_rect(1, 124, 204)                         # figure with a CJK caption
    p.draw_rect(fx, color=(0.2, 0.2, 0.2), width=0.7)
    for i, h in enumerate([30, 55, 45]):
        bx = fx.x0 + 30 + i * 60
        p.draw_rect(pymupdf.Rect(bx, fx.y1 - 8 - h, bx + 30, fx.y1 - 8),
                    color=(0.1, 0.1, 0.1), fill=(0.5, 0.6, 0.8), width=0.4)
    p.insert_text((fx.x0, fx.y1 + 40), "圖1 監測流程與每週捕獲趨勢", fontsize=9, fontname=f)

    tx = col_rect(1, 270, 350)                         # ruled table with a CJK caption
    p.insert_text((tx.x0, tx.y0 + 10), "表1 各週捕獲數與陽性數", fontsize=9, fontname=f)
    y = tx.y0 + 18
    for row in [("週次", "捕獲數", "陽性"), ("1", "120", "3"), ("2", "98", "1")]:
        for ci, cell in enumerate(row):
            cr = pymupdf.Rect(tx.x0 + ci * 45, y, tx.x0 + (ci + 1) * 45, y + 16)
            p.draw_rect(cr, color=(0.25, 0.25, 0.25), width=0.5)
            p.insert_text((cr.x0 + 4, cr.y0 + 11), cell, fontsize=9, fontname=f)
        y += 16

    p.insert_text((M, 400), "參考文獻", fontsize=11.5, fontname=f)
    lines(p, M, 416, ["1. 王小明, 李大華. 臺灣登革熱之流行病學研究回顧與展望. 臺灣醫學會雜誌. 2020;119:1-10.",
                      "2. 陳美玲. 社區病媒蚊密度調查方法之比較與建議. 臺灣公共衛生雜誌. 2019;38:22-30.",
                      "3. 林志強. 版面分析技術於醫學文獻數位典藏之應用. 資訊科學學報. 2021;12:5-15."], font=f)
    doc.save(path)
    doc.close()


def build_encrypted(src, dst, user_pw="secret"):
    doc = pymupdf.open(src)
    doc.save(dst, encryption=pymupdf.PDF_ENCRYPT_AES_256, owner_pw="owner-" + user_pw, user_pw=user_pw)
    doc.close()


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--cjk":
        out = args[1] if len(args) > 1 else "fixture_zh.pdf"
        build_cjk(out)
    else:
        out = args[0] if args else "fixture.pdf"
        build(out)
    print("wrote", out)
