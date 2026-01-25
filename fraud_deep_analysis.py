"""
Deep Fraud Analysis for California Childcare Facilities
Based on patterns from Minnesota Feeding Our Future investigation

This script performs:
1. Phone number duplicate analysis (same phone = same operator hiding connections)
2. Licensee name pattern matching (shell company detection)
3. Geographic clustering analysis (unusual concentrations)
4. Cross-reference with CACFP county data
5. Generate prioritized investigation list
"""

import pandas as pd
import numpy as np
from collections import Counter
from urllib.parse import quote
import re
import requests
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Load the facility data
def load_data():
    """Load all facility data from previously downloaded CSVs."""
    print("Loading facility data...")

    try:
        centers = pd.read_csv('raw_child_care_centers.csv', low_memory=False)
        homes = pd.read_csv('raw_family_child_care_homes.csv', low_memory=False)

        centers['facility_type'] = 'child_care_center'
        homes['facility_type'] = 'family_child_care_home'

        df = pd.concat([centers, homes], ignore_index=True)
        print(f"Loaded {len(df)} total facilities")
        return df
    except FileNotFoundError:
        print("ERROR: Run ca_childcare_analysis.py first to download data")
        return pd.DataFrame()


def analyze_duplicate_phones(df):
    """
    FLAG: Multiple facilities sharing the same phone number.
    This can indicate same operator trying to hide connections.
    """
    print(f"\n{'='*60}")
    print("ANALYSIS 1: DUPLICATE PHONE NUMBERS")
    print("="*60)

    # Clean phone numbers
    df = df.copy()
    df['phone_clean'] = df['facility_telephone_number'].astype(str).str.replace(r'[^\d]', '', regex=True)
    df['phone_clean'] = df['phone_clean'].replace('', np.nan).replace('nan', np.nan)

    # Find duplicates (exclude NaN and short numbers)
    valid_phones = df[df['phone_clean'].str.len() >= 10]['phone_clean']
    phone_counts = valid_phones.value_counts()
    dup_phones = phone_counts[phone_counts > 1]

    print(f"Found {len(dup_phones)} phone numbers used by multiple facilities")

    # Flag phones with 3+ facilities (more suspicious)
    suspicious_phones = phone_counts[phone_counts >= 3]
    print(f"Phone numbers with 3+ facilities: {len(suspicious_phones)}")

    results = []
    for phone, count in suspicious_phones.head(50).items():
        facilities = df[df['phone_clean'] == phone]
        licensees = facilities['licensee'].unique()

        # More suspicious if different licensee names
        if len(licensees) > 1:
            suspicion = "HIGH - Different licensees!"
        else:
            suspicion = "Medium - Same licensee"

        results.append({
            'phone': phone,
            'facility_count': count,
            'unique_licensees': len(licensees),
            'licensees': '; '.join(str(l) for l in licensees[:5]),
            'suspicion_level': suspicion,
            'facilities': '; '.join(facilities['facility_name'].head(5).tolist())
        })

    dup_phone_df = pd.DataFrame(results)
    if not dup_phone_df.empty:
        # Sort by suspicion (different licensees first)
        dup_phone_df = dup_phone_df.sort_values(['unique_licensees', 'facility_count'], ascending=[False, False])
        dup_phone_df.to_csv('fraud_analysis_duplicate_phones.csv', index=False)

        print("\nMost suspicious (different licensees, same phone):")
        high_suspicion = dup_phone_df[dup_phone_df['unique_licensees'] > 1]
        for _, row in high_suspicion.head(15).iterrows():
            print(f"\n  Phone: {row['phone']} ({row['facility_count']} facilities)")
            print(f"    Licensees: {row['licensees']}")
            print(f"    Facilities: {row['facilities']}")

        print(f"\nSaved to 'fraud_analysis_duplicate_phones.csv'")

    # Add flag to main dataframe
    df['flag_shared_phone'] = df['phone_clean'].isin(suspicious_phones.index)

    return df, dup_phone_df


def analyze_licensee_patterns(df):
    """
    FLAG: Shell company detection through name patterns.
    Look for:
    - Similar LLC names (slight variations)
    - Generic names (ABC, 123, Learning, Academy patterns)
    - Same person with multiple LLCs
    """
    print(f"\n{'='*60}")
    print("ANALYSIS 2: LICENSEE NAME PATTERNS (Shell Company Detection)")
    print("="*60)

    df = df.copy()
    df['licensee_clean'] = df['licensee'].str.upper().str.strip()

    # Extract potential person names from LLCs
    def extract_person_name(licensee):
        if pd.isna(licensee):
            return None
        licensee = str(licensee).upper()
        # Remove common business suffixes
        for suffix in [' LLC', ' INC', ' INC.', ' CORP', ' CORPORATION', ' L.L.C.', ' L.L.C']:
            licensee = licensee.replace(suffix, '')
        # If it looks like a person name (comma separated or short)
        if ',' in licensee or len(licensee.split()) <= 3:
            return licensee.strip()
        return None

    df['possible_person'] = df['licensee'].apply(extract_person_name)

    # Find people with multiple facilities under different business names
    person_counts = df[df['possible_person'].notna()].groupby('possible_person').agg({
        'facility_name': 'count',
        'licensee': lambda x: list(x.unique())
    }).reset_index()
    person_counts.columns = ['person_name', 'facility_count', 'business_names']
    person_counts = person_counts[person_counts['facility_count'] >= 3]
    person_counts = person_counts.sort_values('facility_count', ascending=False)

    print(f"\nPeople operating 3+ facilities:")
    for _, row in person_counts.head(20).iterrows():
        print(f"  {row['person_name']}: {row['facility_count']} facilities")

    # Detect generic/suspicious naming patterns
    suspicious_patterns = [
        r'^[A-Z]\s*&\s*[A-Z]\s',  # A & B pattern
        r'LEARNING CENTER',
        r'CHILD DEVELOPMENT',
        r'LITTLE\s*(ONES|ANGELS|STARS|KIDS)',
        r'^(ABC|123)',
        r'KIDZ|KIDDS|KIDDZ',
        r'ACADEMY\s*LLC',
        r'BRIGHT\s*(START|FUTURE|HORIZON)',
    ]

    df['generic_name_flag'] = False
    for pattern in suspicious_patterns:
        df['generic_name_flag'] |= df['licensee_clean'].str.contains(pattern, regex=True, na=False)

    generic_count = df['generic_name_flag'].sum()
    print(f"\nFacilities with generic/suspicious name patterns: {generic_count}")

    # Find LLCs registered in quick succession (would need SOS data for dates)
    # For now, flag LLCs with similar names

    # Group licensees by first few words to find variations
    df['licensee_prefix'] = df['licensee_clean'].str.split().str[:2].str.join(' ')
    prefix_counts = df['licensee_prefix'].value_counts()
    common_prefixes = prefix_counts[prefix_counts >= 5].index

    print(f"\nCommon licensee name prefixes (potential related entities):")
    for prefix in list(common_prefixes)[:15]:
        if len(prefix) > 3:  # Skip very short prefixes
            count = prefix_counts[prefix]
            print(f"  '{prefix}...': {count} facilities")

    return df, person_counts


def analyze_geographic_clustering(df):
    """
    FLAG: Unusual geographic concentrations.
    Look for many facilities in small areas that don't match population.
    """
    print(f"\n{'='*60}")
    print("ANALYSIS 3: GEOGRAPHIC CLUSTERING")
    print("="*60)

    df = df.copy()

    # Analyze by ZIP code
    zip_counts = df.groupby('facility_zip').agg({
        'facility_name': 'count',
        'facility_capacity': 'sum',
        'county_name': 'first',
        'facility_city': 'first'
    }).reset_index()
    zip_counts.columns = ['zip', 'facility_count', 'total_capacity', 'county', 'city']
    zip_counts = zip_counts.sort_values('facility_count', ascending=False)

    print("\nTop 20 ZIP codes by facility count:")
    print(zip_counts.head(20).to_string(index=False))

    # Flag ZIPs with unusually high concentrations
    mean_per_zip = zip_counts['facility_count'].mean()
    std_per_zip = zip_counts['facility_count'].std()
    threshold = mean_per_zip + (2 * std_per_zip)  # 2 standard deviations above mean

    high_concentration_zips = zip_counts[zip_counts['facility_count'] > threshold]
    print(f"\nZIP codes with unusually high concentrations (>{threshold:.0f}): {len(high_concentration_zips)}")

    # Analyze COVID-era facilities by geography
    df['license_date'] = pd.to_datetime(df['license_first_date'], errors='coerce')
    df['license_year'] = df['license_date'].dt.year

    covid_by_zip = df[df['license_year'].isin([2020, 2021, 2022])].groupby('facility_zip').size()
    covid_hotspots = covid_by_zip.sort_values(ascending=False).head(20)

    print(f"\nTop ZIP codes for COVID-era (2020-2022) new licenses:")
    for zip_code, count in covid_hotspots.items():
        city = df[df['facility_zip'] == zip_code]['facility_city'].iloc[0] if len(df[df['facility_zip'] == zip_code]) > 0 else 'Unknown'
        print(f"  {zip_code} ({city}): {count} new facilities")

    zip_counts.to_csv('fraud_analysis_geographic_clusters.csv', index=False)
    print(f"\nSaved to 'fraud_analysis_geographic_clusters.csv'")

    return df, zip_counts


def download_cacfp_data():
    """
    Download CACFP county-level data for cross-reference.
    """
    print(f"\n{'='*60}")
    print("ANALYSIS 4: CACFP DATA CROSS-REFERENCE")
    print("="*60)

    # Download the impact report
    url = "https://www.cdss.ca.gov/Portals/13/CACFP/CACFP%202023-24%20Impact%20Report.xlsx"
    print(f"Downloading CACFP Impact Report...")

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        with open('cacfp_impact_report_2023-24.xlsx', 'wb') as f:
            f.write(response.content)

        # Try to read the Excel file
        try:
            cacfp_df = pd.read_excel('cacfp_impact_report_2023-24.xlsx', sheet_name=None)
            print(f"Downloaded CACFP data. Sheets: {list(cacfp_df.keys())}")

            # Print summary of each sheet
            for sheet_name, sheet_df in cacfp_df.items():
                print(f"\n  Sheet '{sheet_name}': {len(sheet_df)} rows, {len(sheet_df.columns)} columns")
                print(f"    Columns: {list(sheet_df.columns)[:5]}...")

            return cacfp_df
        except Exception as e:
            print(f"  Could not parse Excel: {e}")
            return None

    except Exception as e:
        print(f"  Could not download CACFP data: {e}")
        return None


def generate_investigation_report(df):
    """
    Generate a prioritized investigation report with the most suspicious facilities.
    """
    print(f"\n{'='*60}")
    print("GENERATING PRIORITIZED INVESTIGATION REPORT")
    print("="*60)

    df = df.copy()

    # Calculate composite risk score
    df['risk_score'] = 0

    # License timing (COVID era)
    df['license_date'] = pd.to_datetime(df['license_first_date'], errors='coerce')
    df['license_year'] = df['license_date'].dt.year
    df.loc[df['license_year'].isin([2020, 2021, 2022]), 'risk_score'] += 2

    # Status (closed/inactive)
    df.loc[df['facility_status'].str.upper().isin(['CLOSED', 'INACTIVE']), 'risk_score'] += 2

    # Short operation period
    df['closed_date_parsed'] = pd.to_datetime(df['closed_date'], errors='coerce')
    df['months_operated'] = ((df['closed_date_parsed'] - df['license_date']).dt.days / 30).round(1)
    df.loc[(df['months_operated'] > 0) & (df['months_operated'] < 24), 'risk_score'] += 3

    # Shared phone
    if 'flag_shared_phone' in df.columns:
        df.loc[df['flag_shared_phone'] == True, 'risk_score'] += 2

    # Generic name
    if 'generic_name_flag' in df.columns:
        df.loc[df['generic_name_flag'] == True, 'risk_score'] += 1

    # Add Google Maps verification link
    df['google_maps_url'] = df.apply(
        lambda row: f"https://www.google.com/maps/search/{quote(str(row['facility_address']) + ', ' + str(row['facility_city']) + ', CA')}"
        if pd.notna(row['facility_address']) and row['facility_address'] != 'UNAVAILABLE' else '',
        axis=1
    )

    # Sort by risk score
    high_risk = df[df['risk_score'] >= 5].sort_values('risk_score', ascending=False)

    print(f"\nHIGHEST RISK FACILITIES (score >= 5): {len(high_risk)}")

    # Select columns for report
    report_cols = [
        'facility_name', 'licensee', 'facility_address', 'facility_city',
        'facility_zip', 'county_name', 'facility_capacity', 'facility_status',
        'license_first_date', 'closed_date', 'months_operated',
        'facility_telephone_number', 'risk_score', 'google_maps_url'
    ]
    report_cols = [c for c in report_cols if c in high_risk.columns]

    investigation_report = high_risk[report_cols].copy()
    investigation_report.to_csv('PRIORITY_INVESTIGATION_LIST.csv', index=False)

    print(f"\n*** Saved {len(investigation_report)} facilities to 'PRIORITY_INVESTIGATION_LIST.csv' ***")

    # Print top 25 for immediate review
    print(f"\n{'='*60}")
    print("TOP 25 FACILITIES FOR IMMEDIATE INVESTIGATION")
    print("="*60)

    for i, (_, row) in enumerate(high_risk.head(25).iterrows(), 1):
        print(f"\n{i}. {row['facility_name']} (Risk Score: {row['risk_score']})")
        print(f"   Licensee: {row['licensee']}")
        print(f"   Address: {row['facility_address']}, {row['facility_city']} {row['facility_zip']}")
        print(f"   County: {row['county_name']}")
        print(f"   Status: {row['facility_status']} | Capacity: {row['facility_capacity']}")
        print(f"   Licensed: {row['license_first_date']} | Closed: {row['closed_date']}")
        if pd.notna(row.get('months_operated')) and row['months_operated'] > 0:
            print(f"   Operated: {row['months_operated']} months")
        print(f"   Phone: {row['facility_telephone_number']}")
        print(f"   VERIFY: {row['google_maps_url']}")

    # Summary statistics
    print(f"\n{'='*60}")
    print("RISK SCORE DISTRIBUTION")
    print("="*60)
    print(df['risk_score'].value_counts().sort_index(ascending=False))

    return investigation_report


def main():
    """Run all fraud detection analyses."""
    print("="*60)
    print("CALIFORNIA CHILDCARE FRAUD DEEP ANALYSIS")
    print("Based on Minnesota Feeding Our Future Investigation Patterns")
    print("="*60)
    print(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    # Load data
    df = load_data()
    if df.empty:
        return

    # Run analyses
    df, dup_phones = analyze_duplicate_phones(df)
    df, person_patterns = analyze_licensee_patterns(df)
    df, geo_clusters = analyze_geographic_clustering(df)
    cacfp_data = download_cacfp_data()

    # Generate final report
    investigation_report = generate_investigation_report(df)

    # Final summary
    print(f"\n{'='*60}")
    print("ANALYSIS COMPLETE - OUTPUT FILES")
    print("="*60)
    print("""
    1. PRIORITY_INVESTIGATION_LIST.csv  <-- START HERE
       Highest risk facilities sorted by composite score

    2. fraud_analysis_duplicate_phones.csv
       Facilities sharing phone numbers (potential hidden connections)

    3. fraud_analysis_geographic_clusters.csv
       ZIP codes with unusual facility concentrations

    4. cacfp_impact_report_2023-24.xlsx
       Federal food program county data for cross-reference

    NEXT STEPS FOR INVESTIGATION:
    - Use Google Maps links to verify facilities exist
    - Cross-reference licensees with CA Secretary of State business search
    - File Public Records Act request for CACFP participant list
    - Check for news articles about licensees
    - Look for patterns in registered agent addresses
    """)


if __name__ == "__main__":
    main()
