---
name: translate-pptx
description: >-
  Translate a PowerPoint (.pptx) deck into another language — primarily
  English→German, but any language pair — while keeping the layout intact and
  making the translated text actually FIT its boxes. Use whenever the user asks
  to translate, localize, or convert the language of a .pptx / PowerPoint /
  slides file. Handles the classic problem where German (and other) text grows
  longer than the source and overflows its text boxes.
---

# Translate PowerPoint decks (fit-aware)

Translate the text of a `.pptx` while preserving its design, then **verify and
fix the fit visually** — because translated text (especially German, ~25–35%
longer than English) overflows boxes that were sized for the original.

The translation itself is done by **you, the model** — not an external API.
That is the whole point: you can choose concise wording and shorten text that
won't fit. Scripts only move text in/out of the file and render it for review.

## The loop

```
extract → translate (you) → apply → render → review (you) → fix → re-render
```

1. **Extract** the text into a JSON job file.
2. **Translate** every paragraph in the JSON (concise, context-aware).
3. **Apply** it back; this also turns on shrink-to-fit autofit.
4. **Render** the result to one PNG per slide.
5. **Review** the PNGs with your own eyes; find overflow/overlap/clipping.
6. **Fix** the flagged slides (shorten text first, then force-scale), re-render.
7. Repeat 4–6 until clean, then report.

All scripts live in `scripts/`. Run them with `python3`. They need
`python-pptx` and `Pillow` (pip), plus `LibreOffice` (`soffice`) and `poppler`
(`pdftoppm`) for rendering.

## 1. Extract

```bash
python3 scripts/extract.py "deck.pptx" --target de -o job.json
```

`--target` is just a label carried into the output filename. Add `--no-notes`
to skip speaker notes. The JSON is a list of `frames`; each has `paras` with
`src` (source text) and an empty `tgt` you will fill. `id`, `i`, `slide`,
`kind` are bookkeeping — **never change them**.

## 2. Translate (this is your job)

Edit `job.json` and fill every `tgt`. Rules:

- **Translate per slide, in context.** Read all `paras` on a `slide` together so
  terminology and tone stay consistent across titles, bullets, and notes.
- **Be concise — brevity is a feature, not a compromise.** Slides are not prose.
  Prefer the shorter natural phrasing, use compound nouns, drop filler
  ("in order to" → "um", "is able to" → "kann"). For **titles and short
  labels**, weight brevity heavily; a snug box can't absorb a 40%-longer title.
- **Keep meaning and register.** Match the formality of the source (German: pick
  Sie/du consistently — default to **Sie** for business decks unless the source
  is casual).
- **Leave non-text as-is**: numbers, URLs, emails, code, product/brand names,
  acronyms. Copy them into `tgt` unchanged.
- **Don't add or remove paragraphs.** One `tgt` per `src`. If a paragraph should
  stay in the source language, copy `src` into `tgt` verbatim.
- Preserve leading/trailing punctuation and bullet-friendly phrasing.

For big decks, work through the JSON in chunks but keep the structure exact.

## 3. Apply

```bash
python3 scripts/apply.py "deck.pptx" job.json -o "deck.de.pptx"
```

This writes each `tgt` into its paragraph (keeping the original font, color,
bold, bullets) and sets every slide text box to PowerPoint's native
**shrink-to-fit** autofit (`<a:normAutofit/>`). That means real PowerPoint
re-fits the text the moment the user opens the file — and our renderer
approximates the same. Watch the stderr summary for warnings (empty `tgt`,
missing runs, etc.).

## 4. Render

```bash
python3 scripts/render.py "deck.de.pptx" -o render/
```

Produces `render/slide-1.png`, `slide-2.png`, … Use `-f`/`-l` to render only a
range of slides while iterating (faster). LibreOffice rendering is a **proxy**
for PowerPoint: close enough to catch real layout problems, not pixel-identical.

## 5. Review — look at every slide

`Read` each PNG and check for:

- **Overflow / overlap** — text spilling out of its box or onto a neighbor,
  image, or off the slide edge.
- **Clipping** — text cut off at a box edge.
- **Cramped / shrunk-too-small** — autofit made a box's text noticeably tiny
  versus the rest of the deck.
- **Ugly wraps** — a long compound noun forcing an awkward break, a title
  spilling to a second line it shouldn't.

If a slide looks clean, leave it. Only fix what's actually broken.

## 6. Fix (in this priority order)

1. **Shorten the translation (preferred).** Re-word the offending `tgt` in
   `job.json` to be tighter — this keeps the original typography. Most fits are
   solved here.
2. **Force-scale the box.** If wording can't get shorter, add to that frame
   object in `job.json`:
   - `"font_scale": 85` — render the box at 85% (1–100, percent), and/or
   - `"line_reduction": 10` — tighten line spacing by 10% (0–20).
   Choose the number **by looking at the render and iterating** — drop it a step,
   re-render, repeat. Do not compute it.
3. Only if layout truly can't accommodate the text, tell the user which
   slide(s) need a manual design change (e.g. a bigger box). Don't silently ship
   unreadable slides.

Re-run `apply.py`, then `render.py` (just the changed slides with `-f`/`-l`).

## 7. Report

When done, give the user: the output path, slide/paragraph counts, and a short
list of any slides that needed force-scaling or still have a caveat.

## Scope

- **Covered:** slide body text, titles, grouped shapes, table cells, chart
  titles, speaker notes.
- **Not covered:** text baked into images (needs OCR), SmartArt diagram text
  (fragile; PowerPoint often regenerates it), chart category/series data labels.
  Flag these to the user if the deck relies on them.

See [reference.md](./reference.md) for the autofit XML mechanics, the JSON
schema, and known limitations.
