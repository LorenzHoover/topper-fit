#!/usr/bin/env python3
"""
Parse ATC (LTA Manufacturing) fitment guide PDF (April 2022) into seed CSVs.

ATC is the sister brand to Ranch (same parent: LTA Manufacturing).
Same W/X/U typology, different model series names, older coverage including
1st-gen Toyota Tundra (2004-2006 DC, 2000-2006 SB).

Outputs (appended to existing CSVs — do NOT truncate before running):
  data/parsed/atc_2022-04_bed_platforms.csv
  data/parsed/atc_2022-04_truck_models.csv
  data/parsed/atc_2022-04_topper_fitments.csv

Then use load_to_supabase.py to ingest those files.

Run from repo root:
  python3 scripts/parse_atc_pdf.py
"""

import csv
import re
from pathlib import Path

import pdfplumber

PDF_PATH        = Path("data/sources/atc_2022-04.pdf")
OUT_DIR         = Path("data/parsed/atc")
SOURCE_URL      = "data/sources/atc_2022-04.pdf"
EFFECTIVE_DATE  = "2022-04-01"
CURRENT_YEAR    = 2025

# ── Series name mapping ───────────────────────────────────────────────────────
# ATC has 11 series. Column positions differ by table layout.
# These mappings were determined by inspecting header rows of each table type.
# See parse notes in docs/ for derivation.

# Chevy/GMC page — widest layout (~56 columns)
COLS_CHEVGMC = {
    12: "Wrap",
    17: "Classic",
    22: "Express",
    26: "LED/LTD",
    30: "WorkForce",
    35: "LER Classic",
    40: "LER",
    42: "LEX Classic",
    46: "LEX",
    50: "LHR",
    54: "LHR-XD",
}

# Dodge/Ram, Ford, Nissan pages — 42-column layout
COLS_STANDARD = {
    10: "Wrap",
    13: "Classic",
    16: "Express",
    19: "LED/LTD",
    22: "WorkForce",
    25: "LER Classic",
    28: "LER",
    31: "LEX Classic",
    34: "LEX",
    37: "LHR",
    40: "LHR-XD",
}

# Toyota page — 40-column layout
COLS_TOYOTA = {
     9: "Wrap",
    11: "Classic",
    14: "Express",
    17: "LED/LTD",
    20: "WorkForce",
    23: "LER Classic",
    26: "LER",
    29: "LEX Classic",
    32: "LEX",
    35: "LHR",
    38: "LHR-XD",
}

SECTION_COLS = {
    "CHEVROLET/GMC":   COLS_CHEVGMC,
    "DODGE/RAM":       COLS_STANDARD,
    "FORD":            COLS_STANDARD,
    "FORD (CONTINUED)": COLS_STANDARD,
    "NISSAN":          COLS_STANDARD,
    "TOYOTA":          COLS_TOYOTA,
}

# ── Year / bed / cab helpers (reused from Ranch parser) ──────────────────────

def _two_digit_year(s):
    """Convert 2-digit year string to 4-digit int. Years > 25 assumed 19xx."""
    y = int(s)
    return (1900 + y) if y > 25 else (2000 + y)


def _clean_year_token(tok):
    """Strip trailing non-digit noise (e.g. '22HD' → '22', '2022HD' → '2022')."""
    return re.sub(r'[^0-9]$', '', re.sub(r'[A-Za-z]+$', '', tok.strip()))


def parse_year_range(year_str):
    # Remove whitespace/asterisks; keep digits, +, -
    s = re.sub(r'[*\s]', '', str(year_str)).strip()
    if not s:
        return None, None
    if s.endswith('+'):
        base = _clean_year_token(s[:-1])
        y = int(base) if len(base) == 4 else _two_digit_year(base)
        return y, None
    if '-' in s:
        left, right = s.split('-', 1)
        left  = _clean_year_token(left)
        right = _clean_year_token(right)
        if not left or not right:
            return None, None
        start = int(left)  if len(left)  == 4 else _two_digit_year(left)
        end   = int(right) if len(right) == 4 else _two_digit_year(right)
        return start, end
    s = _clean_year_token(s)
    try:
        y = int(s) if len(s) == 4 else _two_digit_year(s)
        return y, y
    except ValueError:
        return None, None


def extract_make_model(truck_name):
    t = truck_name.strip()
    # Check Dodge/Ram BEFORE generic 2500/HD patterns to avoid false positives
    if re.search(r'Dakota', t, re.I):
        return "Dodge", "Dakota"
    if re.search(r'Dodge|RAM|Ram', t, re.I):
        if re.search(r'2500|3500|HD', t, re.I):
            return "Ram", "2500"
        return "Ram", "1500"
    if re.search(r'Colorado|Canyon', t, re.I):
        make = "Chevrolet" if re.search(r'Chev|Colorado', t, re.I) else "GMC"
        model = "Colorado" if "Colorado" in t else "Canyon"
        return make, model
    if re.search(r'Silverado.?2500|2500 HD', t, re.I) and 'GMC' not in t:
        return "Chevrolet", "Silverado 2500"
    if re.search(r'Silverado', t, re.I):
        return "Chevrolet", "Silverado 1500"
    if re.search(r'GMC Sierra.?2500|Sierra 2500|GMC\s+2500', t, re.I):
        return "GMC", "Sierra 2500"
    if re.search(r'GMC Sierra|GMC\s+1500', t, re.I):
        return "GMC", "Sierra 1500"
    if re.search(r'Silverado / Sierra|Chev/GMC', t, re.I):
        return "Chevrolet", "Silverado 1500"  # GMC added separately via is_shared_platform
    if re.search(r'F150|F-150', t, re.I):
        return "Ford", "F-150"
    if re.search(r'F250|F-250', t, re.I):
        return "Ford", "F-250"
    if re.search(r'Ranger', t, re.I):
        return "Ford", "Ranger"
    if re.search(r'Tundra', t, re.I):
        return "Toyota", "Tundra"
    if re.search(r'Tacoma', t, re.I):
        return "Toyota", "Tacoma"
    if re.search(r'Titan', t, re.I):
        return "Nissan", "Titan"
    if re.search(r'Frontier', t, re.I):
        return "Nissan", "Frontier"
    return "Unknown", t[:30]


def is_shared_platform(truck_name):
    t = truck_name
    if re.search(r'Silverado / Sierra.*2500|Sierra \(2019 HD2500\)', t, re.I):
        return [("Chevrolet", "Silverado 2500"), ("GMC", "Sierra 2500")]
    if re.search(r'Silverado / Sierra', t, re.I):
        return [("Chevrolet", "Silverado 1500"), ("GMC", "Sierra 1500")]
    if re.search(r'Chev/GMC.*Colorado.*Canyon|Colorado/Canyon', t, re.I):
        return [("Chevrolet", "Colorado"), ("GMC", "Canyon")]
    if re.search(r'Chev/GMC', t, re.I):
        return [("Chevrolet", "Silverado 1500"), ("GMC", "Sierra 1500")]
    return []


def extract_cab_style(truck_name, bed_str):
    c = (truck_name + " " + bed_str).lower()
    if "crewmax" in c or "crew max" in c:     return "CrewMax"
    if "super crew" in c:                      return "SuperCrew"
    if "crew cab" in c or re.search(r'\bcc\b', c): return "Crew Cab"
    if "double cab" in c or "dbl cab" in c:   return "Double Cab"
    if re.search(r'\bdc\b', c):               return "Double Cab"
    if "access cab" in c or re.search(r'\bacc\b|\bxc\b|\bsbxc\b', c): return "Access Cab"
    if "reg. cab" in c or "reg cab" in c or "std cab" in c: return "Regular Cab"
    if re.search(r'\brc\b|\bstd\b', c):       return "Regular Cab"
    if "quad" in c:                            return "Quad Cab"
    if "mega" in c:                            return "Mega Cab"
    if "ext" in c:                             return "Extended Cab"
    return None


def extract_tailgate_variant(truck_name, bed_str):
    c = (truck_name + " " + bed_str).lower()
    if "multiflex" in c or re.search(r'\bmf\b', c):  return "MultiFlex"
    if "multipro" in c  or re.search(r'\bmp\b', c):  return "MultiPro"
    if "pro access" in c:                              return "Pro Access"
    return "Standard"


def extract_bed_label(bed_str):
    s = bed_str.strip()
    m = re.search(r"(\d+)['′]\s*(\d+)[\"″]?", s)
    if m:
        return f"{m.group(1)}'{m.group(2)}\""
    m = re.search(r"([\d]+(?:\.[\d]+)?)[\"″'']", s)
    if m:
        return f'{m.group(1)}"'
    if re.search(r'\bLB\b', s, re.I): return "Long Bed"
    if re.search(r'\bSB\b', s, re.I): return "Short Bed"
    return s


def bed_to_inches(bed_str):
    s = bed_str.strip()
    # feet'inches notation: 5'6" or 5'6'' → feet*12 + inches
    m = re.search(r"(\d+)['′]\s*(\d+)", s)
    if m:
        return int(m.group(1)) * 12 + int(m.group(2))
    # Any numeric followed by a quote/apostrophe variant.
    # ATC PDF uses ' as an inch marker (e.g. 79.5', 70'), not always a foot marker.
    # Heuristic: values < 20 must be feet (no real truck bed is that short in inches).
    m = re.search(r"([\d]+(?:\.[\d]+)?)[\"″'']", s)
    if m:
        val = float(m.group(1))
        return val * 12 if val < 20 else val
    return None


MAKE_CODES  = {"Chevrolet":"CHEV","GMC":"GMC","Ford":"FORD","Ram":"RAM",
               "Dodge":"DDG","Toyota":"TOY","Nissan":"NIS","Jeep":"JEEP"}
MODEL_CODES = {
    "Silverado 1500":"S15","Silverado 2500":"S25",
    "Sierra 1500":"SRA","Sierra 2500":"SRA25",
    "F-150":"F150","F-250":"F250","Ranger":"RNG",
    "1500":"R15","2500":"R25","Dakota":"DAK",
    "Tundra":"TUN","Tacoma":"TAC",
    "Colorado":"COL","Canyon":"CAN",
    "Titan":"TTN","Frontier":"FRONT",
}
CAB_CODES = {
    "Crew Cab":"CC","Double Cab":"DC","Access Cab":"AC","Regular Cab":"RC",
    "CrewMax":"CM","SuperCrew":"SC","Extended Cab":"XC","Quad Cab":"QC","Mega Cab":"MC",
}
TAILGATE_CODES = {"MultiFlex":"MF","MultiPro":"MP","Pro Access":"PA"}


def make_platform_id(make, model_family, year_start, year_end,
                     cab_style, bed_label, tailgate_variant):
    m  = MAKE_CODES.get(make, make[:4].upper())
    mo = MODEL_CODES.get(model_family, re.sub(r'[^A-Z0-9]','',model_family.upper())[:6])
    yr = (f"{str(year_start)[-2:]}P" if year_end is None
          else str(year_start)[-2:] if year_start == year_end
          else f"{str(year_start)[-2:]}-{str(year_end)[-2:]}")
    cab = CAB_CODES.get(cab_style, "") if cab_style else ""
    bed = re.sub(r"['\"]", "", bed_label)
    bed = re.sub(r'[^A-Z0-9]', '', bed.upper())[:6]
    parts = [p for p in [m, mo, yr, cab, bed] if p]
    pid = "-".join(parts)
    if tailgate_variant and tailgate_variant != "Standard":
        tg = TAILGATE_CODES.get(tailgate_variant, tailgate_variant[:2].upper())
        pid += f"-{tg}"
    return pid


# ── Cell parsing ──────────────────────────────────────────────────────────────

def parse_cell(cell_value):
    """
    Returns list of (wrap_type, fit_type, extra_note).
    ATC uses same W/X/U typology as Ranch but 'X or W' instead of 'W - X'.
    Also handles 'COMING SOON' and 'COMING' (spans two rows in PDF).
    """
    if not cell_value:
        return []
    raw = str(cell_value).strip()
    if not raw:
        return []

    upper = raw.upper()

    # Future release placeholder
    if "COMING" in upper:
        return [("", "future_release", raw)]

    # Asterisk note extraction
    extra = ""
    if '*' in raw:
        base, _, note = raw.partition('*')
        raw   = base.strip()
        extra = note.strip()
        upper = raw.upper()

    if re.search(r'X\s+or\s+W|W\s+or\s+X|W\s*-\s*X|X\s*-\s*W', upper):
        return [("W", "OEM", extra), ("X", "OEM", extra)]
    if raw == "W":  return [("W", "OEM", extra)]
    if raw == "X":  return [("X", "OEM", extra)]
    if raw == "U":  return [("U", "universal", extra)]
    if raw == "XD": return [("X", "OEM", "LHR-XD")]  # seen in one Chevy row

    # Fallback: contains a recognizable code
    if "W" in upper: return [("W", "OEM", extra)]
    if "X" in upper: return [("X", "OEM", extra)]
    if "U" in upper: return [("U", "universal", extra)]
    return []


# ── Section detection ─────────────────────────────────────────────────────────

def detect_section(row):
    """
    Return the canonical section key if this row is a section header, else None.

    Header rows come in two forms:
      - col 0 has the section name, col 1 is empty  (e.g. ['FORD', '', ...])
      - col 0 is empty, col 1 has the section name  (echo row, e.g. ['', 'FORD', ...])

    Truck data rows always have a truck name in col 1 that is NOT an exact section name,
    so we require exact match (case-insensitive) to avoid false-positives like
    'Ford F150' or 'Toyota Tundra...' being treated as headers.
    """
    if not row:
        return None
    col0 = str(row[0] or '').strip()
    col1 = str(row[1] or '').strip() if len(row) > 1 else ''

    # Primary header: section name in col 0, col 1 empty
    if col0 and not col1:
        u = col0.upper()
        for key in SECTION_COLS:
            if u == key:
                return key
        # "FORD (Continued)" → matches "FORD (CONTINUED)"
        for key in SECTION_COLS:
            if u == key.upper():
                return key

    # Echo header: section name exactly in col 1, col 0 empty
    if col1 and not col0:
        u = col1.upper()
        for key in SECTION_COLS:
            if u == key:
                return key

    return None


def is_proper_data_row(row):
    """True if this looks like a parseable data row (truck name in col 1)."""
    if not row or len(row) < 8:
        return False
    col1 = row[1]
    if not col1 or str(col1).strip() == '':
        return False
    # Reject sub-header rows (col 1 is a section name like 'FORD')
    known_sections = {'CHEVROLET/GMC','FORD','FORD (CONTINUED)','DODGE/RAM','NISSAN','TOYOTA'}
    if str(col1).strip().upper() in known_sections:
        return False
    # Reject rows where col 1 looks like a series name
    known_series = {'Wrap','Classic','Express','Force','LTD','LER','LEX','LHR','LHR-XD','Year','Bed Size'}
    if str(col1).strip() in known_series:
        return False
    return True


def find_year_in_row(row):
    """Return (col_idx, year_str) for the first year-like value in cols 3-7."""
    for col in range(3, 8):
        if col >= len(row):
            break
        v = str(row[col] or '').strip()
        if re.match(r'\d{2}[+\-]|\d{4}[+\-]|\d{2}-\d{2}|\d{4}', v):
            return col, v
    return None, None


def find_bed_in_row(row, year_col):
    """Return (col_idx, bed_str) for the bed size field after year_col."""
    for col in range(year_col + 1, year_col + 5):
        if col >= len(row):
            break
        v = str(row[col] or '').strip()
        if v and v not in ('', 'None') and not re.match(r'\d{2}[+\-]|\d{4}[+\-]', v):
            return col, v
    return None, None


# ── CSV field lists ───────────────────────────────────────────────────────────

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
    platforms    = {}
    truck_models = []
    fitments     = []
    seen_tm_keys = set()

    skipped_garbage = 0
    skipped_no_year = 0

    current_section = None
    series_cols     = {}

    with pdfplumber.open(PDF_PATH) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                if not table:
                    continue

                for row in table:
                    if not row:
                        continue

                    # ── Detect section header ──────────────────────────────
                    sec = detect_section(row[:3])
                    if sec:
                        current_section = sec
                        series_cols = SECTION_COLS.get(sec, {})
                        continue

                    if not series_cols:
                        continue

                    # ── Garbage row: all data collapsed into col 0 ─────────
                    col0 = str(row[0] or '').strip()
                    col1 = str(row[1] or '').strip() if len(row) > 1 else ''

                    if col0 and not col1:
                        skipped_garbage += 1
                        continue   # best-effort parse not yet implemented

                    # ── Proper data row ────────────────────────────────────
                    if not is_proper_data_row(row):
                        continue

                    truck_name = col1

                    year_col, year_str = find_year_in_row(row)
                    if not year_str:
                        skipped_no_year += 1
                        continue

                    year_start, year_end = parse_year_range(year_str)
                    if year_start is None:
                        skipped_no_year += 1
                        continue

                    _, bed_str = find_bed_in_row(row, year_col)
                    bed_str = bed_str or ""

                    make, model_family = extract_make_model(truck_name)
                    cab_style         = extract_cab_style(truck_name, bed_str)
                    tailgate_variant  = extract_tailgate_variant(truck_name, bed_str)
                    bed_label         = extract_bed_label(bed_str)
                    bed_inches        = bed_to_inches(bed_str)

                    platform_id = make_platform_id(
                        make, model_family, year_start, year_end,
                        cab_style, bed_label, tailgate_variant
                    )

                    # Deduplicate with suffix
                    base_pid = platform_id
                    suffix = 2
                    while platform_id in platforms:
                        platform_id = f"{base_pid}-{suffix}"
                        suffix += 1

                    # ── bed_platforms ──────────────────────────────────────
                    name_clean = truck_name.replace('\n', ' ').strip()
                    platforms[platform_id] = {
                        "platform_id":              platform_id,
                        "nickname":                 f"{name_clean} ({year_start}–{year_end or 'present'})",
                        "make":                     make,
                        "model_family":             model_family,
                        "generation":               "",
                        "production_year_start":    year_start,
                        "production_year_end":      year_end or "",
                        "cab_style":                cab_style or "",
                        "bed_length_class":         "",
                        "bed_length_floor_inches":  "",
                        "bed_length_rail_inches":   bed_inches or "",
                        "bed_width_at_rail_inches": "",
                        "bed_width_outer_inches":   "",
                        "bed_depth_inches":         "",
                        "rail_profile_shape":       "",
                        "rail_cross_section_width_inches":  "",
                        "rail_cross_section_height_inches": "",
                        "stake_pockets_present":    "",
                        "stake_pocket_count_per_side": "",
                        "stake_pocket_length_inches": "",
                        "stake_pocket_width_inches":  "",
                        "utility_track_system":     "none",
                        "cab_back_generation":      "",
                        "cab_camera_present":       "",
                        "tailgate_variant":         tailgate_variant,
                        "notes":                    "",
                        "source_urls":              SOURCE_URL,
                    }

                    # ── truck_models ───────────────────────────────────────
                    end_yr = year_end or CURRENT_YEAR
                    for make_t, model_t in (is_shared_platform(truck_name) or [(make, model_family)]):
                        for yr in range(year_start, end_yr + 1):
                            k = (yr, make_t, model_t, cab_style, bed_label)
                            if k not in seen_tm_keys:
                                seen_tm_keys.add(k)
                                truck_models.append({
                                    "year":              yr,
                                    "make":              make_t,
                                    "model":             model_t,
                                    "trim":              "",
                                    "cab_style":         cab_style or "",
                                    "bed_length_label":  bed_label,
                                    "platform_id":       platform_id,
                                    "vin_decodable_trim":"partial",
                                    "vin_decodable_bed": "partial",
                                    "notes":             "",
                                    "source_urls":       SOURCE_URL,
                                })

                    # ── topper_fitments ────────────────────────────────────
                    for col_idx, series_name in series_cols.items():
                        if col_idx >= len(row):
                            continue
                        cell_val = row[col_idx]
                        if cell_val is None or str(cell_val).strip() == '':
                            continue
                        fits = parse_cell(str(cell_val))
                        for wrap_type, fit_type, extra_note in fits:
                            fitments.append({
                                "topper_brand":               "ATC",
                                "topper_model_series":        series_name,
                                "topper_production_year_start": "",
                                "topper_production_year_end":   "",
                                "fits_platform_id":           platform_id,
                                "confidence":                 100 if fit_type == "OEM" else
                                                              70  if fit_type == "universal" else
                                                              50  if fit_type == "future_release" else 80,
                                "fit_type":                   fit_type,
                                "wrap_type":                  wrap_type,
                                "fit_notes":                  extra_note,
                                "mounting_clamp_type":        "",
                                "required_modifications":     "",
                                "source_urls":                SOURCE_URL,
                                "verified_by":                "manufacturer",
                                "source_effective_date":      EFFECTIVE_DATE,
                                "has_custom_fit":             "",
                                "has_skirted_sides":          "",
                                "door_type":                  "",
                                "clamp_type_required":        "",
                                "bed_size_class":             "",
                                "model_id_alias":             "",
                                "camera_compatible":          "",
                            })

    # ── Write CSVs ────────────────────────────────────────────────────────────
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    plat_path = OUT_DIR / "atc_2022-04_bed_platforms.csv"
    with open(plat_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=PLATFORM_FIELDS)
        w.writeheader()
        w.writerows(platforms.values())
    print(f"bed_platforms       : {len(platforms)} rows → {plat_path}")

    tm_path = OUT_DIR / "atc_2022-04_truck_models.csv"
    with open(tm_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=TRUCK_MODEL_FIELDS)
        w.writeheader()
        w.writerows(truck_models)
    print(f"truck_models        : {len(truck_models)} rows → {tm_path}")

    fit_path = OUT_DIR / "atc_2022-04_topper_fitments.csv"
    with open(fit_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FITMENT_FIELDS)
        w.writeheader()
        w.writerows(fitments)
    print(f"topper_fitments     : {len(fitments)} rows → {fit_path}")

    print(f"\nSkipped garbage rows (col-0 collapse): {skipped_garbage}")
    print(f"Skipped no-year rows                 : {skipped_no_year}")
    print("\nDone. Review data/parsed/ before loading.")


if __name__ == "__main__":
    main()
