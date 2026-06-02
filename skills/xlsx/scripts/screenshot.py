#!/usr/bin/env python3
"""Render an .xlsx to PNG(s) so you can actually look at a formatted sheet.

Mirrors the "render and review with your own eyes" step from translate-pptx:
for reports and models where layout, number formats, and column widths matter,
a recalc-clean file can still look wrong. This converts the workbook to PDF via
LibreOffice, then each PDF page to a PNG via poppler's pdftoppm.

One PNG per printed page, not per sheet — a wide sheet spans several pages. Set
print areas / fit-to-width in the workbook if the pagination is unhelpful. This
is a visual proxy (LibreOffice fonts/pagination differ slightly from Excel), so
treat it as "is anything obviously broken," not pixel truth.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description="Render an .xlsx to PNG pages.")
    ap.add_argument("file", help="path to the .xlsx")
    ap.add_argument("-o", "--outdir", default="render", help="output directory (default ./render)")
    ap.add_argument("-r", "--dpi", type=int, default=110, help="render DPI (default 110)")
    args = ap.parse_args()

    path = Path(args.file)
    if not path.exists():
        print(f"error: {path} not found", file=sys.stderr)
        return 2

    soffice = shutil.which("soffice")
    pdftoppm = shutil.which("pdftoppm")
    if not soffice:
        print("error: soffice (LibreOffice) not on PATH", file=sys.stderr)
        return 2
    if not pdftoppm:
        print("error: pdftoppm (poppler) not on PATH", file=sys.stderr)
        return 2

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        profile = (Path(tmp) / "profile").as_uri()
        r = subprocess.run(
            [soffice, "--headless", f"-env:UserInstallation={profile}",
             "--convert-to", "pdf", "--outdir", tmp, str(path)],
            capture_output=True, text=True, timeout=300)
        pdf = Path(tmp) / (path.stem + ".pdf")
        if not pdf.exists():
            print(f"error: PDF conversion failed: {r.stderr.strip() or r.stdout.strip()}",
                  file=sys.stderr)
            return 1
        r = subprocess.run(
            [pdftoppm, "-png", "-r", str(args.dpi), str(pdf), str(outdir / "page")],
            capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            print(f"error: pdftoppm failed: {r.stderr.strip()}", file=sys.stderr)
            return 1

    pages = sorted(outdir.glob("page*.png"))
    print(f"wrote {len(pages)} page(s) to {outdir}/", file=sys.stderr)
    for p in pages:
        print(f"  {p}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
