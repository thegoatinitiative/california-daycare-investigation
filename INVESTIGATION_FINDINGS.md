# California Daycare Fraud Investigation Findings

**Analysis Date:** January 22, 2026
**Data Source:** CA Community Care Licensing Division (39,184 facilities)

---

## Executive Summary

Analysis of California childcare facility data reveals patterns consistent with potential fraud, though most flagged facilities appear to be legitimate operations that closed due to normal business reasons or pandemic impacts. However, several concerning patterns warrant further investigation.

### Key Statistics
- **Total Facilities Analyzed:** 39,184
- **COVID-Era Licenses (2020-2022):** 5,363
- **Now Closed:** 1,081 (20.2%)
- **Ultra-Short Operations (<6 months):** 74
- **License Cycling Patterns:** 331 licensees

---

## Finding 1: Known Fraud Case (San Diego)

### UMI Learning Center Fraud Ring
**Status:** PROSECUTED - Defendants convicted in 2023-2024

**Scheme:** Four family members (Mohamed Muriidi Mohamed and relatives) operated UMI Learning Center in San Diego's Rolando neighborhood. They:
1. Falsely enrolled people as "students" at their vocational school
2. Created fake childcare attendance records for non-existent children
3. Split fraudulent childcare subsidy payments with participating parents
4. Parents paid $200 to UMI for fake enrollment documents

**Financial Impact:** $3.7 million stolen through Child Development Associates and YMCA

**Sentences:**
- Mohamed Muriidi Mohamed: 27 months prison + $3.7M restitution
- Osob Abdirazak Omar: 12 months + $298K restitution
- Omar Omar: 90 days + $101K restitution

**Source:** [KPBS](https://www.kpbs.org/news/local/2023/05/02/four-san-diego-county-residents-accused-of-child-care-benefits-fraud)

---

## Finding 2: License Cycling Patterns

### What We Found
**331 licensees** show a pattern of repeatedly closing facilities and immediately reopening with new license numbers. While this is normal for large chains (KinderCare, YMCA), some smaller operators show suspicious patterns.

### NOORI Family Network (Flagged for Review)
- **22 facilities** across El Cajon, Sacramento, San Jose, Elk Grove, Lake Forest
- **9 CLOSED**, 11 LICENSED, 2 PENDING
- Pattern: Close facility → Immediately reopen with new license number at same phone
- Total licensed capacity: 154 children
- Uses 14 different phone numbers

**Example:** NOORI, SHAFIQA in El Cajon
- License #376100835: Licensed 11/16/2021 → Closed 9/1/2023
- License #376101652: Licensed 9/1/2023 → Closed 7/11/2024
- License #376102121: Licensed 7/11/2024 → Currently active

**Interpretation:** Could be legitimate (moving locations) OR cycling to reset inspection history

---

## Finding 3: Geographic Hotspots

### COVID-Era License Hotspots (Highest new licenses 2020-2022)
| ZIP Code | City | New Licenses | Notes |
|----------|------|--------------|-------|
| 93454 | Santa Maria | 36 | Agricultural area |
| 92021 | El Cajon | 35 | Large refugee community |
| 93458 | Santa Maria | 32 | |
| 92020 | El Cajon | 31 | |
| 92105 | San Diego | 31 | |

### Top Cities for COVID-Era Closures
| City | Closed Count |
|------|--------------|
| San Diego | 52 |
| Los Angeles | 36 |
| Sacramento | 35 |
| San Jose | 30 |
| Santa Maria | 25 |

---

## Finding 4: Ultra-Short-Lived Facilities

**74 facilities** opened after 2020 and closed within 6 months. Sample:

| Facility | City | Duration | Capacity |
|----------|------|----------|----------|
| SHAMAL, MURSAL | Sacramento | 0.2 months | 14 |
| SHIM, JUYEON | Irvine | 0.5 months | 14 |
| ESMAIL, HALLA | Elk Grove | 0.7 months | 14 |
| PANTHER HOUSE | Lafayette | 1.5 months | 56 |
| DISCOVERY PRESCHOOL | Santa Cruz | 1.5 months | 40 |

**Note:** Some may be legitimate (failed startups, permit issues), but the pattern is worth investigating.

---

## Finding 5: Highest Risk Facilities (Score 10)

These facilities had multiple red flags: COVID-era license, rapid closure, shared phone/address.

| Facility | Licensee | City | Duration |
|----------|----------|------|----------|
| GIANT STEPS CHILD CARE | G&M CARE, INC. | Long Beach | 15 mo |
| SUPERIOR CHILDREN'S CENTER | Bright Horizons | Sacramento | 19.5 mo |
| LITTLE SUNSHINE LEARNING | LLC | St. Helena | 15.8 mo |
| CARING HEARTS CHILD DEV | LLC | San Bernardino | 15.9 mo |
| HAGGINWOOD ACADEMY | LLC | Sacramento | 11.8 mo |
| TINKER LEARNING CENTER | LLC | Morgan Hill | 4.4 mo |
| BRIGHT FUTURES PRESCHOOL | LLC | Bakersfield | 23.8 mo |

---

## Finding 6: Current Federal Investigation Context

### Trump Administration Action (January 2026)
- HHS froze $10 billion in childcare funding to CA and 4 other states
- Trump alleged California fraud "worse than Minnesota"
- **No specific evidence provided** for California claims
- Inspector General confirmed no public OIG reports on CA fraud

### Minnesota Comparison
- $250 million fraud prosecuted (Feeding Our Future)
- 57 individuals convicted
- California has 1 known prosecution ($3.7M San Diego case)

---

## Limitations of This Analysis

1. **No CACFP Data:** Cannot verify which facilities receive federal food program money
2. **No Inspection Records:** Violation/complaint data requires Public Records Act request
3. **Addresses Hidden:** Family child care home addresses marked "Unavailable" for privacy
4. **No Subsidy Data:** Cannot verify which facilities receive state subsidies

---

## Files Generated

| File | Description |
|------|-------------|
| `PRIORITY_INVESTIGATION_LIST.csv` | 1,159 high-risk facilities |
| `ULTRA_SHORT_LIVED_FACILITIES.csv` | 74 facilities open <6 months |
| `LICENSE_CYCLING_PATTERNS.csv` | 331 licensees with cycling behavior |
| `SUSPICIOUS_LICENSEES.csv` | High closure rate operators |
| `INVESTIGATION_REPORT.html` | Interactive browser report |

---

## Recommendations for Further Investigation

1. **File Public Records Act request** for CACFP participant list
2. **Physical verification** of ultra-short-lived facilities via Google Maps
3. **Cross-reference** NOORI network with subsidy payment records
4. **Contact** San Diego prosecutors for pattern information from UMI case
5. **Analyze** phone number sharing among family child care homes

---

## Conclusion

The data shows patterns that **could** indicate fraud but also could reflect normal business operations, pandemic disruptions, or regulatory compliance issues. The only proven fraud case in California ($3.7M in San Diego) represents a tiny fraction of the program.

The current political claims of "tens of billions" in California fraud are not supported by available evidence. However, the system's reliance on self-reported data creates vulnerabilities that warrant continued oversight.

**Key finding:** The NOORI family network in El Cajon/Sacramento shows the clearest pattern of license cycling that merits further investigation.
