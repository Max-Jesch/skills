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

The scripts live in **this skill's own `scripts/` directory** (its path is at
the bottom of this file). Don't copy them into the workspace — point at them
where they are. Set a shell var once and reuse it (adjust the path if this
skill is installed elsewhere):

```bash
S=.agents/skills/translate-pptx/scripts
```

They need `python-pptx` and `Pillow` (pip), plus `LibreOffice` (`soffice`) and
`poppler` (`pdftoppm`) for rendering.

## 1. Extract

```bash
python3 "$S/extract.py" "deck.pptx" --target de -o job.json
```

`--target` is just a label carried into the output filename. Add `--no-notes`
to skip speaker notes. The JSON is a list of `frames`; each has `paras` with
`src` (source text) and an empty `tgt` you will fill. `id`, `i`, `slide`,
`kind` are bookkeeping — **never change them**.

A vertical-tab char (``) in `src` is an in-box line break — keep it in `tgt`
at the matching spot; `apply.py` restores it as a real break.

## 2. Translate (this is your job)

Read the source from `job.json`, then produce your translations as a **flat
map** keyed by `"<id>.<i>"` — **do not re-author `job.json` by hand** (that is
how it ends up with a stray control char or bad escape and fails to parse).
Translation rules:

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

Write the map to `tr.json`, using `\n` for an in-box line break:

```json
{ "0.0": "IBM Dev Day:\nBob-Edition\nEnablement vor dem Hackathon",
  "1.0": "Maximilian Jesch" }
```

Then merge it into the (already-valid) job file:

```bash
python3 "$S/fill.py" job.json tr.json
```

`fill.py` only touches `tgt`, so the JSON stays valid. It reports any
paragraph you left untranslated — fill those and re-run before applying.

## 3. Apply

```bash
python3 "$S/apply.py" "deck.pptx" job.json -o "deck.de.pptx"
```

This writes each `tgt` into its paragraph (keeping the original font, color,
bold, bullets), restores any `` line breaks as real `<a:br/>`, and sets
every slide text box to PowerPoint's native **shrink-to-fit** autofit
(`<a:normAutofit/>`). Watch the stderr summary for warnings (empty `tgt`,
missing runs, etc.).

## 4. Render

```bash
python3 "$S/render.py" "deck.de.pptx" -o render/
```

Produces `render/slide-01.png`, `slide-02.png`, … Use `-f`/`-l` to render only a
range of slides while iterating (faster). LibreOffice rendering is a **proxy**
for PowerPoint: close enough to catch real layout problems, not pixel-identical.

**Important:** LibreOffice (and PDF export) does **not** apply `normAutofit`
shrink — it renders text at full size. So a box that PowerPoint would auto-shrink
shows up here as *overflowing*. Don't dismiss overflow as "autofit will handle
it on open" — fix it with `font_scale` (step 6), which shrinks the real font and
therefore renders correctly everywhere.

## 5. Review — look at every slide, out loud

`Read` each PNG and write a one-line verdict **per slide** before moving on —
e.g. `slide 3: OK` or `slide 5: title "Schritt für Schritt" breaks mid-word →
force-scale`. Do not emit a single global "looks good"; that is how real
breakage gets shipped. Check each slide for:

- **Overflow / overlap** — text spilling out of its box or onto a neighbor,
  image, or off the slide edge.
- **Clipping** — text cut off at a box edge (a title missing its last letters).
- **Cramped / shrunk-too-small** — autofit/force-scale made text noticeably tiny
  versus the rest of the deck.
- **Ugly wraps** — a long compound noun forcing an awkward break, a title
  spilling to a line it shouldn't, a word broken mid-word.

If unsure whether a problem is yours, render the same slide from the *source*
deck and compare. If it's there too, it's pre-existing — report it, don't move
shapes to "fix" it. Only fix what translation made worse.

## 6. Fix (in this priority order)

1. **Shorten the translation (preferred).** Re-word the offending `tgt` in
   `job.json` to be tighter — this keeps the original typography. Most fits are
   solved here.
2. **Force-scale the box.** If wording can't get shorter, add to that frame
   object in `job.json`:
   - `"font_scale": 85` — shrink that box's text to 85% (1–100, percent), and/or
   - `"line_reduction": 10` — tighten line spacing by 10% (0–20).
   `font_scale` rescales the **real run font sizes** (renders everywhere, unlike
   `normAutofit`). Pick it by eye — drop a step, re-render, repeat; don't compute
   it. See reference.md for the inherited-size caveat.
3. Only if layout truly can't accommodate the text, tell the user which
   slide(s) need a manual design change (e.g. a bigger box). Don't silently ship
   unreadable slides.

Re-run `apply.py`, then `render.py` (just the changed slides with `-f`/`-l`).

## 7. Report

When done, give the user: the output path, slide/paragraph counts, a list of any
slides that needed force-scaling, any slides with **pre-existing** layout issues
you left alone (and why), and a list of any **untranslated content** (see Scope)
so they're not surprised.

## Scope

- **Covered:** slide body text, titles, grouped shapes, table cells, chart
  titles, speaker notes.
- **Not covered:** text inside images/screenshots, SmartArt diagram text, chart
  data labels. **List these in the report** — otherwise screenshot-heavy decks
  look half-translated.

See [reference.md](./reference.md) for the autofit XML mechanics, the JSON
schema, and known limitations.


## Supporting files in this skill directory:
- reference.md
- scripts/apply.py
- scripts/extract.py
- scripts/fill.py
- scripts/_common.py
- scripts/render.py

Use the read_file tool with paths relative to: .agents/skills/translate-pptx/
