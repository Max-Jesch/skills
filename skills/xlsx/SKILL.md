---
name: xlsx
description: >-
  Create, edit, read, and analyze Excel spreadsheets (.xlsx / .xlsm / .csv). Use
  whenever the user wants to build or modify a workbook, financial model,
  budget, report, or data table — or to pull numbers out of, summarize, or
  answer questions about an existing spreadsheet. Builds LIVE workbooks with real
  Excel formulas (not hardcoded results), then recalculates and verifies there
  are zero formula errors before handing back.
---

# Work with Excel spreadsheets (.xlsx)

Build and edit real, *live* Excel files: cells carry **formulas**, not numbers
you computed in Python and pasted in. A spreadsheet whose totals are `=SUM(...)`
stays correct when an input changes and is auditable by the user — one full of
hardcoded values is a dead report wearing a spreadsheet's clothes. That single
rule drives most of this skill.

You do the thinking — what the model should compute, how it's laid out, what the
data means. The scripts do the mechanical parts: recalculating formulas (Python
can't), mapping a workbook's structure, and rendering it for a visual check.

## Tools

- **openpyxl** — the editing engine. Formulas, formatting, styles, multiple
  sheets, named ranges, column widths. Use it whenever you write formulas or
  care about appearance.
- **pandas** — the analysis engine. Reading data in bulk, filtering, grouping,
  describing. Use it to *understand* data; use openpyxl to *author* the file.
- The scripts in this skill's `scripts/` directory (path at the bottom). Point at
  them where they live; don't copy them into the workspace. Set a var once:

  ```bash
  S=.agents/skills/xlsx/scripts
  ```

  They need `openpyxl` + `pandas` (pip), and for recalc/render **LibreOffice**
  (`soffice`) and `poppler` (`pdftoppm`).

## The loop

```
outline (understand) → build/edit (you, openpyxl/pandas)
   → recalc (script) → verify zero errors → fix → repeat
```

### 1. Outline — understand before you touch

For any *existing* workbook, map it first so your formulas reference the right
cells (don't guess the layout, and don't slurp the whole file into context):

```bash
python3 "$S/outline.py" book.xlsx           # sheets, dims, headers, sample rows
python3 "$S/outline.py" book.xlsx --values  # show cached results, not formulas
```

For heavier analysis, load it with pandas (`pd.read_excel`, or `pd.read_csv`).
Confirm column names, where the header row really is, and which columns have
nulls **before** writing formulas against them.

### 2. Build / edit — with formulas, always

Write a short Python script using openpyxl (and pandas for bulk data). The
non-negotiables:

- **Formulas, not hardcoded results.** Totals, ratios, growth — emit
  `ws["B10"] = "=SUM(B2:B9)"`, never `ws["B10"] = 47`. The only numbers you type
  are genuine **inputs** (assumptions, source data). If a value comes from
  outside the sheet, hardcode it but note the source in an adjacent cell.
- **Reference cells, don't repeat literals.** A tax rate lives in one input cell
  that every formula points at — not `*0.21` sprinkled across the sheet.
- **Preserve existing structure.** When editing a file the user gave you, keep
  its sheet names, styles, and layout unless asked to change them. Load it,
  modify, save — don't rebuild from scratch.
- **Validate references first.** On a real workbook, test 2–3 formulas against
  known cells before building the whole model on an assumed layout.

See [reference.md](./reference.md) for number-format and financial-model
conventions (color coding, currency units, negatives in parentheses, years as
text) — apply them when building models or reports.

### 3. Recalc — Python wrote no results

openpyxl saves your formula strings but **never their computed values**. Until a
real spreadsheet engine evaluates them, the file has no totals and you can't tell
a sound model from a broken one. Recalculate every time you write formulas:

```bash
python3 "$S/recalc.py" output.xlsx          # LibreOffice (default, headless)
```

This edits the file in place: it evaluates all formulas, writes the results as
cached values, and **scans for formula errors**, printing each one as
`Sheet!Cell: #DIV/0!`. Exit code is non-zero if any error is found.

`--engine excel` uses the installed Microsoft Excel instead (true Excel
evaluation — reach for it only when the model uses Excel-only functions
LibreOffice doesn't match). It's fragile: Excel must already be open and past any
sign-in/first-run dialog. Default to LibreOffice.

### 4. Verify — zero formula errors, sane numbers

`recalc.py` flags `#REF!`, `#DIV/0!`, `#VALUE!`, `#N/A`, `#NAME?`, `#NUM!`,
`#NULL!`, `#SPILL!`. **Don't hand back a file with any of these.** For each one,
fix the cause — a `#REF!` is a deleted/shifted reference, `#DIV/0!` a missing or
zero denominator (guard it: `=IFERROR(a/b, 0)` or check the input), `#NAME?` a
typo'd function or named range.

Then re-read the numbers with `outline.py --values` (or pandas) and sanity-check
them: do the totals foot, are the magnitudes plausible, did a sum land where you
expect? A formula with no error can still be wrong.

### 5. Look at it (when layout matters)

For formatted reports, dashboards, and models — anything where appearance
counts — render it and actually look, the way you'd proofread a printed page:

```bash
python3 "$S/screenshot.py" output.xlsx -o render/
```

One PNG per printed page. `Read` them and check: columns wide enough (no `####`),
number formats applied, headers aligned, nothing spilling or cut off. Set print
areas / fit-to-width in the workbook if pagination is unhelpful. This is a
LibreOffice proxy — close, not pixel-identical to Excel. Skip this step for pure
data-crunching where there's no formatting to inspect.

### 6. Report

Tell the user: the output path, what you built (sheets, key formulas/assumptions),
the result of the error scan (ideally "0 formula errors"), any values you had to
hardcode and their source, and anything you couldn't do (e.g. a feature openpyxl
can't write — see Scope).

## Scope

- **Covered:** cell values and formulas, number formats, fonts/fills/borders,
  column widths, multiple sheets, named ranges, freeze panes, basic data
  validation, reading/analysis of existing data, CSV ↔ xlsx.
- **Limited / not covered:** pivot tables, charts (openpyxl can create simple
  charts but not edit existing ones), conditional formatting beyond basics,
  macros/VBA (`.xlsm` code is preserved on round-trip but not authored here),
  live links to other workbooks. **List anything in this bucket in your report**
  so the user isn't surprised.

See [reference.md](./reference.md) for the formulas-vs-cached-values mechanics,
recalc engine details, formatting conventions, and known limitations.


## Supporting files in this skill directory:
- reference.md
- scripts/outline.py
- scripts/recalc.py
- scripts/screenshot.py

Use the read_file tool with paths relative to: .agents/skills/xlsx/
