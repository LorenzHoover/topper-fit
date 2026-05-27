#!/usr/bin/env python3
"""
Parse SnugPro fitment guide PDF (March 2025) into seed CSVs.

SnugPro uses Unicode symbol characters for availability:
   = Custom fit (fully contoured) → confidence 100
   = Standard fit → confidence 90
   = Contoured fit → confidence 95
   = Future application → confidence 50
  'Non custom fit' = non_custom fit_type → confidence 70

Product lines (one fitment row per series per platform):
  XV          — Fiberglass Commercial series (col 5)
  UT PRO      — Aluminum Truck Caps series (col 6)
  Camera variants flagged via -C suffix in any availability cell.
  Wrap-around variant flagged via -W suffix.

SnugPro model IDs (e.g. '66GSO19') are saved to manufacturer_platform_codes.

Run from repo root:
  python3 scripts/parse_snugpro_pdf.py
"""

import csv
import re
from pathlib import Path

import pdfplumber

PDF_PATH       = Path("data/sources/snugpro_2025-03-07.pdf")
OUT_DIR        = Path("data/parsed/snugpro")
SOURCE_URL     = "data/sources/snugpro_2025-03-07.pdf"
EFFECTIVE_DATE = "2025-03-07"
CURRENT_YEAR   = 2025

# ── Symbol → (fit_type, base_confidence) ─────────────────────────────────────

SYMBOL_FITS = {
    '': ('OEM', 100),
    '': ('OEM', 90),
    '': ('OEM', 95),
    '': ('future_release', 50),
}

# ── Section header → (make, model_hint or None) ───────────────────────────────
# model_hint overrides truck-name extraction when it's unambiguous

SECTION_MAP = {
    'CHEVY':              ('Chevrolet', None),
    'GMC':                ('GMC', None),
    'CHEVY / GMC MINI':   ('Chevrolet', None),  # Colorado / Canyon handled via truck name
    'DODGE RAM':          ('Ram', None),
    'JEEP':               ('Jeep', None),
    'FORD F-150':         ('Ford', 'F-150'),
    'FORD RANGER':        ('Ford', 'Ranger'),
    'FORD MAVERICK':      ('Ford', 'Maverick'),
    'FORD BRANDED MAVERIC': None,               # Special format — skip
    'TOYOTA TUNDRA':      ('Toyota', 'Tundra'),
    'NISSAN MINI':        ('Nissan', None),
}


# ── Year / make / model helpers ───────────────────────────────────────────────

def _two_digit_year(s):
    y = int(s)
    return (1900 + y) if y > 25 else (2000 + y)


def parse_year_range(year_str):
    s = re.sub(r'[*\s]', '', str(year_str)).strip()
    if not s:
        return None, None
    if s.endswith('+'):
        base = re.sub(r'[^0-9]', '', s[:-1])
        y = int(base) if len(base) == 4 else _two_digit_year(base)
        return y, None
    if '-' in s:
        left, right = s.split('-', 1)
        left  = re.sub(r'[^0-9]', '', left)
        right = re.sub(r'[^0-9]', '', right)
        if not left or not right:
            return None, None
        start = int(left)  if len(left)  == 4 else _two_digit_year(left)
        end   = int(right) if len(right) == 4 else _two_digit_year(right)
        return start, end
    s = re.sub(r'[^0-9]', '', s)
    if not s:
        return None, None
    try:
        y = int(s) if len(s) == 4 else _two_digit_year(s)
        return y, y
    except ValueError:
        return None, None


def extract_model(truck_name, section_make, model_hint):
    """Derive model string from truck_name; use model_hint only as a fallback."""
    t = truck_name.lower()
    # Chevy / GMC
    if 'silverado ev' in t:         return 'Silverado EV'
    if 'silverado hd' in t or 'silverado 2500' in t or 'silverado 3500' in t:
        return 'Silverado 2500'
    if 'silverado dually' in t:     return 'Silverado 2500'
    if 'silverado' in t:            return 'Silverado 1500'
    if 'sierra hd' in t or 'sierra 2500' in t:  return 'Sierra 2500'
    if 'sierra dually' in t:        return 'Sierra 2500'
    if 'sierra' in t:               return 'Sierra 1500'
    if 'colorado' in t and 'canyon' in t:  return 'Colorado'  # shared; Canyon added via shared logic
    if 'colorado' in t:             return 'Colorado'
    if 'canyon' in t:               return 'Canyon'
    # Ram
    if 'ram 2500' in t or 'ram 3500' in t:   return '2500'
    if 'ram 1500' in t:             return '1500'
    if 't-300' in t:                return 'T-300'
    if 'dakota' in t:               return 'Dakota'
    # Jeep
    if 'gladiator' in t:            return 'Gladiator'
    # Ford
    if 'raptor' in t and 'ranger' in t:  return 'Ranger'
    if 'raptor' in t:               return 'F-150'
    if 'f-150' in t or 'f150' in t:  return 'F-150'
    if 'superduty' in t or 'super duty' in t or 'superduty' in t:  return 'F-250'
    if 'ranger' in t:               return 'Ranger'
    if 'maverick' in t:             return 'Maverick'
    # Toyota
    if 'tundra' in t:               return 'Tundra'
    if 'tacoma' in t:               return 'Tacoma'
    # Nissan
    if 'frontier' in t or 'd40' in t:  return 'Frontier'
    if 'titan' in t:                return 'Titan'
    # Fall back to section hint, then truck name prefix
    if model_hint:
        return model_hint
    return truck_name.split('(')[0].strip()[:20]


def is_shared_colorado_canyon(truck_name):
    return bool(re.search(r'colorado.*canyon|canyon.*colorado|colorado/canyon|chev.*gmc.*mini',
                          truck_name, re.I))


def extract_cab_style(cab_str):
    """Return the first cab style when multiple are listed (e.g. 'XC/DC' → 'Extended Cab')."""
    c = cab_str.strip().upper()
    first = c.split('/')[0].strip()
    mapping = {
        'RC':    'Regular Cab',
        'DC':    'Double Cab',
        'XC':    'Extended Cab',
        'CREW':  'Crew Cab',
    }
    return mapping.get(first) or (mapping.get(c))


MAKE_CODES  = {'Chevrolet':'CHEV','GMC':'GMC','Ford':'FORD','Ram':'RAM',
               'Dodge':'DDG','Toyota':'TOY','Nissan':'NIS','Jeep':'JEEP'}
MODEL_CODES = {
    'Silverado 1500':'S15','Silverado 2500':'S25','Silverado EV':'SEV',
    'Sierra 1500':'SRA','Sierra 2500':'SRA25',
    'F-150':'F150','F-250':'F250','Ranger':'RNG','Maverick':'MAV',
    '1500':'R15','2500':'R25','Dakota':'DAK','T-300':'T300',
    'Tundra':'TUN','Tacoma':'TAC',
    'Colorado':'COL','Canyon':'CAN',
    'Titan':'TTN','Frontier':'FRONT',
    'Gladiator':'GLAD',
}
CAB_CODES = {
    'Regular Cab':'RC','Double Cab':'DC','Extended Cab':'XC',
    'Crew Cab':'CC','CrewMax':'CM','SuperCrew':'SC',
}


def make_platform_id(make, model, year_start, year_end, cab_style, bed_label):
    m  = MAKE_CODES.get(make, make[:4].upper())
    mo = MODEL_CODES.get(model, re.sub(r'[^A-Z0-9]', '', model.upper())[:6])
    yr = (f"{str(year_start)[-2:]}P" if year_end is None
          else str(year_start)[-2:] if year_start == year_end
          else f"{str(year_start)[-2:]}-{str(year_end)[-2:]}")
    cab = CAB_CODES.get(cab_style, '') if cab_style else ''
    bed_code = re.sub(r'[^A-Z0-9]', '', (bed_label or '').upper())[:6]
    parts = [p for p in [m, mo, yr, cab, bed_code] if p]
    return '-'.join(parts)


# ── Availability cell parser ──────────────────────────────────────────────────

def parse_availability(cell):
    """
    Returns None (no fit) or dict with keys:
      fit_type, confidence, camera_compatible, wrap_type, fit_notes
    """
    raw = str(cell or '').strip()
    if not raw:
        return None

    # Non custom fit — text string
    if 'non custom fit' in raw.lower():
        return {'fit_type': 'non_custom', 'confidence': 70,
                'camera_compatible': False, 'wrap_type': None, 'fit_notes': 'Non custom fit'}

    # Extract suffixes before looking up symbol
    camera = '-C' in raw or raw.endswith('C') and len(raw) > 1
    wrap   = '-W' in raw
    notes  = ''
    if '**' in raw:
        notes = 'Requires attaching kit'
    if "'" in raw or '"' in raw:   # size note like 20" Only
        notes = raw

    # Find the base symbol character
    for sym, (fit_type, conf) in SYMBOL_FITS.items():
        if sym in raw:
            return {
                'fit_type':         fit_type,
                'confidence':       conf,
                'camera_compatible': camera,
                'wrap_type':        'W' if wrap else None,
                'fit_notes':        notes,
            }

    return None   # unrecognised or empty


# ── Page/table filters ────────────────────────────────────────────────────────

def is_header_or_legend_row(row):
    """
    True if this row is part of the repeated legend/header block.
    Checked per-row so tables that mix header rows + data rows still get parsed.
    """
    if not row:
        return True
    cells = [str(c or '') for c in row]
    flat  = ''.join(cells)
    c0    = cells[0]
    # Empty rows
    if not flat.strip():
        return True
    # Legend rows contain "= Custom fit", "= Future", "= Wrap-around", etc.
    legend_phrases = (
        'Custom fit shell', 'Future appl', 'Wrap-around rail',
        'No boot avail', 'Rotary latch', 'Shell contours',
        '60/40 Rear', 'DL = LB', 'DS = SB',
    )
    if any(p in flat for p in legend_phrases):
        return True
    # Page title row: "2025 MODEL AVAILABILITY..."
    if '2025 MO' in c0 or 'FIBERGLASS' in c0.upper() or 'ASS COMMERCIAL' in flat:
        return True
    # Sub-header column labels row
    if 'TRUCK MODEL' in c0.upper() and 'MODEL ID' in c0.upper():
        return True
    # Availability key headers ("XV", "UT PRO Aluminum") sometimes appear alone
    if c0.strip() == '' and 'XV' in flat and 'UT PRO' in flat:
        return True
    return False


def is_section_header_row(row):
    """True if row[0] has text and row[1] and row[2] are both empty."""
    if not row or len(row) < 3:
        return False
    c0 = str(row[0] or '').strip()
    c1 = str(row[1] or '').strip()
    c2 = str(row[2] or '').strip()
    return bool(c0) and not c1 and not c2


def has_year(row):
    """True if col 2 looks like a year range."""
    if len(row) < 3:
        return False
    v = str(row[2] or '').strip()
    return bool(re.search(r'\d{2}', v))


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
MFR_CODE_FIELDS = [
    "platform_id","manufacturer","manufacturer_code",
    "code_type","source_pdf","notes",
]


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    platforms    = {}
    truck_models = []
    fitments     = []
    mfr_codes    = []
    seen_tm_keys = set()

    current_make  = None
    model_hint    = None
    skipped       = 0

    with pdfplumber.open(PDF_PATH) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                if not table:
                    continue

                for row in table:
                    if is_header_or_legend_row(row):
                        continue

                    # ── Section header ─────────────────────────────────────
                    if is_section_header_row(row):
                        key = str(row[0] or '').strip().upper()
                        ctx = SECTION_MAP.get(key)
                        if ctx is None and key in SECTION_MAP:
                            # Explicitly skipped section (value=None)
                            current_make = None
                            model_hint   = None
                        elif ctx:
                            current_make = ctx[0]
                            model_hint   = ctx[1]
                        else:
                            # Unknown section header — try to infer
                            if 'FORD' in key:
                                current_make = 'Ford'
                            elif 'TOYOTA' in key or 'TACOMA' in key:
                                current_make = 'Toyota'
                            elif 'NISSAN' in key:
                                current_make = 'Nissan'
                            model_hint = None
                        continue

                    # ── Require a year in col 2 ────────────────────────────
                    if not has_year(row) or current_make is None:
                        continue

                    truck_name = str(row[0] or '').strip()
                    model_id   = str(row[1] or '').strip().rstrip('*')  # strip trailing *
                    year_str   = str(row[2] or '').strip()
                    cab_raw    = str(row[3] or '').strip() if len(row) > 3 else ''
                    bed_raw    = str(row[4] or '').strip() if len(row) > 4 else ''

                    year_start, year_end = parse_year_range(year_str)
                    if year_start is None:
                        skipped += 1
                        continue

                    # Skip Maverick "FORD BRANDED" format rows (different column layout)
                    if 'MAVERICK' in truck_name.upper() and 'SKU' in str(row):
                        continue

                    model     = extract_model(truck_name, current_make, model_hint)
                    cab_style = extract_cab_style(cab_raw)

                    bed_label_map = {
                        'SB': 'Short Bed', 'LB': 'Long Bed',
                        'V-BED': 'V-Bed', 'DS': 'Dually SB', 'DL': 'Dually LB',
                        'VB': 'V-Bed',
                    }
                    bed_label = bed_label_map.get(bed_raw.upper(), bed_raw or None)

                    # Determine all makes for shared platforms
                    if is_shared_colorado_canyon(truck_name):
                        make_model_pairs = [('Chevrolet', 'Colorado'), ('GMC', 'Canyon')]
                    else:
                        make_model_pairs = [(current_make, model)]

                    # Use first pair for the canonical platform
                    primary_make, primary_model = make_model_pairs[0]

                    platform_id = make_platform_id(
                        primary_make, primary_model,
                        year_start, year_end, cab_style, bed_label
                    )

                    # Deduplicate with numeric suffix
                    base_pid = platform_id
                    suffix   = 2
                    while platform_id in platforms and platforms[platform_id].get('_sig') != (
                            primary_make, primary_model, year_start, year_end, cab_raw, bed_raw):
                        platform_id = f"{base_pid}-{suffix}"
                        suffix += 1

                    nickname = f"{truck_name} ({year_start}–{year_end or 'present'})"

                    if platform_id not in platforms:
                        platforms[platform_id] = {
                            '_sig': (primary_make, primary_model, year_start, year_end, cab_raw, bed_raw),
                            'platform_id':           platform_id,
                            'nickname':              nickname,
                            'make':                  primary_make,
                            'model_family':          primary_model,
                            'generation':            '',
                            'production_year_start': year_start,
                            'production_year_end':   year_end or '',
                            'cab_style':             cab_style or cab_raw,
                            'bed_length_class':      '',
                            'bed_length_floor_inches': '',
                            'bed_length_rail_inches':  '',
                            'bed_width_at_rail_inches':'',
                            'bed_width_outer_inches':  '',
                            'bed_depth_inches':        '',
                            'rail_profile_shape':      '',
                            'rail_cross_section_width_inches':  '',
                            'rail_cross_section_height_inches': '',
                            'stake_pockets_present':   '',
                            'stake_pocket_count_per_side': '',
                            'stake_pocket_length_inches':  '',
                            'stake_pocket_width_inches':   '',
                            'utility_track_system':    'none',
                            'cab_back_generation':     '',
                            'cab_camera_present':      '',
                            'tailgate_variant':        'Standard',
                            'notes':                   '',
                            'source_urls':             SOURCE_URL,
                        }

                    # ── truck_models ───────────────────────────────────────
                    end_yr = year_end or CURRENT_YEAR
                    for mk, mo in make_model_pairs:
                        for yr in range(year_start, end_yr + 1):
                            k = (yr, mk, mo, cab_style or cab_raw, bed_label)
                            if k not in seen_tm_keys:
                                seen_tm_keys.add(k)
                                truck_models.append({
                                    'year':              yr,
                                    'make':              mk,
                                    'model':             mo,
                                    'trim':              '',
                                    'cab_style':         cab_style or cab_raw,
                                    'bed_length_label':  bed_label or '',
                                    'platform_id':       platform_id,
                                    'vin_decodable_trim':'partial',
                                    'vin_decodable_bed': 'partial',
                                    'notes':             '',
                                    'source_urls':       SOURCE_URL,
                                })

                    # ── SnugPro model ID → manufacturer_platform_codes ─────
                    if model_id:
                        mfr_codes.append({
                            'platform_id':       platform_id,
                            'manufacturer':      'SnugPro',
                            'manufacturer_code': model_id,
                            'code_type':         'model_id',
                            'source_pdf':        SOURCE_URL,
                            'notes':             '',
                        })

                    # ── topper_fitments (cols 5 and 6, plus col 7 camera) ──
                    # XV (col 5) = fiberglass → wraps over rails (W)
                    # UT PRO (col 6) = aluminum → inside rails (X)
                    series_cols = {5: 'XV', 6: 'UT PRO'}
                    series_default_wrap = {'XV': 'W', 'UT PRO': 'X'}
                    for col_idx, series in series_cols.items():
                        cell = row[col_idx] if len(row) > col_idx else None
                        avail = parse_availability(cell)
                        if avail is None:
                            continue

                        # Check col 7 for camera variant of this same series
                        cam_col7 = parse_availability(row[7] if len(row) > 7 else None)
                        if cam_col7 and cam_col7.get('camera_compatible'):
                            avail['camera_compatible'] = True

                        fitments.append({
                            'topper_brand':                'SnugPro',
                            'topper_model_series':         series,
                            'topper_production_year_start':'',
                            'topper_production_year_end':  '',
                            'fits_platform_id':            platform_id,
                            'confidence':                  avail['confidence'],
                            'fit_type':                    avail['fit_type'],
                            'wrap_type':                   avail['wrap_type'] or series_default_wrap.get(series, ''),
                            'fit_notes':                   avail['fit_notes'],
                            'mounting_clamp_type':         '',
                            'required_modifications':      '',
                            'source_urls':                 SOURCE_URL,
                            'verified_by':                 'manufacturer',
                            'source_effective_date':       EFFECTIVE_DATE,
                            'has_custom_fit':              '',
                            'has_skirted_sides':           '',
                            'door_type':                   '',
                            'clamp_type_required':         '',
                            'bed_size_class':              '',
                            'model_id_alias':              '',
                            'camera_compatible':           avail['camera_compatible'],
                        })

                    # Col 7 standalone camera fit (when cols 5+6 are empty)
                    col5_empty = parse_availability(row[5] if len(row) > 5 else None) is None
                    col6_empty = parse_availability(row[6] if len(row) > 6 else None) is None
                    if col5_empty and col6_empty and len(row) > 7:
                        avail7 = parse_availability(row[7])
                        if avail7:
                            fitments.append({
                                'topper_brand':                'SnugPro',
                                'topper_model_series':         'UT PRO',
                                'topper_production_year_start':'',
                                'topper_production_year_end':  '',
                                'fits_platform_id':            platform_id,
                                'confidence':                  avail7['confidence'],
                                'fit_type':                    avail7['fit_type'],
                                'wrap_type':                   avail7['wrap_type'] or 'X',
                                'fit_notes':                   avail7['fit_notes'],
                                'mounting_clamp_type':         '',
                                'required_modifications':      '',
                                'source_urls':                 SOURCE_URL,
                                'verified_by':                 'manufacturer',
                                'source_effective_date':       EFFECTIVE_DATE,
                                'has_custom_fit':              '',
                                'has_skirted_sides':           '',
                                'door_type':                   '',
                                'clamp_type_required':         '',
                                'bed_size_class':              '',
                                'model_id_alias':              '',
                                'camera_compatible':           avail7.get('camera_compatible', False),
                            })

    # ── Write CSVs ────────────────────────────────────────────────────────────
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Strip internal _sig key before writing
    plat_rows = [{k: v for k, v in p.items() if k != '_sig'} for p in platforms.values()]

    plat_path = OUT_DIR / "snugpro_2025-03_bed_platforms.csv"
    with open(plat_path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=PLATFORM_FIELDS)
        w.writeheader(); w.writerows(plat_rows)
    print(f"bed_platforms           : {len(plat_rows)} rows → {plat_path}")

    tm_path = OUT_DIR / "snugpro_2025-03_truck_models.csv"
    with open(tm_path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=TRUCK_MODEL_FIELDS)
        w.writeheader(); w.writerows(truck_models)
    print(f"truck_models            : {len(truck_models)} rows → {tm_path}")

    fit_path = OUT_DIR / "snugpro_2025-03_topper_fitments.csv"
    with open(fit_path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=FITMENT_FIELDS)
        w.writeheader(); w.writerows(fitments)
    print(f"topper_fitments         : {len(fitments)} rows → {fit_path}")

    mfr_path = OUT_DIR / "snugpro_2025-03_manufacturer_platform_codes.csv"
    with open(mfr_path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=MFR_CODE_FIELDS)
        w.writeheader(); w.writerows(mfr_codes)
    print(f"manufacturer_platform_codes: {len(mfr_codes)} rows → {mfr_path}")

    print(f"\nSkipped (bad year):     {skipped}")
    print("\nDone. Review data/parsed/ before loading.")


if __name__ == '__main__':
    main()
