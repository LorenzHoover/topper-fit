#!/usr/bin/env python3
"""
Parse LEER East PDF fitment chart.

Primary source: leer_east_2025-01-24.pdf
Outputs to:    data/parsed/leer/

Column layout (standard 18-col data tables):
  Col 0: Year range   Col 1: LEER Model ID   Col 2: Clamp   Col 3: Bed size class
  Cols 4–17: 14 series (100XQ … 550)

Some tables have 1–2 extra leading columns for truck-name context (19 or 20 cols).
The series always occupy the last 14 columns.

Fit cell values:
  X / X SS / X SS 1 2 / XSS / X SS F …  → actual fit — parse flags
  64DR09 / 62TCDC16 / …                  → alias to another LEER model
  empty                                  → no fit
  (self-alias where cell == own model_id) → skip (ordering-code row, redundant)
"""

import csv
import re
import sys
from pathlib import Path

try:
    import pdfplumber
except ImportError:
    print("ERROR: pdfplumber not installed. Run: pip3 install pdfplumber")
    sys.exit(1)

# ── Config ────────────────────────────────────────────────────────────────────

PDF_PATH       = Path("data/sources/leer_east_2025-01-24.pdf")
OUT_DIR        = Path("data/parsed/leer")
EFFECTIVE_DATE = "2025-01-24"

# The 14 series columns, in left-to-right order as they appear in the PDF.
SERIES = [
    "100XQ", "100XQ_SPORT", "100XL", "100XR", "100R",
    "Legend", "100S", "180", "180XL", "180XR",
    "122", "750_SPORT", "700", "550",
]
N_SERIES = len(SERIES)  # 14

# ── Make/model lookup (most-specific prefix first) ────────────────────────────

# After stripping leading digits and trailing modifiers from a model_id,
# match against these prefixes.
MODEL_ID_PREFIXES = [
    ("TCDC", "Toyota",    "Tacoma"),
    ("TC",   "Toyota",    "Tacoma"),
    ("TT",   "Toyota",    "Tundra"),
    ("NF",   "Nissan",    "Frontier"),
    ("NT",   "Nissan",    "Titan"),
    ("HR",   "Honda",     "Ridgeline"),
    ("GMTW", "Chevrolet", "Silverado"),
    ("GSOCC","Chevrolet", "Silverado"),
    ("GSACC","Chevrolet", "Silverado"),
    ("GSOCC","Chevrolet", "Silverado"),
    ("GMT",  "Chevrolet", "Silverado"),
    ("GSO",  "Chevrolet", "Silverado"),
    ("GSA",  "Chevrolet", "Silverado"),
    ("GSD",  "Chevrolet", "Silverado"),
    ("GS",   "Chevrolet", "Silverado"),
    ("GO",   "GMC",       "Sierra"),
    ("GA",   "GMC",       "Sierra"),
    ("GN",   "GMC",       "Canyon"),
    ("GL",   "Chevrolet", "Colorado"),
    ("GC",   "Chevrolet", "Colorado"),
    ("AFR",  "Ford",      "Ranger"),
    ("FST",  "Ford",      "F-150"),
    ("FF",   "Ford",      "F-150"),
    ("FS",   "Ford",      "F-250 Super Duty"),
    ("FM",   "Ford",      "Maverick"),
    ("FR",   "Ford",      "Ranger"),
    ("DR",   "Ram",       "1500"),
    ("DK",   "Dodge",     "Dakota"),
    ("DD",   "Dodge",     "Dakota"),
    ("JG",   "Jeep",      "Gladiator"),
    ("SCC",  "Chevrolet", "S-10"),
    ("SE",   "Suzuki",    "Equator"),
    ("S",    "Chevrolet", "S-10"),
    ("R",    "Ford",      "Ranger"),
    ("IH",   "Isuzu",     "Hombre"),
]


def model_id_to_make_model(raw_id):
    """Return (make, model) by matching model_id prefix, or (None, None)."""
    # Strip leading digits, then strip at first dash/star/hash/caret/space
    mid = re.sub(r"^\d+", "", raw_id.upper())
    mid = re.split(r"[-\*#\^ ]", mid)[0]
    for prefix, make, model in MODEL_ID_PREFIXES:
        if mid.startswith(prefix):
            return make, model
    return None, None


def cab_from_model_id(raw_id):
    """Guess cab style from known suffixes embedded in model_id."""
    u = raw_id.upper()
    if "DCDC" in u or "DC" in u:
        return "Double Cab"
    if "QC" in u:
        return "Quad Cab"
    if "CC" in u:
        return "Crew Cab"
    return None


def bed_length_from_model_id(raw_id, bed_size_class):
    """Estimate bed length in inches from leading digits of model_id."""
    fallback = {
        "SF": 66.0, "LF": 79.0,
        "SC": 61.0, "SS": 69.0,
        "LS": 80.0, "FR": 61.0,
    }
    m = re.match(r"^(\d+)", raw_id)
    if m:
        n = int(m.group(1))
        if 40 <= n <= 100:
            return float(n)
    return fallback.get(bed_size_class or "", None)


def clean_model_id(raw):
    """Remove trailing annotation characters (* # ^ etc.)."""
    return re.sub(r"[\*#\^]+$", "", raw.strip()).strip()


# ── Year-range parsing ────────────────────────────────────────────────────────

def parse_year_range(s):
    """Return (year_start, year_end) integers, or (None, None)."""
    s = re.sub(r"[\*#\^]+", "", str(s or "")).strip()
    # e.g. '2021-2025', '2021 - 2025', '2024 -2025'
    m = re.match(r"(\d{4})\s*[-–]\s*(\d{4})", s)
    if m:
        return int(m.group(1)), int(m.group(2))
    # e.g. '2024+' or '2024 +'
    m = re.match(r"(\d{4})\s*\+", s)
    if m:
        return int(m.group(1)), None
    # Single year
    m = re.match(r"^(\d{4})$", s)
    if m:
        y = int(m.group(1))
        return y, y
    return None, None


# ── Fit-code parsing ──────────────────────────────────────────────────────────

def is_fit_code(cell):
    """True if cell is an X-type fit code (not an alias model_id)."""
    c = str(cell or "").strip().lstrip("<").strip().upper()
    return c.startswith("X")


def is_alias_code(cell):
    """True if cell looks like a LEER model_id alias (not an X code)."""
    c = str(cell or "").strip().upper()
    if not c:
        return False
    if c.startswith("X"):
        return False
    # Must start with digit or alpha code that matches model_id pattern
    return bool(re.match(r"^[\dA-Z]", c))


def parse_fit_flags(cell):
    """Parse 'X SS 1 2 F' → (has_skirted_sides, door_type, frame_note)."""
    c = str(cell or "").strip().upper().replace(" ", "")
    has_ss   = "SS" in c
    has_1    = "1" in c
    has_2    = "2" in c
    has_f    = bool(re.search(r"(?<![A-Z])F(?![A-Z])", c))  # standalone F
    if has_1 and has_2:
        door_type = "windoor_and_option2"
    elif has_1:
        door_type = "windoor"
    else:
        door_type = None
    return has_ss, door_type, ("F" if has_f else None)


# ── Table filtering ───────────────────────────────────────────────────────────

LEGEND_PHRASES = (
    "Level",   # legend key rows
    "Windoor", "SF =", "LF =", "SC =", "Requires Attaching",
)


def is_data_table(table):
    """Skip legend/narrow tables; keep data tables with >= 4 columns."""
    if not table:
        return False
    if len(table[0]) < 4:
        return False
    first_row_text = " ".join(str(c or "") for c in table[0])
    for phrase in LEGEND_PHRASES:
        if phrase in first_row_text:
            return False
    return True


def detect_info_offset(row):
    """Find the column index where the year range starts."""
    for i, cell in enumerate(row):
        if cell and re.match(r"\d{4}", str(cell).strip()):
            return i
    return 0


# ── Platform + row tracking ───────────────────────────────────────────────────

def platform_id_from_model_id(mid):
    clean = re.sub(r"[^a-z0-9]", "_", mid.lower())
    return f"leer_{clean}"


def make_nickname(make, model, model_id, year_start, year_end):
    m = re.match(r"^(\d+)", model_id)
    bed = f" {m.group(1)}\"" if m and 40 <= int(m.group(1)) <= 100 else ""
    yr  = f"{year_start}+" if not year_end else f"{year_start}–{year_end}"
    return f"{make} {model}{bed} ({yr})"


# ── Main parsing logic ────────────────────────────────────────────────────────

def parse_leer(pdf_path):
    platforms = {}  # platform_id → dict
    fitments  = []
    mfr_codes = {}  # (platform_id, manufacturer_code) → True  (dedup set)

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                if not is_data_table(table):
                    continue
                _process_table(table, platforms, fitments, mfr_codes)

    return platforms, fitments, mfr_codes


def _process_table(table, platforms, fitments, mfr_codes):
    for row in table:
        offset = detect_info_offset(row)

        # Need at least offset + 4 info cols + at least 1 series col
        if offset + 4 >= len(row):
            continue

        year_str = str(row[offset]     or "").strip()
        raw_mid  = str(row[offset + 1] or "").strip()
        clamp    = str(row[offset + 2] or "").strip()
        bed_size = str(row[offset + 3] or "").strip()

        if not year_str or not raw_mid:
            continue

        year_start, year_end = parse_year_range(year_str)
        if year_start is None:
            continue

        # Skip "No Custom Fit Models" and similar notes
        if "no custom fit" in raw_mid.lower():
            continue

        model_id = clean_model_id(raw_mid)
        if not model_id:
            continue

        make, model = model_id_to_make_model(model_id)
        if not make:
            continue

        # Series cells: always the last N_SERIES columns
        series_start = len(row) - N_SERIES
        if series_start < 0:
            series_start = offset + 4
        series_cells = [str(c or "").strip() for c in row[series_start:series_start + N_SERIES]]
        while len(series_cells) < N_SERIES:
            series_cells.append("")

        pid = platform_id_from_model_id(model_id)

        # Register platform (first occurrence wins; expand year range on repeat)
        if pid not in platforms:
            bed_len  = bed_length_from_model_id(model_id, bed_size)
            cab_s    = cab_from_model_id(model_id)
            nickname = make_nickname(make, model, model_id, year_start, year_end)
            platforms[pid] = {
                "platform_id":              pid,
                "make":                     make,
                "model_family":             model,
                "cab_style":                cab_s,
                "nickname":                 nickname,
                "bed_length_floor_inches":  bed_len,
                "bed_size_class":           bed_size or None,
                "clamp_type":               clamp or None,
                "production_year_start":    year_start,
                "production_year_end":      year_end,
                "stake_pockets_present":    None,
                "cab_camera_present":       None,
                "source_effective_date":    EFFECTIVE_DATE,
            }
        else:
            p = platforms[pid]
            if year_start < p["production_year_start"]:
                p["production_year_start"] = year_start
            if year_end is None:
                p["production_year_end"] = None
            elif p["production_year_end"] is not None and year_end > p["production_year_end"]:
                p["production_year_end"] = year_end

        # Canonical mfr code for this platform
        mfr_key = (pid, model_id)
        if mfr_key not in mfr_codes:
            mfr_codes[mfr_key] = {
                "platform_id":        pid,
                "manufacturer":       "LEER",
                "manufacturer_code":  model_id,
                "source_effective_date": EFFECTIVE_DATE,
            }

        # Process series cells — each cell independently:
        # X-type → fit code; other alphanumeric (not self-alias) → alias code; empty → skip
        for i, cell in enumerate(series_cells):
            if not cell:
                continue
            series_name = SERIES[i]

            if is_fit_code(cell):
                has_ss, door_type, frame_note = parse_fit_flags(cell)
                fit_notes = ("Frame mount required" if frame_note else None)
                fitments.append({
                    "fits_platform_id":            pid,
                    "topper_brand":                "LEER",
                    "topper_model_series":         series_name,
                    "fit_type":                    "OEM",
                    "wrap_type":                   "X",
                    "has_skirted_sides":           has_ss,
                    "door_type":                   door_type,
                    "clamp_type_required":         clamp or None,
                    "bed_size_class":              bed_size or None,
                    "camera_compatible":           None,
                    "has_custom_fit":              True,
                    "model_id_alias":              None,
                    "fit_notes":                   fit_notes,
                    "confidence":                  100,
                    "verified_by":                 "manufacturer",
                    "source_effective_date":       EFFECTIVE_DATE,
                    "topper_production_year_start": None,
                    "topper_production_year_end":  None,
                })

            elif is_alias_code(cell) and cell.upper() != model_id.upper():
                # Cross-alias to a different LEER model (e.g. older shell also fits)
                mk = (pid, cell)
                if mk not in mfr_codes:
                    mfr_codes[mk] = {
                        "platform_id":       pid,
                        "manufacturer":      "LEER",
                        "manufacturer_code": cell,
                        "source_effective_date": EFFECTIVE_DATE,
                    }
                fitments.append({
                    "fits_platform_id":            pid,
                    "topper_brand":                "LEER",
                    "topper_model_series":         series_name,
                    "fit_type":                    "aliased",
                    "wrap_type":                   "X",
                    "has_skirted_sides":           None,
                    "door_type":                   None,
                    "clamp_type_required":         clamp or None,
                    "bed_size_class":              bed_size or None,
                    "camera_compatible":           None,
                    "has_custom_fit":              True,
                    "model_id_alias":              cell,
                    "fit_notes":                   None,
                    "confidence":                  80,
                    "verified_by":                 "manufacturer",
                    "source_effective_date":       EFFECTIVE_DATE,
                    "topper_production_year_start": None,
                    "topper_production_year_end":  None,
                })
            # self-aliases (cell == model_id) are intentionally skipped


# ── Truck models expansion ────────────────────────────────────────────────────

def expand_truck_models(platforms):
    """
    For each platform, emit one truck_models row per year in the production range.
    LEER doesn't specify cab style in most tables, so cab_style is left null when
    it can't be determined from the model_id suffix.
    """
    rows = []
    for p in platforms.values():
        make      = p["make"]
        model     = p["model_family"]
        pid       = p["platform_id"]
        cab       = p["cab_style"]
        bed_len   = p["bed_length_floor_inches"]
        bed_label = f'{int(bed_len)}"' if bed_len else (p.get("bed_size_class") or "")
        y_start   = p["production_year_start"]
        y_end     = p["production_year_end"] or 2025

        for year in range(y_start, y_end + 1):
            rows.append({
                "year":             year,
                "make":             make,
                "model":            model,
                "cab_style":        cab,
                "bed_length_label": bed_label,
                "platform_id":      pid,
            })
    return rows


# ── CSV writers ───────────────────────────────────────────────────────────────

PLATFORM_FIELDS = [
    "platform_id", "make", "model_family", "cab_style", "nickname",
    "bed_length_floor_inches", "production_year_start", "production_year_end",
    "stake_pockets_present", "cab_camera_present",
]

TRUCK_FIELDS = ["year", "make", "model", "cab_style", "bed_length_label", "platform_id"]

FITMENT_FIELDS = [
    "fits_platform_id", "topper_brand", "topper_model_series",
    "fit_type", "wrap_type", "has_skirted_sides", "door_type",
    "clamp_type_required", "bed_size_class", "camera_compatible",
    "has_custom_fit", "model_id_alias", "fit_notes",
    "confidence", "verified_by",
    "source_effective_date",
    "topper_production_year_start", "topper_production_year_end",
]

MFR_FIELDS = ["platform_id", "manufacturer", "manufacturer_code", "source_effective_date"]


def write_csv(path, fieldnames, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"  Wrote {len(rows):>5} rows → {path}")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    print(f"Parsing {PDF_PATH} …")
    platforms, fitments, mfr_codes = parse_leer(PDF_PATH)

    truck_models = expand_truck_models(platforms)

    # Dedup fitments: same (platform_id, series, wrap_type, fit_type) → keep highest confidence
    seen = {}
    for f in fitments:
        key = (f["fits_platform_id"], f["topper_model_series"], f["wrap_type"], f["fit_type"])
        if key not in seen or f["confidence"] > seen[key]["confidence"]:
            seen[key] = f
    deduped_fitments = list(seen.values())

    prefix = f"leer_east_2025-01"
    write_csv(OUT_DIR / f"{prefix}_bed_platforms.csv",         PLATFORM_FIELDS,  list(platforms.values()))
    write_csv(OUT_DIR / f"{prefix}_truck_models.csv",          TRUCK_FIELDS,     truck_models)
    write_csv(OUT_DIR / f"{prefix}_topper_fitments.csv",       FITMENT_FIELDS,   deduped_fitments)
    write_csv(OUT_DIR / f"{prefix}_manufacturer_platform_codes.csv", MFR_FIELDS, list(mfr_codes.values()))

    print(f"\nSummary:")
    print(f"  {len(platforms):>5} bed platforms")
    print(f"  {len(truck_models):>5} truck models")
    print(f"  {len(deduped_fitments):>5} topper fitments")
    print(f"  {len(mfr_codes):>5} manufacturer platform codes")

    # Show sample platforms
    print("\nSample platforms:")
    for p in list(platforms.values())[:10]:
        print(f"  {p['platform_id']:30s} {p['make']:12s} {p['model_family']:20s} "
              f"{p['production_year_start']}–{p['production_year_end'] or '?'}")


if __name__ == "__main__":
    main()
