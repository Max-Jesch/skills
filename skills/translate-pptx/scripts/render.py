#!/usr/bin/env python3
"""Render a .pptx to one PNG per slide so the model can eyeball the layout.

Usage:
    python render.py deck.de.pptx -o render/ [-f 3 -l 5] [-r 110]

Prints the PNG paths it produced (one per line). Read those images back to
check for text overflow, overlap, clipping, or cramped boxes.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pptx", help="presentation to render")
    ap.add_argument("-o", "--outdir", default="render", help="output dir")
    ap.add_argument("-r", "--dpi", type=int, default=110, help="render DPI")
    ap.add_argument("-f", "--first", type=int, help="first slide (1-based)")
    ap.add_argument("-l", "--last", type=int, help="last slide (1-based)")
    args = ap.parse_args()

    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        sys.exit("LibreOffice not found (install it, or `brew install --cask libreoffice`)")
    if not shutil.which("pdftoppm"):
        sys.exit("pdftoppm not found (`brew install poppler`)")

    pptx = Path(args.pptx).resolve()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as td:
        # A throwaway profile lets this run even if LibreOffice is open in the GUI.
        profile = (Path(td) / "profile").as_uri()
        subprocess.run(
            [soffice, "--headless", f"-env:UserInstallation={profile}",
             "--convert-to", "pdf", "--outdir", td, str(pptx)],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        pdf = Path(td) / (pptx.stem + ".pdf")
        if not pdf.exists():
            sys.exit("PDF conversion failed (LibreOffice produced no output)")

        cmd = ["pdftoppm", "-png", "-r", str(args.dpi)]
        if args.first:
            cmd += ["-f", str(args.first)]
        if args.last:
            cmd += ["-l", str(args.last)]
        cmd += [str(pdf), str(outdir / "slide")]
        subprocess.run(cmd, check=True)

    pngs = sorted(outdir.glob("slide*.png"))
    for p in pngs:
        print(p)
    print(f"rendered {len(pngs)} slide(s) to {outdir}/", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
