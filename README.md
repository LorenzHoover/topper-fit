# topper-fit

Truck topper fitment lookup utility. Enter your truck (year / make / model / trim / cab / bed) and get a ranked list of camper shells / toppers that fit, with confidence scores and fit notes.

## Stack

- **Frontend + API:** Next.js 16 (App Router), JavaScript
- **Database:** Supabase (hosted Postgres)
- **Hosting:** Vercel
- **Data pipeline:** Python (PDF parsers, ETL scripts)

## Project structure

```
├── app/                  Next.js App Router pages and API routes
├── lib/
│   └── supabase.js       Supabase client (browser + server variants)
├── supabase/
│   └── migrations/       Version-controlled SQL migrations (run manually in Supabase SQL editor)
├── data/
│   ├── seed/             CSV files matching schema (populated by Python parsers)
│   └── sources/          Raw source files (PDFs, etc.) + README documenting each source
├── scripts/              Python data scripts (parsers, loaders) — coming soon
├── .env.example          Copy to .env.local and fill in real keys
└── STATUS.md             Running session log — read this first when resuming work
```

## Getting started

```bash
npm install
cp .env.example .env.local  # fill in your Supabase keys
npm run dev
```

## Database migrations

Migrations live in `supabase/migrations/` as plain SQL files. Run them in order in the Supabase project's SQL editor (or via `supabase db push` if using the CLI).

## Data sources

See [data/sources/README.md](data/sources/README.md) for attribution and notes on every data source.

## Status

See [STATUS.md](STATUS.md) for current session log and upcoming milestones.
