#!/usr/bin/env python3
"""Write translations from a job JSON back into a .pptx and fix text fitting.

Usage:
    python apply.py deck.pptx job.json -o deck.de.pptx

For every "slide"-kind text frame this also turns on PowerPoint's native
shrink-to-fit autofit (<a:normAutofit/>), so the deck re-fits itself when
opened. When you need to force a frame smaller than autofit manages on its
own, add an optional "font_scale" (1-100, percent) and/or "line_reduction"
(0-20, percent) to that frame object in the JSON; apply.py bakes them into
the normAutofit element. Pick those numbers by looking at rendered slides,
not by computing them.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

from pptx import Presentation
from pptx.enum.text import MSO_AUTO_SIZE
from pptx.oxml.ns import qn

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import iter_translatable_frames  # noqa: E402

# python-pptx represents an in-paragraph line break (<a:br/>) as a vertical tab
# (U+000B) in TextFrame/paragraph .text, so extract.py emits it into "src". A
# literal newline can show up the same way. Both must round-trip back to real
# <a:br/> elements — if we just assign them to run.text, python-pptx escapes the
# control char as the literal string "_x000B_", which renders as visible garbage.
_LINE_BREAK_CHARS = ("\x0b", "\n", "\r")


def _split_line_breaks(text):
    """Split on any line-break char, returning the list of text segments."""
    segments = [text]
    for ch in _LINE_BREAK_CHARS:
        segments = [piece for seg in segments for piece in seg.split(ch)]
    return segments


def write_paragraph(tf, p_idx, text, warn):
    """Put `text` into paragraph p_idx, preserving the first run's formatting.

    Line breaks in `text` (vertical tab / newline) are re-materialised as real
    <a:br/> elements that inherit the first run's formatting, instead of being
    escaped into a literal "_x000B_" string.
    """
    if p_idx >= len(tf.paragraphs):
        warn(f"paragraph index {p_idx} out of range")
        return
    runs = tf.paragraphs[p_idx].runs
    if not runs:
        warn(f"paragraph {p_idx} has no runs; left unchanged")
        return

    segments = _split_line_breaks(text)
    first = runs[0]
    first.text = segments[0]
    for r in runs[1:]:
        r.text = ""

    if len(segments) == 1:
        return

    # Rebuild the trailing segments as <a:br/> + <a:r> pairs cloned from the
    # first run, inserted right after it so formatting carries over.
    r_el = first._r
    rPr = r_el.find(qn("a:rPr"))
    parent = r_el.getparent()
    insert_at = list(parent).index(r_el) + 1
    for seg in segments[1:]:
        br = r_el.makeelement(qn("a:br"), {})
        if rPr is not None:
            br.append(copy.deepcopy(rPr))
        new_r = copy.deepcopy(r_el)
        new_t = new_r.find(qn("a:t"))
        if new_t is None:
            new_t = new_r.makeelement(qn("a:t"), {})
            new_r.append(new_t)
        new_t.text = seg
        parent.insert(insert_at, br)
        parent.insert(insert_at + 1, new_r)
        insert_at += 2


def _scale_explicit_sizes(tf, factor):
    """Multiply every explicit font size (sz, in 1/100 pt) in the frame by factor.

    LibreOffice — and any viewer/exporter that does not recompute autofit on open
    (e.g. PDF export) — IGNORES the normAutofit fontScale attribute. So baking
    fontScale alone leaves the render looking exactly as overflowed as before.
    Scaling the explicit run sizes instead makes the force-scale render correctly
    everywhere. Runs that inherit their size from the placeholder/theme have no
    sz attribute and are left to normAutofit (PowerPoint re-fits them on open).
    """
    txBody = tf._txBody
    scaled = 0
    for tag in ("a:rPr", "a:defRPr", "a:endParaRPr"):
        for el in txBody.iter(qn(tag)):
            sz = el.get("sz")
            if sz is None:
                continue
            new = max(100, int(round(int(sz) * factor)))  # floor at 1pt
            el.set("sz", str(new))
            scaled += 1
    return scaled


def set_autofit(tf, font_scale=None, line_reduction=None):
    """Enable shrink-to-fit autofit, optionally with a forced scale.

    A bare <a:normAutofit/> lets PowerPoint re-fit on open. When font_scale is
    given we ALSO shrink the explicit run sizes directly (see
    _scale_explicit_sizes) so the scale is honored by every renderer, not just
    PowerPoint. We deliberately do NOT also bake fontScale, to avoid PowerPoint
    double-shrinking the already-reduced sizes.
    """
    tf.word_wrap = True
    tf.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE  # writes a well-formed normAutofit
    if font_scale is not None:
        _scale_explicit_sizes(tf, float(font_scale) / 100.0)
    if line_reduction is not None:
        bodyPr = tf._txBody.find(qn("a:bodyPr"))
        na = bodyPr.find(qn("a:normAutofit")) if bodyPr is not None else None
        if na is not None:
            na.set("lnSpcReduction", str(int(round(float(line_reduction) * 1000))))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pptx", help="source presentation")
    ap.add_argument("job", help="translated job JSON")
    ap.add_argument("-o", "--out", help="output .pptx (default: <stem>.<lang>.pptx)")
    args = ap.parse_args()

    doc = json.loads(Path(args.job).read_text(encoding="utf-8"))
    frames_by_id = {f["id"]: f for f in doc["frames"]}
    include_notes = doc.get("include_notes", True)

    prs = Presentation(args.pptx)

    warnings: list[str] = []
    written = 0
    for fid, item in enumerate(
            iter_translatable_frames(prs, include_notes=include_notes)):
        frame = frames_by_id.get(fid)
        if frame is None:
            warnings.append(f"frame {fid} missing from job JSON; left as source")
            continue

        def warn(msg, _fid=fid):
            warnings.append(f"frame {_fid}: {msg}")

        for p in frame.get("paras", []):
            tgt = (p.get("tgt") or "").strip()
            if not tgt:
                warn(f"paragraph {p.get('i')} has empty tgt; left as source")
                continue
            write_paragraph(item["tf"], p["i"], p["tgt"], warn)
            written += 1

        if item["autofit_ok"] and frame.get("autofit", True):
            set_autofit(item["tf"],
                        font_scale=frame.get("font_scale"),
                        line_reduction=frame.get("line_reduction"))

    out = args.out
    if not out:
        stem = Path(args.pptx).stem
        out = f"{stem}.{doc.get('target_lang', 'out')}.pptx"
    prs.save(out)

    print(f"wrote {written} paragraphs -> {out}", file=sys.stderr)
    if warnings:
        print(f"{len(warnings)} warning(s):", file=sys.stderr)
        for w in warnings[:50]:
            print(f"  - {w}", file=sys.stderr)
        if len(warnings) > 50:
            print(f"  ... and {len(warnings) - 50} more", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
