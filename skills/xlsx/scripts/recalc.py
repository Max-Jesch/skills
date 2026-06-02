#!/usr/bin/env python3
"""Recalculate an .xlsx in place and report any formula errors.

openpyxl writes formulas but never their results, so a freshly written sheet
has no cached values — reading it back with data_only=True yields None until a
real spreadsheet engine evaluates it. This script does that evaluation and then
scans every cell for error values (#REF!, #DIV/0!, ...), which is how you verify
a model is actually sound rather than just syntactically valid.

Engines, in order of fidelity:
  libreoffice  - headless soffice forced to recalculate on load. Reliable, no
                 GUI, no prompts. Default. Close to Excel, not byte-identical.
  excel        - drive the installed Microsoft Excel via AppleScript (macOS).
                 True Excel evaluation (use for Excel-only functions), but
                 fragile: Excel must be launched and past any sign-in/first-run
                 dialog, and the first run triggers a macOS automation prompt.
  auto         - libreoffice (the dependable path). Ask for --engine excel
                 explicitly when you need exact Excel fidelity.
"""
from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ERROR_VALUES = {"#REF!", "#DIV/0!", "#VALUE!", "#N/A", "#NAME?",
                "#NULL!", "#NUM!", "#SPILL!", "#CALC!", "#GETTING_DATA"}

EXCEL_APP = Path("/Applications/Microsoft Excel.app")


def have_excel() -> bool:
    return platform.system() == "Darwin" and EXCEL_APP.exists()


def have_soffice() -> str | None:
    return shutil.which("soffice")


def recalc_excel(path: Path) -> None:
    p = str(path)
    script = f'''
with timeout of 580 seconds
    tell application "Microsoft Excel"
        activate
        set display alerts to false
        open workbook workbook file name "{p}"
        calculate
        close active workbook saving yes
        set display alerts to true
    end tell
end timeout
'''
    r = subprocess.run(["osascript", "-e", script],
                       capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        raise RuntimeError(
            "Excel recalc failed: " + (r.stderr.strip() or r.stdout.strip()) +
            "\n(Excel must be launched and past any sign-in/first-run dialog; "
            "or use --engine libreoffice.)")


# Force LibreOffice to recalculate every formula when it loads a file, rather
# than trusting (absent) cached values. Mode 0 = "Always recalculate". With this
# set, a plain --convert-to round-trip evaluates all formulas and writes the
# results back as cached values — more reliable than driving a Basic macro,
# which a fresh profile's macro-security settings tend to block.
REGISTRY = '''<?xml version="1.0" encoding="UTF-8"?>
<oor:items xmlns:oor="http://openoffice.org/2001/registry" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
 <item oor:path="/org.openoffice.Office.Calc/Formula/Load"><prop oor:name="OOXMLRecalcMode" oor:op="fuse"><value>0</value></prop></item>
 <item oor:path="/org.openoffice.Office.Calc/Formula/Load"><prop oor:name="ODFRecalcMode" oor:op="fuse"><value>0</value></prop></item>
</oor:items>
'''


def recalc_libreoffice(path: Path, soffice: str) -> None:
    path = path.resolve()
    with tempfile.TemporaryDirectory() as tmp:
        profile = Path(tmp) / "profile"
        (profile / "user").mkdir(parents=True)
        (profile / "user" / "registrymodifications.xcu").write_text(REGISTRY)
        outdir = Path(tmp) / "out"
        outdir.mkdir()
        r = subprocess.run(
            [soffice, "--headless", "--norestore", "--nologo",
             f"-env:UserInstallation={profile.as_uri()}",
             "--convert-to", "xlsx:Calc MS Excel 2007 XML",
             "--outdir", str(outdir), str(path)],
            capture_output=True, text=True, timeout=300)
        produced = outdir / (path.stem + ".xlsx")
        if not produced.exists():
            raise RuntimeError(f"LibreOffice recalc failed: {r.stderr.strip() or r.stdout.strip()}")
        shutil.copyfile(produced, path)


def scan_errors(path: Path) -> list[tuple[str, str, str]]:
    import openpyxl
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    hits: list[tuple[str, str, str]] = []
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                v = cell.value
                if isinstance(v, str) and v in ERROR_VALUES:
                    hits.append((ws.title, cell.coordinate, v))
    wb.close()
    return hits


def main() -> int:
    ap = argparse.ArgumentParser(description="Recalculate an .xlsx and report formula errors.")
    ap.add_argument("file", help="path to the .xlsx to recalculate (edited in place)")
    ap.add_argument("--engine", choices=["auto", "excel", "libreoffice"], default="auto")
    ap.add_argument("--no-scan", action="store_true", help="skip the formula-error scan")
    args = ap.parse_args()

    path = Path(args.file)
    if not path.exists():
        print(f"error: {path} not found", file=sys.stderr)
        return 2

    engine = args.engine
    if engine == "auto":
        engine = "libreoffice" if have_soffice() else ("excel" if have_excel() else "libreoffice")

    if engine == "excel":
        if not have_excel():
            print("error: Microsoft Excel not found at /Applications", file=sys.stderr)
            return 2
        print(f"recalculating {path.name} with Microsoft Excel ...", file=sys.stderr)
        recalc_excel(path)
    else:
        soffice = have_soffice()
        if not soffice:
            print("error: soffice (LibreOffice) not on PATH", file=sys.stderr)
            return 2
        print(f"recalculating {path.name} with LibreOffice ...", file=sys.stderr)
        recalc_libreoffice(path, soffice)

    if args.no_scan:
        print("recalc done (scan skipped)", file=sys.stderr)
        return 0

    hits = scan_errors(path)
    if not hits:
        print("recalc done — no formula errors found", file=sys.stderr)
        return 0
    print(f"recalc done — {len(hits)} formula error(s):", file=sys.stderr)
    for sheet, coord, err in hits[:50]:
        print(f"  {sheet}!{coord}: {err}", file=sys.stderr)
    if len(hits) > 50:
        print(f"  ... and {len(hits) - 50} more", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
