#!/usr/bin/env python3
"""
Parse Ranch/LTA Manufacturing fitment guide PDF (July 2025) into seed CSVs.

Writes three files:
  data/seed/bed_platforms.csv
  data/seed/truck_models.csv
  data/seed/topper_fitments.csv

Run from repo root:
  python3 scripts/parse_ranch_pdf.py
"""

import csv
import re
from pathlib import Path

import pdfplumber

PDF_PATH = Path("data/sources/ranch_fitment_guide.pdf")
SEED_DIR = Path("data/seed")
SOURCE_URL = "data/sources/ranch_fitment_guide.pdf"
CURRENT_YEAR = 2025  # cap for "19+" style year ranges

# ── Topper series ────────────────────────────────────────────────────────────

# Canonical names in column order (columns 3–13 in every table row).
SERIES_NAMES = [
    "Sport Wrap", "Legacy", "Echo", "Sierra/Xtra", "WorkForce",
    "Fusion Classic", "Fusion", "Premier", "ICON", "Skyline", "XD",
]

# Header cell text → canonical series name (handles per-page abbreviations).
SERIES_ALIASES = {
    "Wrap":             "Sport Wrap",
    "Sport Wrap":       "Sport Wrap",
    "Fusion CL":        "Fusion Classic",
    "Fusion\nClassic":  "Fusion Classic",
    "Fusion Classic":   "Fusion Classic",
    "Fusion":           "Fusion",
}


def normalize_series(raw):
    return SERIES_ALIASES.get(raw.strip(), raw.strip())


# ── Year parsing ─────────────────────────────────────────────────────────────

def parse_year_range(year_str):
    """
    '19+'    → (2019, None)
    '2020+'  → (2020, None)
    '15-20'  → (2015, 2020)
    '19-24*' → (2019, 2024)   asterisk stripped
    """
    s = re.sub(r'[*]', '', year_str).strip()
    if s.endswith('+'):
        base = s[:-1]
        year = int(base) if len(base) == 4 else int('20' + base)
        return year, None
    if '-' in s:
        left, right = s.split('-', 1)
        start = int(left) if len(left) == 4 else int('20' + left)
        end   = int(right) if len(right) == 4 else int('20' + right)
        return start, end
    # Single year
    y = int(s) if len(s) == 4 else int('20' + s)
    return y, y


# ── Make / model extraction ───────────────────────────────────────────────────

def extract_make_model(truck_name):
    """
    Return (make, model_family) from raw truck name.
    For shared platforms (e.g. 'Silverado / Sierra') returns the primary make;
    callers that need both should use is_shared_platform().
    """
    t = truck_name.strip()

    if re.search(r'Colorado', t, re.I):
        return "Chevrolet", "Colorado"
    if re.search(r'Canyon', t, re.I):
        return "GMC", "Canyon"
    if re.search(r'Silverado.+2500|2500 HD', t, re.I) and 'GMC' not in t:
        return "Chevrolet", "Silverado 2500"
    if re.search(r'Silverado', t, re.I):
        return "Chevrolet", "Silverado 1500"
    if re.search(r'GMC Sierra.+2500|Sierra 2500', t, re.I):
        return "GMC", "Sierra 2500"
    if re.search(r'GMC Sierra', t, re.I):
        return "GMC", "Sierra 1500"
    if re.search(r'Silverado / Sierra.+2500|Sierra \(2019 HD2500\)', t, re.I):
        return "Chevrolet", "Silverado 2500"    # primary; GMC Sierra 2500 added separately
    if re.search(r'Silverado / Sierra|Chev/GMC', t, re.I):
        return "Chevrolet", "Silverado 1500"    # primary; GMC Sierra 1500 added separately
    if re.search(r'F150|F-150|F 150', t, re.I):
        return "Ford", "F-150"
    if re.search(r'F250|F-250|F 250', t, re.I):
        return "Ford", "F-250"
    if re.search(r'F350|F-350|F 350', t, re.I):
        return "Ford", "F-350"
    if re.search(r'Maverick', t, re.I):
        return "Ford", "Maverick"
    if re.search(r'Ranger', t, re.I):
        return "Ford", "Ranger"
    if re.search(r'Dodge|RAM|Ram', t, re.I):
        if re.search(r'2500|3500|HD', t, re.I):
            return "Ram", "2500"
        return "Ram", "1500"
    if re.search(r'Tundra', t, re.I):
        return "Toyota", "Tundra"
    if re.search(r'Tacoma', t, re.I):
        return "Toyota", "Tacoma"
    if re.search(r'Frontier', t, re.I):
        return "Nissan", "Frontier"
    if re.search(r'Gladiator', t, re.I):
        return "Jeep", "Gladiator"

    return "Unknown", truck_name[:30]


def is_shared_platform(truck_name):
    """
    Returns list of (make, model_family) for cross-make platforms.
    Empty list means single-make.
    """
    t = truck_name.strip()
    if re.search(r'Silverado / Sierra.+2500|Sierra \(2019 HD2500\)', t, re.I):
        return [("Chevrolet", "Silverado 2500"), ("GMC", "Sierra 2500")]
    if re.search(r'Silverado / Sierra', t, re.I):
        return [("Chevrolet", "Silverado 1500"), ("GMC", "Sierra 1500")]
    if re.search(r'Chev/GMC.*Colorado.*Canyon|Colorado/Canyon', t, re.I):
        return [("Chevrolet", "Colorado"), ("GMC", "Canyon")]
    if re.search(r'Chev/GMC', t, re.I):
        return [("Chevrolet", "Silverado 1500"), ("GMC", "Sierra 1500")]
    return []


# ── Cab / bed / tailgate extraction ──────────────────────────────────────────

def extract_cab_style(truck_name, bed_size_str):
    combined = (truck_name + " " + bed_size_str).lower()
    if "crewmax" in combined or "crew max" in combined:
        return "CrewMax"
    if "super crew" in combined:
        return "SuperCrew"
    if "crew cab" in combined:
        return "Crew Cab"
    # "cc" as standalone token
    if re.search(r'\bcc\b', combined):
        return "Crew Cab"
    if "double cab" in combined or "dbl cab" in combined:
        return "Double Cab"
    if re.search(r'\bdc\b|\bdc/rc\b', combined):
        return "Double Cab"
    if "access cab" in combined or re.search(r'\bacc\b', combined):
        return "Access Cab"
    if re.search(r'\bxc\b|xtracab|sbxc', combined):
        return "Access Cab"
    if "reg. cab" in combined or "reg cab" in combined or "regular cab" in combined:
        return "Regular Cab"
    if re.search(r'\brc\b', combined):
        return "Regular Cab"
    if "ext" in combined:
        return "Extended Cab"
    if re.search(r'\bquad\b', combined):
        return "Quad Cab"
    if re.search(r'\bmega\b', combined):
        return "Mega Cab"
    return None


def extract_tailgate_variant(truck_name, bed_size_str):
    combined = (truck_name + " " + bed_size_str).lower()
    if "multiflex" in combined or re.search(r'\bmf\b', combined):
        return "MultiFlex"
    if "multipro" in combined or re.search(r'\bmp\b', combined):
        return "MultiPro"
    if "pro access" in combined:
        return "Pro Access"
    return "Standard"


def extract_bed_length_label(bed_size_str):
    """Return a clean inch-based label, e.g. '70"', '5\'6"', 'Long Bed'."""
    s = bed_size_str.strip()
    # feet+inch: 5'6" or 5' 5"
    m = re.search(r"(\d+)['′]\s*(\d+)[\"″]?", s)
    if m:
        return f"{m.group(1)}'{m.group(2)}\""
    # plain inches
    m = re.search(r"([\d]+(?:\.[\d]+)?)[\"″]", s)
    if m:
        return m.group(0)
    if re.search(r'\bLB\b', s, re.I):
        return "Long Bed"
    if re.search(r'\bSB\b', s, re.I):
        return "Short Bed"
    return s


def bed_to_inches(bed_size_str):
    """Convert bed size string to a float in inches, or None."""
    s = bed_size_str.strip()
    m = re.search(r"(\d+)['′]\s*(\d+)", s)
    if m:
        return int(m.group(1)) * 12 + int(m.group(2))
    m = re.search(r"([\d]+(?:\.[\d]+)?)[\"″]", s)
    if m:
        return float(m.group(1))
    # "SB 6.5" = 6.5 ft = 78"
    m = re.search(r"(\d+(?:\.\d+)?)\s*ft", s, re.I)
    if m:
        return float(m.group(1)) * 12
    return None


def has_camera_note(text):
    return bool(re.search(r'camera|w/camera', text, re.I))


# ── Platform ID generation ────────────────────────────────────────────────────

MAKE_CODES = {
    "Chevrolet": "CHEV", "GMC": "GMC", "Ford": "FORD",
    "Ram": "RAM", "Toyota": "TOY", "Nissan": "NIS",
    "Jeep": "JEEP", "Unknown": "UNK",
}
MODEL_CODES = {
    "Silverado 1500": "S15",  "Silverado 2500": "S25",
    "Sierra 1500":    "SRA",  "Sierra 2500":    "SRA25",
    "F-150": "F150", "F-250": "F250", "F-350": "F350",
    "Maverick": "MAV", "Ranger": "RNG",
    "1500": "R15",   "2500": "R25",
    "Tundra": "TUN", "Tacoma": "TAC",
    "Colorado": "COL", "Canyon": "CAN",
    "Frontier": "FRONT", "Gladiator": "GLAD",
}
CAB_CODES = {
    "Crew Cab": "CC", "Double Cab": "DC", "Access Cab": "AC",
    "Regular Cab": "RC", "CrewMax": "CM", "SuperCrew": "SC",
    "Extended Cab": "XC", "Quad Cab": "QC", "Mega Cab": "MC",
}
TAILGATE_CODES = {
    "MultiFlex": "MF", "MultiPro": "MP", "Pro Access": "PA",
}


def make_platform_id(make, model_family, year_start, year_end,
                     cab_style, bed_label, tailgate_variant):
    m  = MAKE_CODES.get(make, make[:4].upper())
    mo = MODEL_CODES.get(model_family, re.sub(r'[^A-Z0-9]', '', model_family.upper())[:6])

    if year_end is None:
        yr = f"{str(year_start)[-2:]}P"
    elif year_start == year_end:
        yr = str(year_start)[-2:]
    else:
        yr = f"{str(year_start)[-2:]}-{str(year_end)[-2:]}"

    cab = CAB_CODES.get(cab_style, "") if cab_style else ""

    # Sanitize bed label to alphanumeric
    bed_raw = re.sub(r"['\"]", "", bed_label)
    bed = re.sub(r'[^A-Z0-9]', '', bed_raw.upper())[:6]

    parts = [p for p in [m, mo, yr, cab, bed] if p]
    base_id = "-".join(parts)

    if tailgate_variant and tailgate_variant != "Standard":
        tg = TAILGATE_CODES.get(tailgate_variant, tailgate_variant[:2].upper())
        base_id += f"-{tg}"

    return base_id


# ── Cell value parsing ────────────────────────────────────────────────────────

def parse_cell(cell_value):
    """
    Return list of (wrap_type, fit_type, extra_note) tuples.
    Empty cell → [].
    'W'       → [('W', 'OEM', '')]
    'X'       → [('X', 'OEM', '')]
    'U'       → [('U', 'universal', '')]
    'W - X'   → [('W', 'OEM', ''), ('X', 'OEM', '')]
    'W*'      → [('W', 'OEM', '')]   (asterisk = "see notes"; note stored in fit_notes)
    'U*'      → [('U', 'universal', '')]
    'X*MidRise' → [('X', 'OEM', 'MidRise')]
    """
    if not cell_value:
        return []
    raw = cell_value.strip()
    if not raw:
        return []

    # Separate any note after first asterisk
    if '*' in raw:
        base, _, note_part = raw.partition('*')
        extra = note_part.strip()
    else:
        base = raw
        extra = ""

    base = base.strip()

    if re.search(r'W\s*-\s*X', base, re.I):
        return [("W", "OEM", extra), ("X", "OEM", extra)]
    if base == "W":
        return [("W", "OEM", extra)]
    if base == "X":
        return [("X", "OEM", extra)]
    if base == "U":
        return [("U", "universal", extra)]
    # Fallback: contains W/X/U somewhere
    if "W" in base:
        return [("W", "OEM", extra)]
    if "X" in base:
        return [("X", "OEM", extra)]
    if "U" in base:
        return [("U", "universal", extra)]
    return []


# ── Section header detection ──────────────────────────────────────────────────

def is_section_header(row):
    """
    True when a mid-table row is a new make section header
    (e.g. DODGE/RAM row embedded inside the Ford table).
    Returns (True, make_str) or (False, None).
    """
    if not row or len(row) < 2:
        return False, None
    col1 = (row[1] or "").strip()
    col2 = (row[2] or "").strip()
    if col1 == "Year" and col2.startswith("Bed Size"):
        make_str = (row[0] or "").strip()
        return True, make_str
    return False, None


def get_make_from_header(header_cell):
    h = (header_cell or "").strip().upper()
    if "CHEVROLET" in h or "GMC" in h:
        return "CHEVROLET/GMC"
    if "DODGE" in h or "RAM" in h:
        return "DODGE/RAM"
    if "FORD" in h:
        return "FORD"
    if "TOYOTA" in h:
        return "TOYOTA"
    if "NISSAN" in h:
        return "NISSAN"
    if "JEEP" in h:
        return "JEEP"
    return h


# ── CSV field lists (match migration column order) ────────────────────────────

PLATFORM_FIELDS = [
    "platform_id", "nickname", "make", "model_family", "generation",
    "production_year_start", "production_year_end", "cab_style",
    "bed_length_class", "bed_length_floor_inches", "bed_length_rail_inches",
    "bed_width_at_rail_inches", "bed_width_outer_inches", "bed_depth_inches",
    "rail_profile_shape", "rail_cross_section_width_inches",
    "rail_cross_section_height_inches", "stake_pockets_present",
    "stake_pocket_count_per_side", "stake_pocket_length_inches",
    "stake_pocket_width_inches", "utility_track_system", "cab_back_generation",
    "cab_camera_present", "tailgate_variant", "notes", "source_urls",
]

TRUCK_MODEL_FIELDS = [
    "year", "make", "model", "trim", "cab_style", "bed_length_label",
    "platform_id", "vin_decodable_trim", "vin_decodable_bed", "notes", "source_urls",
]

FITMENT_FIELDS = [
    "topper_brand", "topper_model_series", "topper_production_year_start",
    "topper_production_year_end", "fits_platform_id", "confidence", "fit_type",
    "wrap_type", "fit_notes", "mounting_clamp_type", "required_modifications",
    "source_urls", "verified_by",
]


# ── Main ──────────────────────────────────────────────────────────────────────

def build_platform_row(platform_id, truck_name, make, model_family,
                       year_start, year_end, cab_style, bed_label,
                       bed_inches, tailgate_variant, cam_note, extra_notes):
    return {
        "platform_id":                     platform_id,
        "nickname":                        f"{truck_name.replace(chr(10), ' ').strip()} ({year_start}–{year_end or 'present'})",
        "make":                            make,
        "model_family":                    model_family,
        "generation":                      "",
        "production_year_start":           year_start,
        "production_year_end":             year_end if year_end else "",
        "cab_style":                       cab_style or "",
        "bed_length_class":                "",
        "bed_length_floor_inches":         "",
        "bed_length_rail_inches":          bed_inches if bed_inches else "",
        "bed_width_at_rail_inches":        "",
        "bed_width_outer_inches":          "",
        "bed_depth_inches":                "",
        "rail_profile_shape":              "",
        "rail_cross_section_width_inches": "",
        "rail_cross_section_height_inches":"",
        "stake_pockets_present":           "",
        "stake_pocket_count_per_side":     "",
        "stake_pocket_length_inches":      "",
        "stake_pocket_width_inches":       "",
        "utility_track_system":            "none",
        "cab_back_generation":             "",
        "cab_camera_present":              cam_note,
        "tailgate_variant":                tailgate_variant,
        "notes":                           extra_notes,
        "source_urls":                     SOURCE_URL,
    }


def build_truck_model_rows(platform_id, make, model_family,
                           year_start, year_end, cab_style, bed_label):
    """One row per year in the range."""
    end = year_end if year_end else CURRENT_YEAR
    rows = []
    for yr in range(year_start, end + 1):
        rows.append({
            "year":              yr,
            "make":              make,
            "model":             model_family,
            "trim":              "",
            "cab_style":         cab_style or "",
            "bed_length_label":  bed_label,
            "platform_id":       platform_id,
            "vin_decodable_trim":"partial",
            "vin_decodable_bed": "partial",
            "notes":             "",
            "source_urls":       SOURCE_URL,
        })
    return rows


def extract_name_and_notes(raw_name):
    """
    Split newline-embedded notes from truck name.
    'Dodge SB 67" Crew / Quad\nw/o 3rd Brake Light Camera'
    → name='Dodge SB 67" Crew / Quad', note='w/o 3rd Brake Light Camera'
    """
    parts = raw_name.split('\n', 1)
    name = parts[0].strip()
    note = parts[1].strip() if len(parts) > 1 else ""
    return name, note


def main():
    platforms    = {}  # platform_id → dict (deduplicated)
    truck_models = []
    fitments     = []

    # Track IDs we've already added truck_model rows for
    # (year, make, model, cab, bed) → True — avoids cross-make dupes
    seen_truck_model_keys = set()

    with pdfplumber.open(PDF_PATH) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            tables = page.extract_tables()
            for table in tables:
                if not table or len(table) < 2:
                    continue

                # Parse header row to get column→series mapping
                header = table[0]
                current_section = get_make_from_header(header[0])
                series_cols = []  # list of (col_index, canonical_series_name)
                for i, cell in enumerate(header[3:], start=3):
                    if cell and cell.strip():
                        series_cols.append((i, normalize_series(cell)))

                for row in table[1:]:
                    if not row or not row[0]:
                        continue

                    # Mid-table section header (e.g. DODGE/RAM inside Ford table)
                    is_hdr, new_section = is_section_header(row)
                    if is_hdr:
                        current_section = get_make_from_header(new_section)
                        # Re-derive series_cols from this header row
                        series_cols = []
                        for i, cell in enumerate(row[3:], start=3):
                            if cell and cell.strip():
                                series_cols.append((i, normalize_series(cell)))
                        continue

                    raw_name   = (row[0] or "").strip()
                    year_str   = (row[1] or "").strip()
                    bed_str    = (row[2] or "").strip()

                    if not raw_name or not year_str:
                        continue

                    truck_name, inline_note = extract_name_and_notes(raw_name)

                    try:
                        year_start, year_end = parse_year_range(year_str)
                    except (ValueError, IndexError):
                        print(f"  WARNING: could not parse year '{year_str}' for '{truck_name}' — skipping")
                        continue

                    make, model_family  = extract_make_model(truck_name)
                    cab_style           = extract_cab_style(truck_name, bed_str)
                    tailgate_variant    = extract_tailgate_variant(truck_name, bed_str)
                    bed_label           = extract_bed_length_label(bed_str)
                    bed_inches          = bed_to_inches(bed_str)
                    cam_note            = has_camera_note(truck_name + " " + bed_str)

                    platform_id = make_platform_id(
                        make, model_family, year_start, year_end,
                        cab_style, bed_label, tailgate_variant
                    )

                    # Handle ID collisions with a counter suffix
                    if platform_id in platforms:
                        suffix = 2
                        while f"{platform_id}-{suffix}" in platforms:
                            suffix += 1
                        platform_id = f"{platform_id}-{suffix}"

                    # --- bed_platforms ---
                    platforms[platform_id] = build_platform_row(
                        platform_id, truck_name, make, model_family,
                        year_start, year_end, cab_style, bed_label,
                        bed_inches, tailgate_variant, cam_note, inline_note
                    )

                    # --- truck_models ---
                    # Primary make
                    for yr in range(year_start, (year_end or CURRENT_YEAR) + 1):
                        key = (yr, make, model_family, cab_style, bed_label)
                        if key not in seen_truck_model_keys:
                            seen_truck_model_keys.add(key)
                            truck_models.extend(build_truck_model_rows(
                                platform_id, make, model_family,
                                yr, yr, cab_style, bed_label
                            ))

                    # Secondary makes for shared platforms (Silverado/Sierra, etc.)
                    shared = is_shared_platform(truck_name)
                    for alt_make, alt_model in shared:
                        if alt_make == make:
                            continue  # already added above
                        for yr in range(year_start, (year_end or CURRENT_YEAR) + 1):
                            key = (yr, alt_make, alt_model, cab_style, bed_label)
                            if key not in seen_truck_model_keys:
                                seen_truck_model_keys.add(key)
                                truck_models.extend(build_truck_model_rows(
                                    platform_id, alt_make, alt_model,
                                    yr, yr, cab_style, bed_label
                                ))

                    # --- topper_fitments ---
                    for col_idx, series_name in series_cols:
                        if col_idx >= len(row):
                            continue
                        cell_val = row[col_idx] or ""
                        fits = parse_cell(cell_val)
                        for wrap_type, fit_type, extra_note in fits:
                            note_parts = [p for p in [inline_note, extra_note] if p]
                            fit_notes = "; ".join(note_parts)
                            fitments.append({
                                "topper_brand":                "Ranch",
                                "topper_model_series":         series_name,
                                "topper_production_year_start": "",
                                "topper_production_year_end":   "",
                                "fits_platform_id":            platform_id,
                                "confidence":                  100,
                                "fit_type":                    fit_type,
                                "wrap_type":                   wrap_type,
                                "fit_notes":                   fit_notes,
                                "mounting_clamp_type":         "",
                                "required_modifications":      "",
                                "source_urls":                 SOURCE_URL,
                                "verified_by":                 "manufacturer",
                            })

    # ── Write CSVs ────────────────────────────────────────────────────────────

    SEED_DIR.mkdir(parents=True, exist_ok=True)

    with open(SEED_DIR / "bed_platforms.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=PLATFORM_FIELDS)
        w.writeheader()
        w.writerows(platforms.values())
    print(f"bed_platforms.csv    : {len(platforms)} rows")

    with open(SEED_DIR / "truck_models.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=TRUCK_MODEL_FIELDS)
        w.writeheader()
        w.writerows(truck_models)
    print(f"truck_models.csv     : {len(truck_models)} rows")

    with open(SEED_DIR / "topper_fitments.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FITMENT_FIELDS)
        w.writeheader()
        w.writerows(fitments)
    print(f"topper_fitments.csv  : {len(fitments)} rows")

    print("\nDone. Review CSVs in data/seed/ before loading to Supabase.")


if __name__ == "__main__":
    main()
