# edit-pptx — reference

Background for the skill. You don't need this for the normal loop; read it when
you need the full ops schema, want to reach past the op vocabulary into
python-pptx, or something breaks.

## Addressing: why `slide` + `shape_id`

A `.pptx` is a zip of XML. Every shape carries a `<p:cNvPr id="…">` that
python-pptx exposes as `shape.shape_id`, **unique within its slide**. This skill
keys edits on `(slide number, shape_id)` rather than a position in the shape
list, because adding or deleting shapes renumbers positions but leaves
`shape_id`s alone. `inventory.py` reports both the id and the shape's `name`
(e.g. "Title 1") so you can sanity-check you're editing the right thing.

`shape_id`s are only unique *within a slide*, so a duplicated slide carries the
same ids as its source — which is exactly why `duplicate_slide`'s inline `set`
map is keyed by the source slide's `shape_id`s.

## Ops JSON schema

Top level is either a `{"ops": [ … ]}` object or a bare `[ … ]` list. Each entry
has an `"op"` discriminator. Ops execute **in order against the live deck**.

| op | required | optional | effect |
| --- | --- | --- | --- |
| `set_text` | `slide`, `shape_id`, `text` | `p`, `row`+`col`, `font_scale`, `line_reduction` | Replace a frame's text. `text` is a string (one paragraph) or a list of strings (paragraphs). `p` targets one paragraph; `row`+`col` targets a table cell. |
| `add_bullet` | `slide`, `shape_id`, `text` | `level` | Append a paragraph, cloning the last paragraph's bullet/format. `level` sets indent depth (0-based). |
| `delete_paragraph` | `slide`, `shape_id`, `p` | — | Remove paragraph `p`. |
| `duplicate_slide` | `from` | `at`, `set` | Deep-copy slide `from`; place at 1-based `at` (else end). `set` refills text in the copy, keyed by source `shape_id` (`"<id>"` whole frame, `"<id>.<p>"` one paragraph). |
| `add_slide` | `layout` | `at` | New slide from `layout` (index into the deck's `layouts`). Place at `at` (else end). |
| `delete_slide` | `slide` | — | Remove a slide. |
| `move_slide` | `slide`, `to` | — | Move a slide to 1-based position `to`. |
| `add_textbox` | `slide`, `text`, `left`, `top` | `width` (4), `height` (1), `font_scale`, `line_reduction` | New text box. Positions/sizes in **inches**. |
| `add_picture` | `slide`, `path`, `left`, `top` | `width`, `height` | Insert an image. With only `width` or only `height`, the other scales proportionally; with neither, native size. |
| `add_table` | `slide`, `rows`, `left`, `top` | `width` (6), `height` (rows×0.4) | `rows` is a list of row lists; the table is sized to the widest row. Cells are set as plain text. |

`set_text` / `add_textbox` honour `font_scale` (1–100, %) and `line_reduction`
(0–20, %) only on real slide text boxes (not table cells). Unknown ops and
out-of-range / missing targets are reported as warnings and skipped; an op that
throws is caught, reported, and the rest still run.

### The index-shifting hazard

Because ops run against the live deck, any `add_slide` / `duplicate_slide` /
`delete_slide` / `move_slide` changes the slide numbers of everything after it.
Editing a slide by a number you predicted *after* a structural op in the same
file will hit the wrong slide. Safe patterns:

- Clone-and-fill in one op via `duplicate_slide` + `set`.
- Or: structural ops in pass 1 → re-run `inventory.py` → content edits in pass 2.

The ops file is the source of truth: always re-apply it against the **original**
`deck.pptx`, never against a previous output, so re-runs are reproducible.

## Why text fitting matters here, and the autofit mechanics

Each text box is a `<p:txBody>` whose `<a:bodyPr>` declares an autofit mode:

| Element | Meaning |
| --- | --- |
| `<a:noAutofit/>` | do nothing — text overflows |
| `<a:spAutoFit/>` | grow the box to fit the text |
| `<a:normAutofit/>` | shrink the text to fit the box |

When you rewrite or add text it may no longer fit the box it landed in. So
`apply_ops.py` sets every **slide text box it touches** to `<a:normAutofit/>`
(PowerPoint's "shrink text on overflow"), which PowerPoint recomputes on open.

`normAutofit` can bake a computed scale:

```xml
<a:normAutofit fontScale="80000" lnSpcReduction="10000"/>
```

(thousandths of a percent: `80000` = 80%). But **LibreOffice and PDF export
ignore `fontScale` entirely** — they render every box at nominal size. So a box
PowerPoint would shrink shows up in our render as overflowing, and a baked
`fontScale` would be invisible in review.

That's why the `font_scale` lever **scales the real run sizes** (`sz`) instead of
baking `fontScale`: scaled sizes render identically in LibreOffice, PDF, and
PowerPoint, so review shows what the user gets. `line_reduction` still writes
`lnSpcReduction` on the `normAutofit`. Pick both by eye from renders — not by
computing font metrics (brittle: needs the exact font installed, and Windows
fonts like Calibri aren't on macOS/Linux).

**Caveat:** a run with no explicit `sz` inherits its size from the
placeholder/theme; `font_scale` has nothing to scale there, and only real
PowerPoint (via `normAutofit`) will shrink it. Those boxes need a manual size in
PowerPoint, or a note to the user.

## How text is written back

`apply_ops.py` (via `_common.write_paragraph_text`) puts the whole new paragraph
into the paragraph's **first run** and blanks the remaining runs, preserving the
first run's font/size/color/bold. A `\n` (or the vertical tab python-pptx uses
for an existing `<a:br/>`) is split out and rebuilt as real `<a:br/>` + run pairs
cloned from the first run — assigning it straight to `run.text` would escape it
to the literal string `_x000B_` (visible garbage).

`add_bullet` deep-copies the last existing paragraph (keeping its bullet, indent,
level, run properties), strips it to a single run, and re-texts it — so appended
bullets match the list they join.

**Limitation:** intra-paragraph formatting variation is lost — if one word was
bold or a different color, the rewritten paragraph takes the first run's
formatting. If a slide depends on mid-sentence styling, fix those runs by hand
(see the escape hatch).

## How slide duplication works

python-pptx has no public "duplicate slide," so `_duplicate_slide`:

1. Adds a new slide from the source's layout, then removes the placeholders the
   layout injected.
2. Re-relates the source slide's relationships (images, hyperlinks, media) onto
   the new slide, getting fresh relationship ids.
3. Deep-copies each shape's XML and **remaps** the relationship-id references
   (`r:embed`, `r:id`, `r:link`) to the new ids, then appends them.

This is solid for typical decks (text, pictures, hyperlinks). Objects with their
own embedded parts — charts with cached workbooks, embedded video/audio, SmartArt
— may not round-trip cleanly. Verify the cloned slide in the render and tell the
user if something looks off.

## The python-pptx escape hatch

The op vocabulary covers content edits and adding slides/media. For everything
else — restyling, moving/resizing/deleting an existing shape, z-order, grouping,
chart data — write a short script against the same addressing, then go through
the **same render → review loop**. Reuse this skill's helpers so text edits stay
fit-aware:

```python
import sys
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
sys.path.insert(0, ".agents/skills/edit-pptx/scripts")
from _common import find_shape, set_autofit, set_frame_text

prs = Presentation("deck.pptx")
slide = prs.slides[1]                 # 0-based here (python-pptx), vs 1-based in ops
shape = find_shape(slide, 5)          # by the shape_id inventory.py reported

# --- restyle a run (color / size / bold) ---
run = shape.text_frame.paragraphs[0].runs[0]
run.font.size = Pt(28)
run.font.bold = True
run.font.color.rgb = RGBColor(0x1F, 0x49, 0x7D)

# --- move / resize an existing shape (EMU; use Inches() to be readable) ---
shape.left   = Inches(1.0)
shape.top    = Inches(0.5)
shape.width  = Inches(8.0)
shape.height = Inches(1.2)

# --- delete a shape ---
victim = find_shape(slide, 9)
victim._element.getparent().remove(victim._element)

prs.save("deck.edited.pptx")
```

Geometry is in EMU (914,400 per inch); always wrap with `Inches()`/`Pt()`. After
any escape-hatch run, render and review exactly as with the ops loop, and note in
your report that you stepped outside the op vocabulary.

## Rendering

`render.py` runs:

```bash
soffice --headless -env:UserInstallation=<temp> --convert-to pdf --outdir <tmp> deck.pptx
pdftoppm -png -r <dpi> <tmp>/deck.pdf render/slide
```

The throwaway profile lets it run even while LibreOffice is open in the GUI.
Default DPI 110; bump with `-r` to inspect small text. Use `-f`/`-l` for a slide
range. LibreOffice ≠ PowerPoint (font substitution and autofit math differ) — the
render catches "is anything obviously broken," not final proof.

## Dependencies

- Python: `python-pptx`, `Pillow` (`pip install python-pptx Pillow`).
- System: LibreOffice (`brew install --cask libreoffice`), poppler
  (`brew install poppler`) for `pdftoppm`.

## Known limitations

- Text inside images (needs OCR), SmartArt diagram text, and chart data labels
  are not editable here.
- Intra-paragraph formatting variation collapses to the first run's style on a
  text rewrite (see above).
- Complex objects may not survive `duplicate_slide` (see above).
- The script is named `inventory.py`, not `inspect.py`, on purpose: a script
  named `inspect.py` shadows Python's stdlib `inspect` module (a script's own
  directory is first on `sys.path`), which breaks lxml's import inside pptx.
