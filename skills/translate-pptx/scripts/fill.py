#!/usr/bin/env python3
"""Merge a flat {"<id>.<i>": "translation"} map into an extracted job JSON.

Usage:
    python3 fill.py job.json translations.json -o job.filled.json
    # or read the map from stdin:
    cat translations.json | python3 fill.py job.json - -o job.filled.json

Why this exists: NEVER re-author the whole job.json by hand. extract.py already
wrote a valid file (the vertical-tab line breaks and curly quotes in `src` are
correctly escaped). Re-typing all ~1000 lines is how the file ends up with a
raw control char or a botched escape and fails to parse. Instead you supply only
the translations as a small flat map; this script drops them into the matching
`tgt` fields and leaves every other byte untouched, so the output is always
valid JSON.

Map format — one entry per paragraph, key is "<frame id>.<paragraph i>":

    {
      "0.0": "IBM Dev Day:\nBob-Edition\nEnablement vor dem Hackathon",
      "1.0": "Maximilian Jesch",
      "1.1": "Produktmanager, IBM Bob"
    }

Use "\n" inside a value to mark an in-box line break (apply.py turns it into a
real <a:br/>). Copy a paragraph's source verbatim if it should stay untranslated.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("job", help="job JSON from extract.py")
    ap.add_argument("map", help='translations map ("-" for stdin)')
    ap.add_argument("-o", "--out", help="output JSON (default: overwrite job)")
    args = ap.parse_args()

    doc = json.loads(Path(args.job).read_text(encoding="utf-8"))
    raw = sys.stdin.read() if args.map == "-" else Path(args.map).read_text(encoding="utf-8")
    tmap = json.loads(raw)

    # Index the expected paragraph keys so we can report gaps precisely.
    expected = {f"{f['id']}.{p['i']}" for f in doc["frames"] for p in f["paras"]}
    given = set(tmap)

    filled = 0
    for f in doc["frames"]:
        for p in f["paras"]:
            key = f"{f['id']}.{p['i']}"
            if key in tmap:
                p["tgt"] = tmap[key]
                filled += 1

    out = args.out or args.job
    Path(out).write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8")

    missing = sorted(expected - given, key=lambda k: tuple(map(int, k.split("."))))
    unknown = sorted(given - expected, key=lambda k: tuple(map(int, k.split("."))))
    print(f"filled {filled}/{len(expected)} paragraphs -> {out}", file=sys.stderr)
    if missing:
        print(f"  {len(missing)} paragraph(s) still untranslated: "
              f"{', '.join(missing[:20])}{' …' if len(missing) > 20 else ''}",
              file=sys.stderr)
    if unknown:
        print(f"  {len(unknown)} map key(s) match no paragraph (ignored): "
              f"{', '.join(unknown[:20])}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
