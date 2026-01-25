import requests
import pandas as pd
from datetime import datetime
from urllib.parse import quote
import warnings
warnings.filterwarnings('ignore')

# Official CA Open Data Portal CSV URLs (updated Nov 2025)
DATA_URLS = {
    'child_care_centers': 'https://data.chhs.ca.gov/dataset/46ffcbdf-4874-4cc1-92c2-fb715e3ad014/resource/7aed8063-cea7-4367-8651-c81643164ae0/download/tmpwya01y9s.csv',
    'family_child_care_homes': 'https://data.chhs.ca.gov/dataset/46ffcbdf-4874-4cc1-92c2-fb715e3ad014/resource/4b5cc48d-03b1-4f42-a7d1-b9816903eb2b/download/tmpghf_prqt.csv'
}

# List of all 58 California counties
CA_COUNTIES = [
    'Alameda', 'Alpine', 'Amador', 'Butte', 'Calaveras', 'Colusa', 'Contra Costa', 'Del Norte',
    'El Dorado', 'Fresno', 'Glenn', 'Humboldt', 'Imperial', 'Inyo', 'Kern', 'Kings', 'Lake',
    'Lassen', 'Los Angeles', 'Madera', 'Marin', 'Mariposa', 'Mendocino', 'Merced', 'Modoc',
    'Mono', 'Monterey', 'Napa', 'Nevada', 'Orange', 'Placer', 'Plumas', 'Riverside',
    'Sacramento', 'San Benito', 'San Bernardino', 'San Diego', 'San Francisco', 'San Joaquin',
    'San Luis Obispo', 'San Mateo', 'Santa Barbara', 'Santa Clara', 'Santa Cruz', 'Shasta',
    'Sierra', 'Siskiyou', 'Solano', 'Sonoma', 'Stanislaus', 'Sutter', 'Tehama', 'Trinity',
    'Tulare', 'Tuolumne', 'Ventura', 'Yolo', 'Yuba'
]


def download_facility_data(facility_type, url):
    """Download facility data from CA Open Data Portal."""
    print(f"Downloading {facility_type} data...")
    try:
        response = requests.get(url, timeout=60)
        response.raise_for_status()

        # Save raw data
        filename = f"raw_{facility_type}.csv"
        with open(filename, 'wb') as f:
            f.write(response.content)
        print(f"  Saved raw data to {filename}")

        # Read into DataFrame
        df = pd.read_csv(filename, low_memory=False)
        print(f"  Loaded {len(df)} records")
        return df
    except requests.RequestException as e:
        print(f"  Error downloading {facility_type}: {e}")
        return pd.DataFrame()


def analyze_low_capacity_facilities(capacity_threshold=14, counties=None):
    """
    Analyze childcare facilities for low capacity.

    Args:
        capacity_threshold: Facilities with capacity below this are flagged (default 14)
        counties: List of counties to filter (None = all CA counties)
    """
    all_facilities = []

    for facility_type, url in DATA_URLS.items():
        df = download_facility_data(facility_type, url)
        if df.empty:
            continue

        # Standardize column names (lowercase, strip whitespace)
        df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')

        # Print available columns for debugging
        print(f"\n{facility_type} columns: {list(df.columns)}")

        # Add facility type
        df['facility_type'] = facility_type
        all_facilities.append(df)

    if not all_facilities:
        print("No data downloaded!")
        return pd.DataFrame()

    # Combine all facility types
    combined = pd.concat(all_facilities, ignore_index=True)
    print(f"\nTotal facilities loaded: {len(combined)}")

    # Find capacity column (varies by dataset)
    capacity_col = None
    for col in combined.columns:
        if 'capacity' in col.lower():
            capacity_col = col
            break

    if not capacity_col:
        print("Warning: Could not find capacity column!")
        print("Available columns:", list(combined.columns))
        return combined

    print(f"Using capacity column: {capacity_col}")

    # Find county column
    county_col = None
    for col in combined.columns:
        if 'county' in col.lower():
            county_col = col
            break

    # Find status column
    status_col = None
    for col in combined.columns:
        if 'status' in col.lower() or 'facility_status' in col.lower():
            status_col = col
            break

    # Convert capacity to numeric
    combined[capacity_col] = pd.to_numeric(combined[capacity_col], errors='coerce').fillna(0).astype(int)

    # Filter by county if specified
    if counties and county_col:
        # Normalize county names for comparison
        combined['county_normalized'] = combined[county_col].str.strip().str.upper()
        counties_upper = [c.upper() for c in counties]
        combined = combined[combined['county_normalized'].isin(counties_upper)]
        print(f"Filtered to {len(combined)} facilities in specified counties")

    # Filter for low capacity (greater than 0 to exclude invalid data)
    low_capacity = combined[
        (combined[capacity_col] > 0) &
        (combined[capacity_col] < capacity_threshold)
    ].copy()

    print(f"\nLow-capacity facilities (capacity < {capacity_threshold}): {len(low_capacity)}")

    # Save low capacity facilities
    low_capacity.to_csv('low_capacity_daycares_ca.csv', index=False)
    print("Saved to 'low_capacity_daycares_ca.csv'")

    # Analysis: Count by county
    if county_col:
        print(f"\n{'='*50}")
        print("LOW-CAPACITY FACILITIES BY COUNTY")
        print('='*50)
        county_counts = low_capacity[county_col].value_counts()
        print(county_counts.head(20))

    # Analysis: Count by facility type
    print(f"\n{'='*50}")
    print("LOW-CAPACITY FACILITIES BY TYPE")
    print('='*50)
    type_counts = low_capacity['facility_type'].value_counts()
    print(type_counts)

    # Flag potentially suspicious facilities based on status
    if status_col:
        print(f"\nStatus values found: {low_capacity[status_col].unique()}")

        # Separate by status
        status_breakdown = low_capacity[status_col].value_counts()
        print("\nLow-capacity facilities by status:")
        print(status_breakdown)

        # Flag non-LICENSED facilities (CLOSED, INACTIVE, PENDING, ON PROBATION)
        suspicious = low_capacity[
            ~low_capacity[status_col].str.upper().isin(['LICENSED'])
        ].copy()

        if not suspicious.empty:
            suspicious.to_csv('suspicious_low_capacity_daycares.csv', index=False)
            print(f"\nNon-licensed low-capacity facilities: {len(suspicious)}")
            print("Saved to 'suspicious_low_capacity_daycares.csv'")

            # Breakdown by status
            print("\nBreakdown of non-licensed:")
            print(suspicious[status_col].value_counts())

        # Also save only LICENSED low-capacity for comparison
        licensed_low_cap = low_capacity[
            low_capacity[status_col].str.upper() == 'LICENSED'
        ]
        licensed_low_cap.to_csv('licensed_low_capacity_daycares.csv', index=False)
        print(f"\nActive licensed low-capacity facilities: {len(licensed_low_cap)}")
        print("Saved to 'licensed_low_capacity_daycares.csv'")

    # Summary statistics
    print(f"\n{'='*50}")
    print("SUMMARY STATISTICS")
    print('='*50)
    print(f"Total facilities analyzed: {len(combined)}")
    print(f"Low-capacity facilities (< {capacity_threshold}): {len(low_capacity)}")
    print(f"Capacity range in low-cap: {low_capacity[capacity_col].min()} - {low_capacity[capacity_col].max()}")

    return low_capacity, combined


def detect_fraud_indicators(df):
    """
    Analyze facilities for fraud indicators similar to Minnesota Feeding Our Future case.

    Red flags:
    1. Multiple facilities at same address
    2. Same licensee operating many facilities
    3. Facilities licensed during COVID (2020-2022) - reduced oversight period
    4. Very small capacity at commercial-sounding addresses
    """
    print(f"\n{'='*60}")
    print("FRAUD INDICATOR ANALYSIS")
    print("='*60")

    # Standardize address for comparison
    df = df.copy()
    df['address_normalized'] = (
        df['facility_address'].str.upper().str.strip()
        .str.replace(r'\s+', ' ', regex=True)
        .str.replace(r'\.', '', regex=True)
        .str.replace(r',', '', regex=True)
    )
    df['full_address'] = df['address_normalized'] + ', ' + df['facility_city'].str.upper().str.strip()

    # Initialize fraud score
    df['fraud_score'] = 0
    df['fraud_flags'] = ''

    # =========================================
    # FLAG 1: Duplicate Addresses
    # =========================================
    print(f"\n[FLAG 1] DUPLICATE ADDRESSES")
    print("-" * 40)

    address_counts = df['full_address'].value_counts()
    duplicate_addresses = address_counts[address_counts > 1]

    if not duplicate_addresses.empty:
        print(f"Found {len(duplicate_addresses)} addresses with multiple facilities:")
        for addr, count in duplicate_addresses.head(20).items():
            print(f"  {count}x: {addr}")
            facilities_at_addr = df[df['full_address'] == addr]
            for _, fac in facilities_at_addr.iterrows():
                print(f"      - {fac.get('facility_name', 'N/A')} (Cap: {fac.get('facility_capacity', 'N/A')}, Status: {fac.get('facility_status', 'N/A')})")

        # Add to fraud score
        df.loc[df['full_address'].isin(duplicate_addresses.index), 'fraud_score'] += 2
        df.loc[df['full_address'].isin(duplicate_addresses.index), 'fraud_flags'] += 'DUPLICATE_ADDRESS; '
    else:
        print("  No duplicate addresses found.")

    # Save duplicate address facilities
    dup_addr_facilities = df[df['full_address'].isin(duplicate_addresses.index)].copy()
    if not dup_addr_facilities.empty:
        dup_addr_facilities.to_csv('fraud_flag_duplicate_addresses.csv', index=False)
        print(f"\nSaved {len(dup_addr_facilities)} facilities at duplicate addresses to 'fraud_flag_duplicate_addresses.csv'")

    # =========================================
    # FLAG 2: Licensees with Multiple Facilities
    # =========================================
    print(f"\n[FLAG 2] LICENSEES WITH MULTIPLE FACILITIES")
    print("-" * 40)

    df['licensee_normalized'] = df['licensee'].str.upper().str.strip()
    licensee_counts = df['licensee_normalized'].value_counts()
    multi_facility_licensees = licensee_counts[licensee_counts >= 3]  # 3+ facilities

    if not multi_facility_licensees.empty:
        print(f"Found {len(multi_facility_licensees)} licensees operating 3+ facilities:")
        for licensee, count in multi_facility_licensees.head(15).items():
            total_capacity = df[df['licensee_normalized'] == licensee]['facility_capacity'].sum()
            print(f"  {count} facilities: {licensee} (Total capacity: {total_capacity})")

        # Flag licensees with 5+ facilities (higher risk)
        high_volume_licensees = licensee_counts[licensee_counts >= 5].index
        df.loc[df['licensee_normalized'].isin(high_volume_licensees), 'fraud_score'] += 1
        df.loc[df['licensee_normalized'].isin(high_volume_licensees), 'fraud_flags'] += 'HIGH_VOLUME_LICENSEE; '
    else:
        print("  No licensees with 3+ facilities found.")

    # Save multi-facility licensee data
    multi_lic_facilities = df[df['licensee_normalized'].isin(multi_facility_licensees.index)].copy()
    if not multi_lic_facilities.empty:
        multi_lic_facilities.to_csv('fraud_flag_multi_facility_licensees.csv', index=False)
        print(f"\nSaved {len(multi_lic_facilities)} facilities from multi-facility licensees to 'fraud_flag_multi_facility_licensees.csv'")

    # =========================================
    # FLAG 3: COVID-Era Licenses (2020-2022)
    # =========================================
    print(f"\n[FLAG 3] COVID-ERA LICENSES (2020-2022)")
    print("-" * 40)

    df['license_first_date'] = pd.to_datetime(df['license_first_date'], errors='coerce')
    df['license_year'] = df['license_first_date'].dt.year

    covid_era = df[
        (df['license_year'] >= 2020) &
        (df['license_year'] <= 2022) &
        (df['facility_status'].str.upper() == 'LICENSED')
    ]

    print(f"Facilities licensed during COVID (2020-2022): {len(covid_era)}")
    print("\nBreakdown by year:")
    print(covid_era['license_year'].value_counts().sort_index())

    # Flag COVID-era licenses
    covid_mask = (df['license_year'] >= 2020) & (df['license_year'] <= 2022)
    df.loc[covid_mask, 'fraud_score'] += 1
    df.loc[covid_mask, 'fraud_flags'] += 'COVID_ERA_LICENSE; '

    covid_era.to_csv('fraud_flag_covid_era_licenses.csv', index=False)
    print(f"\nSaved to 'fraud_flag_covid_era_licenses.csv'")

    # =========================================
    # FLAG 4: Recently Closed (Potential Hit-and-Run)
    # =========================================
    print(f"\n[FLAG 4] RECENTLY CLOSED FACILITIES")
    print("-" * 40)

    df['closed_date'] = pd.to_datetime(df['closed_date'], errors='coerce')
    df['closed_year'] = df['closed_date'].dt.year

    # Facilities that opened during COVID and already closed
    covid_opened_closed = df[
        (df['license_year'] >= 2020) &
        (df['facility_status'].str.upper() == 'CLOSED')
    ]

    print(f"Facilities opened 2020+ and now CLOSED: {len(covid_opened_closed)}")

    if not covid_opened_closed.empty:
        # Calculate how long they operated
        covid_opened_closed = covid_opened_closed.copy()
        covid_opened_closed['months_operated'] = (
            (covid_opened_closed['closed_date'] - covid_opened_closed['license_first_date']).dt.days / 30
        ).round(1)

        short_lived = covid_opened_closed[covid_opened_closed['months_operated'] < 24]
        print(f"  Operated less than 2 years: {len(short_lived)}")

        if not short_lived.empty:
            short_lived.to_csv('fraud_flag_short_lived_facilities.csv', index=False)
            print(f"  Saved to 'fraud_flag_short_lived_facilities.csv'")

            # Add to fraud score
            short_lived_idx = short_lived.index
            df.loc[df.index.isin(short_lived_idx), 'fraud_score'] += 2
            df.loc[df.index.isin(short_lived_idx), 'fraud_flags'] += 'SHORT_LIVED; '

    # =========================================
    # COMBINED HIGH-RISK FACILITIES
    # =========================================
    print(f"\n{'='*60}")
    print("HIGH-RISK FACILITIES (Fraud Score >= 3)")
    print("='*60")

    high_risk = df[df['fraud_score'] >= 3].copy()

    if not high_risk.empty:
        # Add Google Maps link for verification
        high_risk['google_maps_url'] = high_risk.apply(
            lambda row: f"https://www.google.com/maps/search/{quote(str(row['facility_address']) + ', ' + str(row['facility_city']) + ', CA')}",
            axis=1
        )

        print(f"\nFound {len(high_risk)} high-risk facilities:")
        for _, fac in high_risk.head(20).iterrows():
            print(f"\n  {fac.get('facility_name', 'N/A')}")
            print(f"    Address: {fac.get('facility_address', 'N/A')}, {fac.get('facility_city', 'N/A')}")
            print(f"    Licensee: {fac.get('licensee', 'N/A')}")
            print(f"    Capacity: {fac.get('facility_capacity', 'N/A')} | Status: {fac.get('facility_status', 'N/A')}")
            print(f"    Licensed: {fac.get('license_first_date', 'N/A')}")
            print(f"    Fraud Score: {fac['fraud_score']} | Flags: {fac['fraud_flags']}")
            print(f"    Verify: {fac['google_maps_url']}")

        high_risk.to_csv('HIGH_RISK_FACILITIES.csv', index=False)
        print(f"\n*** Saved {len(high_risk)} high-risk facilities to 'HIGH_RISK_FACILITIES.csv' ***")
    else:
        print("No facilities with fraud score >= 3")

    # =========================================
    # SUMMARY
    # =========================================
    print(f"\n{'='*60}")
    print("FRAUD ANALYSIS SUMMARY")
    print("='*60")
    print(f"Total facilities analyzed: {len(df)}")
    print(f"Facilities at duplicate addresses: {len(dup_addr_facilities)}")
    print(f"Facilities from multi-facility licensees (3+): {len(multi_lic_facilities)}")
    print(f"COVID-era licenses (2020-2022): {len(covid_era)}")
    print(f"Short-lived facilities (<2 years): {len(short_lived) if 'short_lived' in dir() and not short_lived.empty else 0}")
    print(f"HIGH-RISK (score >= 3): {len(high_risk)}")

    print(f"\n{'='*60}")
    print("OUTPUT FILES GENERATED")
    print("='*60")
    print("  - fraud_flag_duplicate_addresses.csv")
    print("  - fraud_flag_multi_facility_licensees.csv")
    print("  - fraud_flag_covid_era_licenses.csv")
    print("  - fraud_flag_short_lived_facilities.csv")
    print("  - HIGH_RISK_FACILITIES.csv  <-- START HERE")

    return df


if __name__ == "__main__":
    # Run analysis
    # Set capacity_threshold based on your needs
    # Family child care homes typically have capacity 6-14
    # Set to 5 for very small operations, or higher to include small family homes

    low_cap_results, all_facilities = analyze_low_capacity_facilities(
        capacity_threshold=14,  # Adjust as needed
        counties=None  # None = all counties; or pass list like ['Los Angeles', 'San Diego']
    )

    if not low_cap_results.empty:
        print(f"\n{'='*50}")
        print("SAMPLE OF LOW-CAPACITY FACILITIES")
        print('='*50)
        # Show sample with key columns
        display_cols = [col for col in low_cap_results.columns if any(
            x in col.lower() for x in ['name', 'facility_name', 'county', 'capacity', 'status', 'address', 'city']
        )][:8]
        if display_cols:
            print(low_cap_results[display_cols].head(10).to_string())

    # Run fraud detection on ALL facilities (not just low capacity)
    if not all_facilities.empty:
        print("\n" + "="*60)
        print("RUNNING FRAUD DETECTION ON ALL FACILITIES...")
        print("="*60)
        detect_fraud_indicators(all_facilities)
