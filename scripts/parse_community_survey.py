#!/usr/bin/env python3
"""
Parse community survey responses (Google Form → Google Sheet CSV export)
into seed CSVs matching the bed_platforms / truck_models / topper_fitments schema.

Usage:
  1. In Google Sheets: File → Download → CSV (current sheet)
  2. Save to data/sources/community_survey_YYYY-MM-DD.csv
  3. python3 scripts/parse_community_survey.py --csv data/sources/community_survey_YYYY-MM-DD.csv

Output:
  data/parsed/community/
    community_YYYY-MM-DD_bed_platforms.csv
    community_YYYY-MM-DD_truck_models.csv
    community_YYYY-MM-DD_topper_fitments.csv

Columns expected from Google Form (in order, matching survey_design.md):
  Timestamp, Q1_truck_year, Q2_truck_make, Q3_truck_model, Q4_cab_style,
  Q5_bed_length_choice, Q5b_bed_inches, Q6_topper_brand, Q7_topper_model,
  Q8_topper_made_for, Q9_how_ended_up (multi), Q10_fit_rating, Q11_alignment (multi),
  Q12_overhang_notes, Q13_topper_mods, Q14_truck_mods, Q15_clamps,
  Q16_tips, Q17_recommend, Q18_photo (skip), Q19_handle, Q20_other
"""

import argparse
import csv
import re
import sys
from datetime import date
from pathlib import Path

OUT_DIR = Path("data/parsed/community")

# ── Column name → index mapping (update if form column order changes) ─────────
# These match the Google Form field labels. Adjust if you rename questions.
COL = {
    'timestamp':      0,
    'truck_year':     1,
    'truck_make':     2,
    'truck_model':    3,
    'cab_style':      4,
    'bed_length':     5,
    'bed_inches':     6,
    'topper_brand':   7,
    'topper_model':   8,
    'topper_made_for':9,
    'how_ended_up':   10,
    'fit_rating':     11,
    'alignment':      12,
    'overhang_notes': 13,
    'topper_mods':    14,
    'truck_mods':     15,
    'clamps':         16,
    'tips':           17,
    'recommend':      18,
    'photo':          19,   # skip
    'handle':         20,
    'other':          21,
}


# ── Confidence from fit rating ────────────────────────────────────────────────

def confidence_from_rating(rating):
    """Map Q10 answer text to confidence integer."""
    r = str(rating).lower()
    if 'perfect' in r:                       return 85
    if 'good enough' in r or 'minor' in r:   return 70
    if 'noticeable' in r:                    return 60
    if 'rough' in r or 'significant' in r:   return 50
    if "didn't work" in r or 'gave up' in r: return 0
    return 60   # default if unrecognised


# ── fit_type from Q9 and truck vs topper source ───────────────────────────────

def fit_type_from_responses(how_ended_up, truck_make, truck_model, topper_made_for):
    """
    Derive fit_type from Q9 multi-select and by comparing truck vs topper source truck.
    Priority: cross_make > cross_cab > cross_generation > with_modification
    """
    h = str(how_ended_up).lower()
    m = str(topper_made_for).lower()

    # Explicit cross-make signals
    if 'different make or model entirely' in h:
        return 'cross_make'

    # If topper_made_for mentions a clearly different make
    other_makes = ['ford', 'chevy', 'chevrolet', 'gmc', 'toyota', 'nissan',
                   'ram', 'dodge', 'jeep', 'honda']
    truck_make_lc = str(truck_make).lower()
    for mk in other_makes:
        if mk in m and mk not in truck_make_lc:
            return 'cross_make'

    if 'different cab' in h:
        return 'cross_cab'

    if 'different year' in h or 'previous gen' in h:
        return 'cross_generation'

    if 'modification' in h or 'deal' in h:
        return 'with_modification'

    # Fall back: if it needed mods, call it with_modification; otherwise cross_generation
    return 'with_modification'


# ── Cab style normalisation ────────────────────────────────────────────────────

def normalise_cab(raw):
    r = str(raw).lower()
    if 'regular' in r or '2-door' in r:
        return 'Regular Cab'
    if 'extended' in r or 'access' in r or 'jump' in r:
        return 'Extended Cab'
    if 'double' in r or 'quad' in r:
        return 'Double Cab'
    if 'crew' in r or 'supercrew' in r or 'crewmax' in r:
        return 'Crew Cab'
    return raw.split('(')[0].strip() if raw else ''


# ── Bed length normalisation ───────────────────────────────────────────────────

def normalise_bed(choice, inches_raw):
    """Return (bed_label, bed_inches_float|None)"""
    inches = None
    if inches_raw:
        m = re.search(r'(\d+\.?\d*)', str(inches_raw))
        if m:
            inches = float(m.group(1))

    # If we have a measured value, derive label from it
    if inches:
        if inches < 62:    label = 'Short Bed'
        elif inches < 74:  label = 'Mid Bed'
        else:              label = 'Long Bed'
        return label, inches

    # Fall back to choice
    c = str(choice).lower()
    if 'short' in c or "5'" in c:   return 'Short Bed', None
    if 'standard' in c or 'mid' in c or "6'" in c: return 'Mid Bed', None
    if 'long' in c or "8'" in c:    return 'Long Bed', None
    return choice or '', None


# ── Make normalisation ─────────────────────────────────────────────────────────

MAKE_NORM = {
    'chevy': 'Chevrolet', 'chevrolet': 'Chevrolet',
    'gmc': 'GMC', 'ford': 'Ford', 'toyota': 'Toyota',
    'nissan': 'Nissan', 'ram': 'Ram', 'dodge': 'Dodge',
    'jeep': 'Jeep', 'honda': 'Honda',
}

def normalise_make(raw):
    return MAKE_NORM.get(str(raw).strip().lower(), str(raw).strip().title())


# ── Platform ID ───────────────────────────────────────────────────────────────

def make_platform_id(make, model, year, cab, bed_label):
    m  = re.sub(r'[^A-Z0-9]', '', make.upper())[:4]
    mo = re.sub(r'[^A-Z0-9]', '', model.upper())[:6]
    yr = str(year)[-2:]
    c  = re.sub(r'[^A-Z]', '', (cab or '').upper())[:2]
    b  = re.sub(r'[^A-Z0-9]', '', (bed_label or '').upper())[:3]
    parts = [p for p in [m, mo, yr, c, b] if p]
    return 'COM-' + '-'.join(parts)   # COM- prefix marks community-sourced platforms


# ── Platform / truck_model field lists ────────────────────────────────────────

PLATFORM_FIELDS = [
    "platform_id","nickname","make","model_family","generation",
    "production_year_start","production_year_end","cab_style",
    "bed_length_class","bed_length_floor_inches","bed_length_rail_inches",
    "bed_width_at_rail_inches","bed_width_outer_inches","bed_depth_inches",
    "rail_profile_shape","rail_cross_section_width_inches",
    "rail_cross_section_height_inches","stake_pockets_present",
    "stake_pocket_count_per_side","stake_pocket_length_inches",
    "stake_pocket_width_inches","utility_track_system","cab_back_generation",
    "cab_camera_present","tailgate_variant","notes","source_urls",
]
TRUCK_MODEL_FIELDS = [
    "year","make","model","trim","cab_style","bed_length_label",
    "platform_id","vin_decodable_trim","vin_decodable_bed","notes","source_urls",
]
FITMENT_FIELDS = [
    "topper_brand","topper_model_series","topper_production_year_start",
    "topper_production_year_end","fits_platform_id","confidence","fit_type",
    "wrap_type","fit_notes","mounting_clamp_type","required_modifications",
    "source_urls","verified_by","source_effective_date",
    "has_custom_fit","has_skirted_sides","door_type","clamp_type_required",
    "bed_size_class","model_id_alias","camera_compatible",
]


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--csv', required=True, help='Path to Google Sheet CSV export')
    args = parser.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"ERROR: file not found: {csv_path}")
        sys.exit(1)

    today = date.today().isoformat()
    # Extract date from filename if present (e.g. community_survey_2026-06-01.csv)
    m = re.search(r'(\d{4}-\d{2}-\d{2})', csv_path.stem)
    file_date = m.group(1) if m else today

    platforms    = {}
    truck_models = []
    fitments     = []
    skipped      = []
    seen_tm      = set()

    with open(csv_path, newline='', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        header = next(reader, None)  # skip header row

        for row_num, row in enumerate(reader, start=2):
            if not row or not any(row):
                continue

            def col(key, default=''):
                idx = COL.get(key, -1)
                return row[idx].strip() if idx >= 0 and idx < len(row) else default

            # ── Parse truck fields ─────────────────────────────────────────
            year_raw = col('truck_year')
            try:
                year = int(re.sub(r'[^0-9]', '', year_raw))
                if year < 1980 or year > 2030:
                    raise ValueError
            except ValueError:
                skipped.append((row_num, f"bad year: '{year_raw}'"))
                continue

            make  = normalise_make(col('truck_make'))
            model = col('truck_model').strip().title()
            if not make or not model:
                skipped.append((row_num, "missing make or model"))
                continue

            cab_raw  = col('cab_style')
            cab      = normalise_cab(cab_raw)
            bed_choice = col('bed_length')
            bed_label, bed_inches = normalise_bed(bed_choice, col('bed_inches'))

            # ── Parse topper fields ────────────────────────────────────────
            topper_brand  = col('topper_brand').strip().title()
            topper_model  = col('topper_model').strip() or 'Unknown'
            topper_source = col('topper_made_for').strip()
            if not topper_brand:
                skipped.append((row_num, "missing topper brand"))
                continue

            # ── Fit fields ────────────────────────────────────────────────
            fit_rating   = col('fit_rating')
            confidence   = confidence_from_rating(fit_rating)
            how_ended_up = col('how_ended_up')
            fit_type     = fit_type_from_responses(how_ended_up, make, model, topper_source)

            # Build fit notes from multiple answers
            notes_parts = []
            if topper_source:
                notes_parts.append(f"Topper made for: {topper_source}")
            overhang = col('overhang_notes')
            if overhang:
                notes_parts.append(f"Overhang/gap: {overhang}")
            alignment = col('alignment')
            if alignment and 'fits great' not in alignment.lower():
                notes_parts.append(f"Alignment issues: {alignment}")
            tips = col('tips')
            if tips:
                notes_parts.append(f"Tips: {tips}")
            handle = col('handle')
            if handle:
                notes_parts.append(f"Reported by: {handle}")
            fit_notes = ' | '.join(notes_parts)

            # Required modifications
            mods_parts = []
            topper_mods = col('topper_mods')
            truck_mods  = col('truck_mods')
            clamps      = col('clamps')
            if topper_mods: mods_parts.append(f"Topper: {topper_mods}")
            if truck_mods:  mods_parts.append(f"Truck: {truck_mods}")
            if clamps:      mods_parts.append(f"Clamps: {clamps}")
            required_mods = ' | '.join(mods_parts)

            # ── Platform ──────────────────────────────────────────────────
            platform_id = make_platform_id(make, model, year, cab, bed_label)

            if platform_id not in platforms:
                platforms[platform_id] = {
                    'platform_id':           platform_id,
                    'nickname':              f"{year} {make} {model} {cab}".strip(),
                    'make':                  make,
                    'model_family':          model,
                    'generation':            '',
                    'production_year_start': year,
                    'production_year_end':   year,
                    'cab_style':             cab,
                    'bed_length_class':      bed_label,
                    'bed_length_floor_inches': bed_inches or '',
                    'bed_length_rail_inches':  '',
                    'bed_width_at_rail_inches':'',
                    'bed_width_outer_inches':  '',
                    'bed_depth_inches':        '',
                    'rail_profile_shape':      '',
                    'rail_cross_section_width_inches':  '',
                    'rail_cross_section_height_inches': '',
                    'stake_pockets_present':   '',
                    'stake_pocket_count_per_side': '',
                    'stake_pocket_length_inches': '',
                    'stake_pocket_width_inches': '',
                    'utility_track_system':    'none',
                    'cab_back_generation':     '',
                    'cab_camera_present':      '',
                    'tailgate_variant':        'Standard',
                    'notes':                   'Community-reported platform',
                    'source_urls':             f'community_survey_{file_date}.csv',
                }
            else:
                # Expand year range if this truck year is outside existing range
                existing = platforms[platform_id]
                existing['production_year_start'] = min(existing['production_year_start'], year)
                existing['production_year_end']   = max(existing['production_year_end'], year)

            # ── truck_models (one row per year) ───────────────────────────
            tm_key = (year, make, model, cab, bed_label)
            if tm_key not in seen_tm:
                seen_tm.add(tm_key)
                truck_models.append({
                    'year':              year,
                    'make':              make,
                    'model':             model,
                    'trim':              '',
                    'cab_style':         cab,
                    'bed_length_label':  bed_label,
                    'platform_id':       platform_id,
                    'vin_decodable_trim':'no',
                    'vin_decodable_bed': 'no',
                    'notes':             'Community-reported',
                    'source_urls':       f'community_survey_{file_date}.csv',
                })

            # ── topper_fitments ───────────────────────────────────────────
            # Skip rows where someone said it didn't work (confidence=0)
            # Those would be incompatible rows — useful but need manual review
            if confidence == 0:
                print(f"  Row {row_num}: fit failed — skipping fitment row (confidence=0). Manual review: {topper_brand} on {year} {make} {model}")
                continue

            fitments.append({
                'topper_brand':                topper_brand,
                'topper_model_series':         topper_model,
                'topper_production_year_start':'',
                'topper_production_year_end':  '',
                'fits_platform_id':            platform_id,
                'confidence':                  confidence,
                'fit_type':                    fit_type,
                'wrap_type':                   '',     # unknown from survey
                'fit_notes':                   fit_notes,
                'mounting_clamp_type':         clamps,
                'required_modifications':      required_mods,
                'source_urls':                 f'community_survey_{file_date}.csv',
                'verified_by':                 'owner_report',
                'source_effective_date':       file_date,
                'has_custom_fit':              '',
                'has_skirted_sides':           '',
                'door_type':                   '',
                'clamp_type_required':         clamps,
                'bed_size_class':              bed_label,
                'model_id_alias':              '',
                'camera_compatible':           '',
            })

    # ── Write CSVs ────────────────────────────────────────────────────────────
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    prefix = f"community_{file_date}"

    plat_rows = list(platforms.values())
    with open(OUT_DIR / f"{prefix}_bed_platforms.csv", 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=PLATFORM_FIELDS)
        w.writeheader(); w.writerows(plat_rows)
    print(f"bed_platforms              : {len(plat_rows)} rows")

    with open(OUT_DIR / f"{prefix}_truck_models.csv", 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=TRUCK_MODEL_FIELDS)
        w.writeheader(); w.writerows(truck_models)
    print(f"truck_models               : {len(truck_models)} rows")

    with open(OUT_DIR / f"{prefix}_topper_fitments.csv", 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=FITMENT_FIELDS)
        w.writeheader(); w.writerows(fitments)
    print(f"topper_fitments            : {len(fitments)} rows")

    if skipped:
        print(f"\nSkipped {len(skipped)} rows:")
        for row_num, reason in skipped:
            print(f"  Row {row_num}: {reason}")

    print(f"\nDone. Review {OUT_DIR}/ before loading.")
    print(f"Load with: python3 scripts/load_to_supabase.py --dir {OUT_DIR}")


if __name__ == '__main__':
    main()
