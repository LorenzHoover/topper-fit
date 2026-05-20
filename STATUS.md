# FitMyTopper — Project Status

> This file is updated at the end of every session. Read this first when resuming.

---

## Current state: MVP pipeline complete — data research phase

**Last updated:** 2026-05-18  
**Last session:** Session 1 (full day) — full pipeline built end-to-end, Ranch data live

---

## What exists right now

```
FitMyTopper/
  app/
    api/fitments/route.js     ← GET /api/fitments?year=&make=&model= (live, working)
    components/
      FitmentSearch.js        ← search form + results table (Client Component)
    layout.js                 ← Next.js root layout (unchanged from scaffold)
    page.js                   ← home page, renders FitmentSearch
    globals.css               ← base styles (dark mode vars)
  lib/
    supabase.js               ← Supabase client (browser + server variants)
  supabase/migrations/
    20260518000001_create_bed_platforms.sql
    20260518000002_create_truck_models.sql
    20260518000003_create_topper_fitments.sql
  data/
    seed/
      bed_platforms.csv       ← 91 rows (Ranch data)
      truck_models.csv        ← 486 rows (expanded year ranges)
      topper_fitments.csv     ← 409 rows (Ranch fitments)
    sources/
      ranch_fitment_guide.pdf ← source PDF (July 2025)
      README.md               ← data source attribution log
  scripts/
    parse_ranch_pdf.py        ← PDF → 3 CSVs (Ranch-specific)
    load_to_supabase.py       ← CSVs → Supabase (generic loader)
    requirements.txt          ← pdfplumber, supabase
  .env.local                  ← Supabase keys (gitignored, never committed)
  .env.example                ← template for keys (committed)
  STATUS.md                   ← this file
  README.md                   ← project overview
```

---

## Database state (Supabase, live)

| Table | Rows | Source | Notes |
|-------|------|--------|-------|
| bed_platforms | 91 | Ranch PDF | Dimension fields mostly empty (Ranch doesn't publish specs) |
| truck_models | 486 | Ranch PDF | One row per year (expanded from ranges like "19+") |
| topper_fitments | 409 | Ranch PDF | Ranch brand only; all confidence=100 (OEM) |

RLS enabled on all tables: public SELECT, no public writes.

---

## Session log

### Session 1 — 2026-05-18 (full day)
**Completed:**
- [x] Scaffolded Next.js 16 (App Router, JavaScript)
- [x] Wired Supabase JS client (browser + server variants in lib/supabase.js)
- [x] Created .env.local with keys; .env.example committed
- [x] Wrote SQL migrations for 3 tables (bed_platforms, truck_models, topper_fitments)
- [x] Ran migrations in Supabase SQL editor + added RLS policies
- [x] Wrote Ranch PDF parser (scripts/parse_ranch_pdf.py) → 91/486/409 rows
- [x] Wrote Supabase loader (scripts/load_to_supabase.py) → data live in DB
- [x] Built API route: GET /api/fitments?year=&make=&model= (optional &cab= &bed=)
- [x] Built search UI stub with results table, confidence labels, fit notes
- [x] Fixed dark mode text color inheritance issue
- [x] Pushed all commits to GitHub

---

## Known gaps / next improvements

### Data gaps
- Ranch covers only 11 topper series (Ranch brand only). Need: LEER, ARE, SnugTop, ATC, Century
- bed_platforms has empty dimension fields (bed length in rail inches from Ranch is unreliable; need manufacturer spec sheets or personal measurements)
- 1st gen Toyota Tundra (2000–2006) not in Ranch data — user's personal truck
- Cab style missing on some Ford F-150 platforms (Ranch doesn't always specify)
- No truck trim data (Ranch chart doesn't go to that level)
- VIN decode not implemented yet

### UI improvements
- Model field is free-text — easy to mistype. Next: cascade dropdowns from DB
- No handling for "no Ranch coverage → suggest other brands" message
- No pagination (fine at current data scale)
- No mobile layout consideration yet

### Upcoming milestones

| # | Milestone | Blocked on |
|---|-----------|-----------|
| 1 | Add LEER fitment data | Find LEER PDF (Wayback Machine research) |
| 2 | Add ARE fitment data | Find ARE PDF |
| 3 | Cascade dropdowns in UI | Need distinct makes/models query from DB |
| 4 | VIN decode flow | Design + NHTSA API integration |
| 5 | Add truck dimensions | Spec sheet sources (not in Ranch PDF) |
| 6 | Deploy to Vercel | Anytime — codebase is deploy-ready |

---

## Data sources status

| Source | Status | Rows loaded |
|--------|--------|-------------|
| Ranch/LTA July 2025 PDF | ✅ Parsed & loaded | 409 fitments |
| LEER fitment guide | 🔍 Hunting (Wayback Machine) | — |
| ARE fitment guide | 🔍 Hunting (Wayback Machine) | — |
| SnugTop fitment guide | 🔍 Not yet started | — |
| Personal 2003 Tundra measurements | ⏳ Partial (dimensions noted) | Not yet loaded |

## Manufacturer research search strategies

```
# LEER
site:web.archive.org/web/* leertrucks.com fitment
site:web.archive.org/web/* leertrucks.com "application guide"
"leer" "fitment guide" filetype:pdf

# ARE
site:web.archive.org/web/* aretruck.com fit-guide
"A.R.E." "application guide" filetype:pdf site:archive.org

# SnugTop
site:web.archive.org/web/* snugtop.com fit
"snugtop" "fitment" filetype:pdf

# General
"camper shell" "fitment guide" filetype:pdf site:archive.org
"topper" "application guide" filetype:pdf site:archive.org
```
