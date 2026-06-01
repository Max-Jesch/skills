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
import json
import sys
from pathlib import Path

from pptx import Presentation
from pptx.enum.text import MSO_AUTO_SIZE
from pptx.oxml.ns import qn

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import iter_translatable_frames  # noqa: E402


def write_paragraph(tf, p_idx, text, warn):
    """Put `text` into paragraph p_idx, preserving the first run's formatting."""
    if p_idx >= len(tf.paragraphs):
        warn(f"paragraph index {p_idx} out of range")
        return
    runs = tf.paragraphs[p_idx].runs
    if not runs:
        warn(f"paragraph {p_idx} has no runs; left unchanged")
        return
    runs[0].text = text
    for r in runs[1:]:
        r.text = ""


def set_autofit(tf, font_scale=None, line_reduction=None):
    """Enable shrink-to-fit autofit, optionally with a baked scale."""
    tf.word_wrap = True
    tf.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE  # writes a well-formed normAutofit
    if font_scale is None and line_reduction is None:
        return
    bodyPr = tf._txBody.find(qn("a:bodyPr"))
    na = bodyPr.find(qn("a:normAutofit")) if bodyPr is not None else None
    if na is None:
        return
    if font_scale is not None:
        na.set("fontScale", str(int(round(float(font_scale) * 1000))))
    if line_reduction is not None:
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
