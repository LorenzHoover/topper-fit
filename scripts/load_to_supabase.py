#!/usr/bin/env python3
"""
Load seed CSVs into Supabase.

Reads data/seed/*.csv and upserts into the three tables.
Uses the service_role key (bypasses RLS) — never run this in a browser context.

Requires:
  SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in environment,
  OR a .env.local file in the repo root.

Usage (from repo root):
  python3 scripts/load_to_supabase.py

Options:
  --dry-run   Print row counts and first row of each CSV without loading.
  --truncate  TRUNCATE tables before inserting (useful for re-seeding).
              Order matters: fitments → truck_models → platforms (FK dependency).
"""

import argparse
import csv
import os
import sys
from pathlib import Path

# ── Supabase client setup ─────────────────────────────────────────────────────

def load_env():
    """Read .env.local from repo root into os.environ (simple parser, no dotenv dep)."""
    env_path = Path(__file__).parent.parent / ".env.local"
    if not env_path.exists():
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())


def get_supabase_client():
    try:
        from supabase import create_client
    except ImportError:
        print("ERROR: supabase-py not installed. Run: pip3 install supabase")
        sys.exit(1)

    url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not key:
        print("ERROR: NEXT_PUBLIC_SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set.")
        print("  Make sure .env.local exists in the repo root, or export the vars.")
        sys.exit(1)

    return create_client(url, key)


# ── CSV helpers ───────────────────────────────────────────────────────────────

SEED_DIR = Path(__file__).parent.parent / "data" / "seed"

def read_csv(filename):
    path = SEED_DIR / filename
    if not path.exists():
        print(f"ERROR: {path} not found. Run parse_ranch_pdf.py first.")
        sys.exit(1)
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    return rows


def clean_row(row):
    """Replace empty string values with None so Postgres gets NULL not ''."""
    return {k: (v if v != "" else None) for k, v in row.items()}


def coerce_types(row, int_fields=(), float_fields=(), bool_fields=()):
    """Cast string CSV values to proper Python types before insertion."""
    out = dict(row)
    for field in int_fields:
        if out.get(field) is not None:
            try:
                out[field] = int(out[field])
            except (ValueError, TypeError):
                out[field] = None
    for field in float_fields:
        if out.get(field) is not None:
            try:
                out[field] = float(out[field])
            except (ValueError, TypeError):
                out[field] = None
    for field in bool_fields:
        if out.get(field) is not None:
            v = str(out[field]).lower()
            out[field] = v in ("true", "1", "yes")
    return out


# ── Upsert helpers ────────────────────────────────────────────────────────────

BATCH_SIZE = 200  # Supabase has a request size limit; batch to stay safe


def upsert_batches(client, table, rows, on_conflict, label):
    total = len(rows)
    inserted = 0
    for i in range(0, total, BATCH_SIZE):
        batch = rows[i : i + BATCH_SIZE]
        resp = (
            client.table(table)
            .upsert(batch, on_conflict=on_conflict)
            .execute()
        )
        inserted += len(batch)
        print(f"  {label}: {inserted}/{total}", end="\r")
    print(f"  {label}: {total}/{total} ✓")


# ── Load functions ────────────────────────────────────────────────────────────

def load_bed_platforms(client):
    rows = read_csv("bed_platforms.csv")
    cleaned = []
    int_f   = ("production_year_start", "production_year_end",
                "stake_pocket_count_per_side")
    float_f = ("bed_length_floor_inches", "bed_length_rail_inches",
                "bed_width_at_rail_inches", "bed_width_outer_inches",
                "bed_depth_inches", "rail_cross_section_width_inches",
                "rail_cross_section_height_inches", "stake_pocket_length_inches",
                "stake_pocket_width_inches")
    bool_f  = ("stake_pockets_present", "cab_camera_present")
    for row in rows:
        r = clean_row(row)
        r = coerce_types(r, int_fields=int_f, float_fields=float_f, bool_fields=bool_f)
        cleaned.append(r)
    upsert_batches(client, "bed_platforms", cleaned, "platform_id", "bed_platforms")


def load_truck_models(client):
    rows = read_csv("truck_models.csv")
    cleaned = []
    for row in rows:
        r = clean_row(row)
        r = coerce_types(r, int_fields=("year",))
        cleaned.append(r)
    upsert_batches(client, "truck_models", cleaned, "id", "truck_models")


def load_topper_fitments(client):
    rows = read_csv("topper_fitments.csv")
    cleaned = []
    for row in rows:
        r = clean_row(row)
        r = coerce_types(r, int_fields=(
            "topper_production_year_start", "topper_production_year_end", "confidence"
        ))
        cleaned.append(r)
    upsert_batches(client, "topper_fitments", cleaned, "id", "topper_fitments")


def truncate_all(client):
    # Must truncate in reverse FK order
    for table in ("topper_fitments", "truck_models", "bed_platforms"):
        client.rpc("truncate_table", {"tbl": table}).execute()
    print("Tables truncated.")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Load seed CSVs into Supabase.")
    parser.add_argument("--dry-run",  action="store_true",
                        help="Print counts without loading.")
    parser.add_argument("--truncate", action="store_true",
                        help="Truncate tables before inserting.")
    args = parser.parse_args()

    if args.dry_run:
        for name in ("bed_platforms.csv", "truck_models.csv", "topper_fitments.csv"):
            rows = read_csv(name)
            print(f"{name}: {len(rows)} rows")
            if rows:
                print(f"  First row: {rows[0]}")
        return

    load_env()
    client = get_supabase_client()

    if args.truncate:
        print("WARNING: --truncate will delete all existing rows.")
        confirm = input("Type 'yes' to continue: ").strip().lower()
        if confirm != "yes":
            print("Aborted.")
            return
        # Truncate via raw SQL (simpler than RPC for now)
        for table in ("topper_fitments", "truck_models", "bed_platforms"):
            client.table(table).delete().neq("id", -1).execute()
        print("Tables cleared.")

    print("Loading data into Supabase...")
    load_bed_platforms(client)
    load_truck_models(client)
    load_topper_fitments(client)
    print("\nAll done.")


if __name__ == "__main__":
    main()
