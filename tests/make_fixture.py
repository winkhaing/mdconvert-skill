#!/usr/bin/env python3
"""
Build a synthetic two-column article PDF used by the test suite and the example.

No third-party document is redistributed: everything here is generated.

    python3 tests/make_fixture.py fixture.pdf
"""
import sys

import pymupdf

PAGE = pymupdf.paper_rect("a4")
M = 56                      # page margin
GUT = 22                    # column gutter
COLW = (PAGE.width - 2 * M - GUT) / 2

BODY1 = ("Arboviral surveillance depends on converting printed reports into machine readable "
         "text. Layout aware extraction preserves the reading order of multi-column pages, "
         "which a naive line sort destroys. In this synthetic article we describe a two-column "
         "layout that carries a running header, a page number, a display equation, one table "
         "and one figure, so that a converter can be checked against a known ground truth.")
BODY2 = ("Vector competence was summarised as the proportion of exposed mosquitoes with "
         "disseminated infection. Confidence intervals were obtained by the Wilson method. "
         "All analyses were carried out in a reproducible environment, and the code needed to "
         "regenerate every number in this article is distributed with the manuscript so that "
         "an independent reader can repeat the calculation without contacting the authors.")
BODY3 = ("The proportion of positive tissues rose with incubation time in every experimental "
         "group. The effect was largest between day 7 and day 14, after which the curve "
         "flattened. Sample sizes were fixed in advance at 25 mosquitoes per group, which "
         "gives adequate precision for a difference of twenty percentage points.")
BODY4 = ("Vertical transmission is difficult to demonstrate in the field because progeny "
         "cannot be linked to a known parent. A laboratory design removes that ambiguity, "
         "at the cost of generalisability. Both limitations should be stated plainly when "
         "such results are used to parameterise a transmission model.")

REFS = [
    "Meegan JM, Bailey CL. Rift Valley fever. In: Monath TP, editor. The arboviruses. "
    "Boca Raton: CRC Press; 1989. p. 51-76.",
    "Turell MJ, Linthicum KJ, Beaman JR. Transmission of Rift Valley fever virus by adult "
    "mosquitoes after ingestion of virus as larvae. Am J Trop Med Hyg. 1990;43(6):677-680.",
    "Wilson EB. Probable inference, the law of succession, and statistical inference. "
    "J Am Stat Assoc. 1927;22(158):209-212.",
    "Lumley S, Horton DL, Hernandez-Triana LLM. Rift Valley fever virus: strategies for "
    "maintenance, survival and vertical transmission. J Gen Virol. 2017;98(5):875-887.",
]


def header(page, pno):
    page.insert_text((M, 34), "Journal of Synthetic Vector Biology  |  Vol. 12, No. 3, 2026",
                     fontsize=7.5, fontname="helv", color=(0.35, 0.35, 0.35))
    page.insert_text((PAGE.width / 2 - 4, PAGE.height - 30), str(pno), fontsize=8.5, fontname="helv")
    page.draw_line((M, 40), (PAGE.width - M, 40), color=(0.6, 0.6, 0.6), width=0.4)


def col_rect(i, top, bottom):
    x0 = M + i * (COLW + GUT)
    return pymupdf.Rect(x0, top, x0 + COLW, bottom)


def build(path):
    doc = pymupdf.open()

    # ---------------------------------------------------------- page 1
    p = doc.new_page(width=PAGE.width, height=PAGE.height)
    header(p, 1)
    p.insert_textbox(pymupdf.Rect(M, 58, PAGE.width - M, 110),
                     "Layout aware conversion of two-column articles to Markdown",
                     fontsize=16, fontname="hebo", align=1)
    p.insert_textbox(pymupdf.Rect(M, 112, PAGE.width - M, 132),
                     "A. Author, B. Coauthor", fontsize=9.5, fontname="helv", align=1)

    p.insert_text((M, 156), "Abstract", fontsize=11, fontname="hebo")
    p.insert_textbox(col_rect(0, 162, 340), BODY1, fontsize=9, fontname="tiro")
    p.insert_text((M + COLW + GUT, 156), "Introduction", fontsize=11, fontname="hebo")
    p.insert_textbox(col_rect(1, 162, 340), BODY2, fontsize=9, fontname="tiro")

    p.insert_text((M, 366), "Methods", fontsize=11, fontname="hebo")
    p.insert_textbox(col_rect(0, 372, 520), BODY3, fontsize=9, fontname="tiro")

    # display equation, left column
    p.insert_textbox(pymupdf.Rect(M, 540, M + COLW, 570),
                     "p = k / n × 100        (1)", fontsize=10, fontname="tiit", align=1)

    # figure: drawn box with a simple bar chart, right column
    fx = col_rect(1, 372, 520)
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

    # ---------------------------------------------------------- page 2
    p2 = doc.new_page(width=PAGE.width, height=PAGE.height)
    header(p2, 2)
    p2.insert_text((M, 60), "Results", fontsize=11, fontname="hebo")
    p2.insert_textbox(col_rect(0, 66, 300), BODY4, fontsize=9, fontname="tiro")

    # ruled table, right column
    tx = col_rect(1, 66, 300)
    rows = [["Day", "Tested", "Positive"], ["7", "25", "7"], ["14", "25", "13"],
            ["21", "25", "19"], ["28", "25", "22"]]
    rh, y = 18, tx.y0 + 30
    p2.insert_textbox(pymupdf.Rect(tx.x0, tx.y0, tx.x1, tx.y0 + 28),
                      "Table 1. Positive tissues by day post exposure.",
                      fontsize=8, fontname="tiro")
    for ri, row in enumerate(rows):
        for ci, cell in enumerate(row):
            cw = tx.width / 3
            cell_rect = pymupdf.Rect(tx.x0 + ci * cw, y, tx.x0 + (ci + 1) * cw, y + rh)
            p2.draw_rect(cell_rect, color=(0.25, 0.25, 0.25), width=0.5)
            p2.insert_text((cell_rect.x0 + 4, cell_rect.y0 + 12), cell, fontsize=8,
                           fontname="hebo" if ri == 0 else "tiro")
        y += rh

    p2.insert_text((M, 330), "References", fontsize=11, fontname="hebo")
    y = 340
    for i, r in enumerate(REFS, 1):
        box = pymupdf.Rect(M, y, M + COLW, y + 46)
        p2.insert_textbox(box, f"{i}. {r}", fontsize=8, fontname="tiro")
        y += 46

    doc.save(path)
    doc.close()


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "fixture.pdf")
    print("wrote", sys.argv[1] if len(sys.argv) > 1 else "fixture.pdf")
