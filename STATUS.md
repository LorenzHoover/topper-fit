# FitMyTopper — Project Status

> This file is updated at the end of every session. It's the first thing to read when resuming.

---

## Current state: Pre-scaffold — awaiting clarifying answers

**Last updated:** 2026-05-18  
**Last session:** Session 1 — project context ingested, memory initialized, clarifying questions posed

---

## What exists right now

```
FitMyTopper/
  data/
    seed/
      bed_platforms.csv     ← empty placeholder
      truck_models.csv      ← empty placeholder
      topper_fitments.csv   ← empty placeholder
    sources/
      ranch_fitment_guide.pdf   ← Ranch/LTA July 2025 PDF (not yet parsed)
  STATUS.md                 ← this file
```

No Next.js app yet. No git repo. No Supabase connection.

---

## Session log

### Session 1 — 2026-05-18
- Ingested full project brief
- Set up Claude memory system (user profile, data model, sources, session log)
- Created this STATUS.md
- Posed clarifying questions (see below)
- **Blocked:** waiting on answers + Supabase keys + GitHub URL

---

## Clarifying questions (open)

These need answers before scaffolding:

1. **Node version / package manager:** Do you have Node.js installed? (`node -v`) Which package manager do you prefer — `npm`, `yarn`, or `pnpm`? (I'd suggest `npm` to keep it simple.)

2. **Next.js app location:** Should the Next.js app live at the repo root, or in a subfolder like `app/` or `web/`? Given your Python data work also lives in this repo, a subfolder like `web/` keeps things clean — but root is more standard for pure Next.js deploys. My recommendation: **root of repo**, with `data/` and `scripts/` as siblings.

3. **Supabase project:** Have you created the Supabase project yet? When you do, I'll need: Project URL, anon (public) key, and service_role (secret) key. The service_role key goes in a `.env.local` file that is gitignored — never committed.

4. **GitHub repo:** What's the exact repo name you're creating? (`topper-fit` or something else?) I'll set the remote after `git init`.

5. **Python environment:** For the PDF parser and loader scripts, do you have a preferred Python version / virtualenv tool? (`python3 --version`, and do you use `venv`, `pyenv`, `conda`, or just system Python?)

6. **Ranch PDF parsing:** The PDF is at `data/sources/ranch_fitment_guide.pdf`. Do you know if it's a text-layer PDF (selectable text) or a scanned image? Run: `pdfinfo data/sources/ranch_fitment_guide.pdf` if you have poppler installed, or just try selecting text in Preview. This determines whether we use `pdfplumber` (text layer) or need `pytesseract` (OCR).

---

## Upcoming milestones

| # | Milestone | Status |
|---|-----------|--------|
| 1 | Scaffold Next.js app + git init | Blocked on Q1–Q4 |
| 2 | Push to GitHub | Blocked on Q4 |
| 3 | Supabase connection + env vars | Blocked on Q3 |
| 4 | SQL migrations (3 tables) | Ready to write |
| 5 | Python Ranch PDF parser → CSVs | Blocked on Q5–Q6 |
| 6 | Python loader → Supabase | Blocked on Q3, Q5 |
| 7 | API route: lookup by year/make/model | After migrations |
| 8 | Basic UI stub | After API route |

---

## Data sources

| Source | File | Status | Notes |
|--------|------|--------|-------|
| Ranch/LTA fitment guide (Jul 2025) | data/sources/ranch_fitment_guide.pdf | Unparsed | ~70 platforms, 11 series, W/X/U typology |
| Personal 2003 Tundra AC measurements | — | Partial | Missing rail XS dims + stake pocket count + rail-top bed length |
| tundras.com forum thread | URL in memory | Noted | AC/DC not interchangeable; SnugTop 01-06 AC confirmed |

**Manufacturer research priority** (for Wayback Machine hunting):
1. LEER, 2. ARE, 3. SnugTop, 4. ATC, 5. Century/Jason

---

## Known schema decisions

- Toppers keyed by `(brand, model_series, production_year_range)` — not just brand+model
- `confidence` (0–100) + `fit_notes` are required; binary fits/doesn't-fit is not enough
- VIN decode doesn't reliably return bed length or cab style — plan for UI follow-up questions
- Ranch PDF does NOT cover 1st gen Tundra (00-06) — important gap for personal test case
