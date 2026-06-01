# translate-pptx — reference

Background details for the skill. You don't need this for the normal loop; read
it when something breaks or you need to reach into the XML.

## Why translated decks overflow

A `.pptx` is a zip of XML. Each text box is a `<p:txBody>` whose
`<a:bodyPr>` declares an **autofit mode**:

| Element | Meaning | python-pptx |
| --- | --- | --- |
| `<a:noAutofit/>` | do nothing — text overflows the box | `MSO_AUTO_SIZE.NONE` |
| `<a:spAutoFit/>` | grow the **box** to fit the text | `SHAPE_TO_FIT_TEXT` |
| `<a:normAutofit/>` | shrink the **text** to fit the box | `TEXT_TO_FIT_SHAPE` |

Most decks ship with `noAutofit` or `spAutoFit`. Naive translation tools swap
the `<a:t>` text and the font size and box stay fixed, so longer German text
spills out. **This skill sets every slide text box to `normAutofit`**, which is
PowerPoint's own "shrink text on overflow." PowerPoint then computes the fit
when the file opens — and our LibreOffice render approximates it for review.

### The baked scale

`normAutofit` can carry two attributes that store the *computed* fit:

```xml
<a:normAutofit fontScale="80000" lnSpcReduction="10000"/>
```

- `fontScale` — render all runs at this % of their nominal size, in
  **thousandths of a percent** (`80000` = 80%).
- `lnSpcReduction` — reduce line spacing by this %, same units (`10000` = 10%).

`apply.py` writes a bare `<a:normAutofit/>` by default (PowerPoint/LibreOffice
recompute it). When you set `"font_scale"` / `"line_reduction"` on a frame in
the job JSON, it bakes them in as the percentages above — so the box renders
small *immediately*, even in viewers that don't recompute autofit. This is the
deterministic lever for the rare box that autofit alone doesn't tame. Pick the
value by looking at renders, not by computing font metrics (that path is
brittle: it needs the exact font installed, and Windows fonts like Calibri and
Cambria aren't on macOS/Linux).

## Job JSON schema

```jsonc
{
  "source": "deck.pptx",
  "target_lang": "de",
  "include_notes": true,        // must match between extract & apply
  "frames": [
    {
      "id": 0,                  // walk position — DO NOT change
      "slide": 1,               // 1-based, informational
      "kind": "slide",          // slide | table | chart_title | notes
      "autofit": true,          // false for table/chart/notes
      "paras": [
        { "i": 0, "src": "Title", "tgt": "Titel" }
      ],
      "font_scale": 85,         // OPTIONAL, 1-100 (%), only honored when autofit
      "line_reduction": 10      // OPTIONAL, 0-20 (%)
    }
  ]
}
```

- `id` is the frame's position in a fixed deterministic walk of the deck.
  `extract.py` and `apply.py` use the **same** walker (`scripts/_common.py`), so
  the position is a stable key. If you reorder/insert/delete frames, mapping
  breaks — only edit `tgt` (and optionally add the two scale fields).
- `i` is the paragraph index within the frame. Only non-empty paragraphs are
  extracted, so `i` may be sparse.
- `font_scale` / `line_reduction` are ignored on frames where `autofit` is
  `false` (tables, charts, notes don't take slide autofit).

## How text is written back

`apply.py` puts the whole translated paragraph into the paragraph's **first
run** and blanks the remaining runs. This preserves the first run's formatting
(font, size, color, bold) for the paragraph.

**Limitation:** intra-paragraph formatting variation is lost — e.g. if one word
in a sentence was bold or a different color, the whole translated paragraph
takes the first run's formatting. This is the standard trade-off for translation
(word order changes, so run boundaries can't be preserved). If a deck depends on
mid-sentence styling, flag it to the user and fix those runs by hand.

## Rendering

`render.py` runs:

```bash
soffice --headless -env:UserInstallation=<temp> --convert-to pdf --outdir <tmp> deck.pptx
pdftoppm -png -r <dpi> <tmp>/deck.pdf render/slide
```

The throwaway `UserInstallation` profile lets it run even while LibreOffice is
open in the GUI. Default DPI is 110 (good enough to read; bump with `-r` if you
need to inspect small text). Use `-f`/`-l` to render a slide range while
iterating.

LibreOffice ≠ PowerPoint: font substitution and autofit math differ slightly.
Treat the render as "is anything obviously broken," not as final proof. Since
the deck carries `normAutofit`, real PowerPoint does its own fit on open.

## Dependencies

- Python: `python-pptx`, `Pillow` (`pip install python-pptx Pillow`).
- System: LibreOffice (`brew install --cask libreoffice`), poppler
  (`brew install poppler`) for `pdftoppm`.

## Known limitations

- Text inside images (needs OCR) and SmartArt diagram text are not translated.
- Chart **titles** are translated; chart category/series **data labels** are not
  (they live in cached chart data / the embedded worksheet).
- Merged table cells may be visited more than once; harmless but redundant.
- Paragraphs with no runs (rare — e.g. text supplied only by a field) are left
  unchanged and reported as a warning.
