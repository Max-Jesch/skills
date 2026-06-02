# xlsx — reference

Background for the skill. You don't need this for the normal loop; read it when
recalc behaves oddly, you hit a formula that won't evaluate, or you're building a
model and want the formatting conventions.

## Why recalc is a separate step (formulas vs. cached values)

An `.xlsx` is a zip of XML. A formula cell stores **two** things: the formula
(`<f>=SUM(B2:B9)</f>`) and the last computed result cached alongside it
(`<v>47</v>`). Excel and LibreOffice keep both in sync. **openpyxl writes only
the formula** — it has no calculation engine, so it never writes `<v>`.

Consequences:

- A file you just wrote with openpyxl has formulas but **no results**. Open it in
  Excel and it computes fine; but read it programmatically with
  `load_workbook(data_only=True)` and every formula cell is `None`.
- You therefore can't verify a model — or let any downstream reader (pandas,
  another script, a chart) see real numbers — until a real engine has evaluated
  it. That's what `recalc.py` is for: it loads the file in a spreadsheet engine,
  forces a full recalculation, and saves, which writes the `<v>` cache back.
- The error scan reads `data_only=True` after recalc, so it sees the cached
  results and can catch `#DIV/0!`, `#REF!`, etc.

`outline.py --values` likewise reads `data_only=True`; run it only **after**
recalc or every computed cell shows blank.

## Recalc engines

### LibreOffice (default)

`recalc.py` writes a throwaway user profile with the registry key

```
/org.openoffice.Office.Calc/Formula/Load → OOXMLRecalcMode = 0   (always recalc)
```

then runs `soffice --headless --convert-to xlsx` against the file. With
recalc-on-load forced, the round-trip evaluates every formula and writes the
results back as cached values. The private `UserInstallation` profile (same
trick as translate-pptx) lets it run even while LibreOffice is open in the GUI.

**The catch — newer Excel functions.** LibreOffice's function set lags Excel.
Dynamic-array and spill features in particular are unsupported:

- spill references `D14#` (`_xlfn.ANCHORARRAY`), `SEQUENCE`, `SORT`, `FILTER`,
  `UNIQUE`, `XLOOKUP`/`XMATCH` (older builds), `LAMBDA`, etc.

LibreOffice evaluates these to `#NAME?` and **writes that wrong value into the
cache**. The formula text survives the round-trip (you may see a harmless case
change like `_xlfn.ANCHORARRAY` → `_xlfn.anchorarray`), so reopening in Excel and
recalculating heals it — but the file you just produced has bogus cached values.

So: if `recalc.py` reports a wall of `#NAME?` on a file you didn't write, suspect
unsupported functions, not real errors. Re-run with `--engine excel`, or tell the
user the file needs Excel to recalculate.

### Excel (`--engine excel`, macOS)

Drives the installed Microsoft Excel over AppleScript: open the workbook,
`calculate`, close saving the file. This is **true Excel evaluation** — the only
faithful option for workbooks using Excel-only functions. Trade-offs:

- First run triggers a macOS automation-permission prompt (allow Terminal/your
  agent to control Excel).
- Excel must be launched and past any sign-in / first-run / "what's new" dialog,
  or the AppleEvent blocks and times out.
- It's GUI automation, so it's inherently less robust than the headless path.
  Use it deliberately for fidelity, not as the everyday default.

## Use formulas, not hardcoded values

The core rule, and why: a cell that reads `=SUM(B2:B9)` recomputes when an input
changes and shows its logic when the user clicks it. A cell that reads `47`
because you summed it in Python is a dead number — wrong the moment anything
upstream changes, and unauditable. Always emit the formula.

The only values you type as literals are genuine **inputs**: assumptions, source
data, scenario knobs. If an input came from outside the sheet, hardcode it but
record the provenance in an adjacent cell — e.g. `Source: Company 10-K FY2024
p.45`. And put each input in **one** cell that formulas reference, rather than
repeating the literal (`*0.21`) across the sheet.

## Financial-model / report conventions

Apply these when building models or formatted reports (skip for throwaway data
dumps). They're the conventions analysts expect, so a model that follows them
reads as professional and is easy to audit.

**Color coding (font color by cell role):**

| Color | Meaning |
| --- | --- |
| Blue | hard-coded **inputs** / assumptions the user may change |
| Black | formulas and calculations |
| Green | references to another sheet in the same workbook |
| Red | references to an external file |

A yellow cell fill is the common flag for "key assumption — update me."

**Number formats:**

- Currency: put the unit in the header (`Revenue ($mm)`), not on every cell.
- Negatives in parentheses: `(123)`, not `-123` (number format
  `#,##0;(#,##0)`).
- Show zeros as `-` where it aids readability (`#,##0;(#,##0);"-"`).
- Percentages to one decimal: `0.0%`.
- Years are labels, not quantities — format as text so they read `2024`, not
  `2,024`.

**Structure:** inputs grouped and clearly labeled; one calculation per row where
practical; freeze the header row/label column on big tables; descriptive sheet
names.

## openpyxl notes & gotchas

- **Writing a formula:** assign the string with the leading `=` —
  `ws["B10"] = "=SUM(B2:B9)"`. openpyxl stores it as a formula, not text.
- **Reading:** default `load_workbook(path)` returns **formulas**;
  `load_workbook(path, data_only=True)` returns **cached values** (blank until
  recalc). You usually want formulas to edit, values to verify.
- **Array / dynamic formulas** load as `ArrayFormula` objects, not plain strings
  — check `getattr(cell.value, "text", cell.value)` when inspecting.
- **Styles don't cascade:** font, fill, border, number_format are set per cell.
  When filling a range, apply the style to every cell (or copy from a template
  cell), not just the first.
- **Merged cells:** only the top-left cell holds the value; the rest are
  read-only `MergedCell`s. `outline.py` lists merged ranges so you don't write
  into a covered cell.
- **`read_only=True`** streams large sheets without loading everything into
  memory (used by the error scan); you can't edit in that mode.
- **Tables / named ranges:** structured references like `DataTable[team_home]`
  resolve against a defined table or name — preserve those definitions when
  editing, or the formulas break.

## Dependencies

- Python: `openpyxl`, `pandas` (`pip install openpyxl pandas`).
- Recalc/render: LibreOffice (`brew install --cask libreoffice`) for `soffice`;
  poppler (`brew install poppler`) for `pdftoppm`. Microsoft Excel optional, for
  `--engine excel`.

## Known limitations

- **Pivot tables, charts:** openpyxl can create simple charts but cannot edit
  existing ones, and does not author pivot tables. Round-tripping a file with
  these generally preserves them, but don't expect to build them here.
- **Conditional formatting:** basic rules only.
- **Macros / VBA:** `.xlsm` macro code is preserved on a load/save round-trip but
  not authored or executed by this skill.
- **LibreOffice fidelity:** newer Excel functions evaluate to `#NAME?` (see
  Recalc engines). Pagination and fonts in `screenshot.py` are approximations.
- **External workbook links** are not resolved during recalc.
