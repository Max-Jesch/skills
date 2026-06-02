---
name: edit-pptx
description: >-
  Edit and extend an existing PowerPoint (.pptx) deck — change wording, fix
  numbers, rewrite bullets, add new slides (cloned from an existing slide to keep
  the design, or from a layout), and drop in text boxes, images, and tables —
  while preserving the original formatting and keeping text fitting its boxes.
  Use whenever the user asks to modify, update, revise, extend, add slides to, or
  restructure a .pptx / PowerPoint / slides file (anything beyond translating it,
  which is translate-pptx's job).
---

# Edit & extend PowerPoint decks (fit-aware)

Modify the content of a `.pptx` and add to it, while keeping its design intact
and making any text you touch **actually FIT its boxes**.

The edits themselves — what to say, which slide to clone, where a box goes — are
**your** judgment, not an external API's. Scripts only inventory the deck, apply
a list of operations you author, and render the result for review. The thinking
is yours; the scripts are I/O.

Unlike translating (a blind 1:1 text swap), editing means changing structure and
layout, so the loop has one extra beat up front: **you look at the deck before
you change it.**

## The loop

```
inspect + render (SEE the deck) → plan edits (you) → write ops
   → apply → render → review (you) → fix → re-render
```

1. **Inspect + render** — dump the deck's structure to JSON *and* render it to
   PNGs. Read both: the render shows what it looks like, the JSON tells you how
   to address each shape.
2. **Plan** the edits against what you saw.
3. **Write a small ops file** — a JSON list of operations (vocabulary below).
4. **Apply** it; this also turns on shrink-to-fit autofit on any slide text box
   you touch.
5. **Render** the result to one PNG per slide.
6. **Review** the PNGs with your own eyes; find overflow/overlap/clipping/ugly
   wraps on every slide you changed.
7. **Fix** the flagged slides (shorten text first, then force-scale), re-render.
   Repeat 4–7 until clean, then report.

The scripts live in **this skill's own `scripts/` directory**. Don't copy them
into the workspace — point at them where they are. Set a shell var once (adjust
the path if this skill is installed elsewhere):

```bash
S=.agents/skills/edit-pptx/scripts
```

They need `python-pptx` and `Pillow` (pip), plus `LibreOffice` (`soffice`) and
`poppler` (`pdftoppm`) for rendering.

## 1. Inspect + render — look before you touch

```bash
python3 "$S/inventory.py" "deck.pptx" -o inv.json
python3 "$S/render.py"    "deck.pptx" -o before/
```

Read `inv.json` **and** the `before/slide-*.png` images together. `inv.json`
lists, per slide: the `layout` name, and every shape with its `shape_id`, `name`,
`type`, geometry in inches (`left_in`/`top_in`/`width_in`/`height_in`), text
(`paras`, each with its index `p`), table grid, and chart flag. It also lists the
deck's available `layouts` (with indices) — that's what `add_slide` targets.

**You address everything by `slide` (1-based) + `shape_id`.** A `shape_id` is
stable when other shapes are added or removed, so it survives editing — unlike a
position in the list. Read `inventory.py`'s output for the exact ids before
writing any op.

## 2. Plan, then 3. Write the ops file

Author a **small** `ops.json` — a top-level `"ops"` list, one object per
operation, applied in order. Keep it small and targeted; never hand-author a
giant dump of the deck (that's how JSON ends up corrupt). Let `inv.json` supply
the addresses.

### Text content

```jsonc
// replace a whole text frame (one paragraph)
{"op":"set_text","slide":2,"shape_id":5,"text":"New title"}
// replace a frame with several bullets (list = paragraphs)
{"op":"set_text","slide":2,"shape_id":6,"text":["First point","Second point"]}
// replace just one paragraph, leave the rest
{"op":"set_text","slide":2,"shape_id":6,"p":0,"text":"Only the first bullet"}
// edit one table cell
{"op":"set_text","slide":2,"shape_id":9,"row":1,"col":0,"text":"cell value"}
// append a bullet (inherits the last bullet's format; optional indent level)
{"op":"add_bullet","slide":2,"shape_id":6,"text":"Another point","level":1}
// remove a paragraph by index
{"op":"delete_paragraph","slide":2,"shape_id":6,"p":3}
```

A `\n` inside a `text` value becomes a real in-box line break. `set_text` on a
slide text box also accepts `"font_scale"` (1–100, %) and `"line_reduction"`
(0–20, %) to force a tighter fit — see step 7.

### Extend — slides

```jsonc
// BEST way to add a designed slide: clone an existing one and refill its text.
// "from"/"at" are 1-based; "set" keys are SOURCE shape_ids ("<id>" = whole
// frame, "<id>.<p>" = one paragraph).
{"op":"duplicate_slide","from":3,"at":4,"set":{"5":"New Title","6":["A","B"]}}
{"op":"add_slide","layout":1,"at":5}    // fresh slide from a layout index
{"op":"delete_slide","slide":7}
{"op":"move_slide","slide":8,"to":2}
```

**Prefer `duplicate_slide`** for new content slides — it keeps the source's
design, placeholders, and bullet styling, and the inline `set` fills it in one
shot. `add_slide` from a layout gives you empty placeholders you then fill.

### Extend — media (positions in inches)

```jsonc
{"op":"add_textbox","slide":4,"text":"Caption","left":1,"top":6,"width":8,"height":0.8}
{"op":"add_picture","slide":4,"path":"logo.png","left":0.5,"top":0.3,"width":1.5}
{"op":"add_table","slide":4,"rows":[["A","B"],["1","2"]],"left":1,"top":2,"width":6,"height":3}
```

### The index-shifting rule (important)

Ops run **in order against the live deck**. `duplicate_slide`, `add_slide`,
`delete_slide`, and `move_slide` change slide numbers for everything after them.
So **don't** add a slide and then, in the same ops file, edit it by a slide
number you guessed — the number has moved. Instead:

- use `duplicate_slide`'s inline `set` to fill a cloned slide in one shot, **or**
- do structural ops in one ops file, then **re-inspect** (`inventory.py`) to get
  the new numbers and `shape_id`s, then edit in a second ops file.

When in doubt, keep structural ops and content edits in separate passes.

## 4. Apply

```bash
python3 "$S/apply_ops.py" "deck.pptx" ops.json -o "deck.edited.pptx"
```

This runs every op, preserves the existing font/color/bold/bullets on text it
rewrites, restores `\n` as real `<a:br/>`, and sets each **slide text box** it
touches to PowerPoint's native shrink-to-fit (`<a:normAutofit/>`). Watch the
stderr summary: it reports each op that warned (bad `shape_id`, out-of-range
paragraph, unknown op) or failed, and keeps going — one bad op won't sink the
rest. Fix the flagged ops and re-run.

## 5. Render

```bash
python3 "$S/render.py" "deck.edited.pptx" -o render/
```

Produces `render/slide-01.png`, … Use `-f`/`-l` to render only a range while
iterating. LibreOffice rendering is a **proxy** for PowerPoint: close enough to
catch real layout problems, not pixel-identical.

**Important:** LibreOffice and PDF export do **not** apply `normAutofit` shrink —
they render text at full size. A box PowerPoint would auto-shrink shows up here
as *overflowing*. Don't wave it away as "autofit will handle it on open" — fix it
with `font_scale` (step 7), which shrinks the real font and so renders correctly
everywhere.

## 6. Review — look at every slide you changed, out loud

`Read` each changed PNG and write a one-line verdict per slide before moving on —
e.g. `slide 3: OK` or `slide 5: new title clips at right edge → font_scale`. Do
not emit a single global "looks good." Check each for:

- **Overflow / overlap** — text or an added image/table spilling out of its box,
  onto a neighbor, or off the slide edge.
- **Clipping** — text cut off at a box edge.
- **Cramped / shrunk-too-small** — autofit/force-scale made text tiny vs. the
  rest of the deck.
- **Ugly wraps** — an awkward mid-word break or a title spilling to a new line.
- **Placement** — an added textbox/picture/table where you meant it, not over
  existing content (check against its `left/top/width/height` and the render).

If unsure whether a problem is yours, render the same slide from the *original*
deck and compare. Only fix what your edit made worse; report pre-existing issues,
don't silently move things.

## 7. Fix (in this priority order)

1. **Shorten the text (preferred).** Re-word the offending `text` in `ops.json`
   to be tighter — keeps the original typography. Most fits are solved here.
2. **Force-scale the box.** If wording can't get shorter, add to that `set_text`
   (or `add_textbox`) op:
   - `"font_scale": 85` — shrink that box's text to 85% (1–100, %), and/or
   - `"line_reduction": 10` — tighten line spacing by 10% (0–20).
   Pick it by eye — drop a step, re-render, repeat; don't compute it.
3. **Move or resize** an added object: change its `left/top/width/height` and
   re-apply. (To move/resize a *pre-existing* shape there's no first-class op —
   use the python-pptx escape hatch in reference.md.)
4. Only if layout truly can't accommodate it, tell the user which slide(s) need a
   manual design change. Don't ship unreadable slides.

Re-run `apply_ops.py` from the **original** deck with the corrected `ops.json`
(the ops file is the source of truth — re-applying it is idempotent), then
re-render the changed slides with `-f`/`-l`.

## 8. Report

Give the user: the output path, a summary of what changed (slides added/edited,
shapes added), any boxes that needed `font_scale`, anything you did via the
escape hatch, any **pre-existing** layout issues you left alone, and a list of
**untouched content** (see Scope) so they're not surprised.

## Scope

- **Covered by ops:** editing text in any shape (placeholders, text boxes, table
  cells, grouped shapes); adding/removing/reordering slides; cloning a slide;
  adding text boxes, pictures, and tables.
- **Via the escape hatch (reference.md):** restyling (font/size/color/bold),
  moving/resizing/deleting existing shapes, z-order, and anything else
  python-pptx can do. Same render/review loop applies.
- **Not handled:** editing text baked into images (needs OCR), SmartArt diagram
  text, and chart data labels (they live in cached chart data). `duplicate_slide`
  handles text + pictures + hyperlinks well; very complex objects (charts with
  embedded workbooks, embedded media, SmartArt) may not clone cleanly — verify in
  the render and flag to the user. **List anything you couldn't touch in the
  report.**

See [reference.md](./reference.md) for the ops JSON schema in full, the autofit
XML mechanics, the python-pptx escape hatch with worked examples, and known
limitations.


## Supporting files in this skill directory:
- reference.md
- scripts/inventory.py
- scripts/apply_ops.py
- scripts/_common.py
- scripts/render.py

Use the read_file tool with paths relative to: .agents/skills/edit-pptx/
