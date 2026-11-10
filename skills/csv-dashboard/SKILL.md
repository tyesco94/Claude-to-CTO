---
name: csv-dashboard
description: Turn a CSV or Excel file into a polished, on-brand interactive HTML dashboard. Use whenever the user uploads tabular data (CSV, XLSX, TSV) and asks for a dashboard, report, visualization, or "make this readable".
---

# CSV → Interactive Dashboard

## Brand settings (edit these once)
- Primary color: #2563EB
- Accent color: #F59E0B
- Background: #0F172A (dark) / #FFFFFF (light)
- Font: Inter, system-ui, sans-serif
- Logo URL or text: YOUR BRAND

## Steps
1. **Load and inspect** the file. Report row/column counts, column types, nulls, duplicates.
2. **Clean the data** before charting:
   - Fix broken/misaligned rows, trim whitespace, normalize headers to Title Case.
   - Parse dates and numbers (strip $, %, commas).
   - Remove exact duplicates; fill or flag missing values (state which).
   - List every cleaning action in a short "Data notes" section.
3. **Pick the story**: identify 3–5 KPIs (totals, growth %, averages) and the 3–4 most useful charts:
   - Time column → line chart of the key metric over time.
   - Category column → bar chart, sorted descending.
   - Part-of-whole with ≤6 parts → donut; otherwise bar.
4. **Build ONE self-contained HTML file** using Chart.js from cdnjs:
   - Header with logo/title and date range.
   - KPI cards row (value, label, change vs previous period when computable).
   - Chart grid (2 columns desktop, 1 on mobile).
   - Filters: dropdown for each low-cardinality category column + date range if dates exist; filters update all charts and KPIs.
   - Sortable, searchable data table at the bottom.
5. **Always use the same layout and brand settings above** so every dashboard looks consistent.
6. Finish with a 3-bullet "What the data says" summary in chat.

## Rules
- Never invent data. If a metric can't be computed, omit it.
- Format numbers (1,234 / $12.3K / 4.5%).
