# Data Sources

Each source entry documents: where it came from, when we pulled it, license/attribution, and known quirks.

---

## Ranch/LTA Manufacturing Fitment Guide

| Field | Value |
|-------|-------|
| File | `ranch_fitment_guide.pdf` |
| Effective date | July 2025 |
| Pulled | 2026-05-18 |
| Attribution | Ranch/LTA Manufacturing (ltatopper.com) |
| License | Factual fitment data (Feist v. Rural Telephone — facts not copyrightable). No marketing copy reproduced. |

**Coverage:**
- ~70 truck bed platform configurations
- Makes: Chevrolet, GMC, Ford, Dodge/Ram, Toyota, Nissan, Jeep
- 11 topper model series: Sport Wrap, Legacy, Echo, Sierra/Xtra, WorkForce, Fusion Classic, Fusion, Premier, ICON, Skyline, XD
- Uses W/X/U wrap-type typology

**Known quirks / edge cases documented in source:**
- Ram: round vs. square gas door marks a body-style boundary (affects fitment)
- Dually (DRW) trucks excluded from most fitment rows
- Some series note camera compatibility ("works with camera")
- 3rd brake light camera restrictions on certain cab-back/topper combinations
- "Classic body" overlap rows where gen boundary is ambiguous

**Notable gap:**
- 1st gen Toyota Tundra (2000–2006) is NOT covered. Ranch Tundra coverage starts 2007–2013.
  This is a data point for users: Ranch is not an option for 1st gen Tundra owners.

---

## Personal Measurement — 2003 Toyota Tundra Access Cab 4x4 TRD

| Field | Value |
|-------|-------|
| Source | Owner measurement (lorenzhoover622@gmail.com) |
| Measured | 2026 (pre-session) |
| Platform ID | TUN-1G-AC-SB (pending confirmation) |
| Verified by | `personal_verification` |

**Measurements taken:**
| Dimension | Value | Notes |
|-----------|-------|-------|
| Bed length (floor along side) | 76.5" | Need re-measure along rail top — likely 74–75" |
| Bed width, inner rail | ~61.0" | Approximate |
| Bed width, outer | 69.25" | |
| Bed depth | 21.0" | Rail top to floor |
| Stake pocket opening | 2.25" × 1.75" | |

**Still needed:**
- Rail cross-section width and height
- Stake pocket count per side
- Rail-top bed length (along rail, not floor)

**Role in project:** Primary "personally verified" reference platform; test case for user correction workflow.

---

## Forum Data — tundras.com thread on cross-year fitment

| Field | Value |
|-------|-------|
| Source | https://www.tundras.com/threads/toppers-for-different-model-years.89513/ |
| Pulled | 2026-05-18 |
| Verified by | `forum` + `owner_report` |

**Key findings:**
- 1st gen Tundra Access Cab (AC) and Double Cab (DC) toppers are NOT freely interchangeable despite similar bed dimensions
- Reported consequences of crossing AC/DC: 0.75–2" overhang at cab end, water leaks
- SnugTop customer service confirmed: same topper SKU covers 2001–2006 Tundra AC (suggesting 1999–2000 may differ within the AC class)

**Use in schema:** Supports cross_cab fit_type rows with confidence ~85 and explicit fit_notes about overhang.

---

## Manufacturer Research Queue (not yet acquired)

Priority order for Internet Archive / Wayback Machine research:

| Brand | Priority | Search notes |
|-------|----------|--------------|
| LEER | 1 | Largest volume brand. Try: `site:web.archive.org leertrucks.com fitment` |
| ARE (A.R.E.) | 2 | #2 market share. Try: `site:archive.org "A.R.E." "fitment guide" filetype:pdf` |
| SnugTop | 3 | Strong West Coast / Toyota presence. Try: `snugtop.com/fit-guide` in Wayback |
| ATC | 4 | Aluminum Truck Covers |
| Century / Jason | 5 | Jason Industries successor; need legacy charts for older fitments |

**Useful Google search patterns:**
```
site:archive.org "LEER" "fitment" filetype:pdf
site:web.archive.org leertrucks.com
"application guide" "topper" filetype:pdf site:archive.org
"fit guide" "camper shell" "ARE" site:archive.org
```
