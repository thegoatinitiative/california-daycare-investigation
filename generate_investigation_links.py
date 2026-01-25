"""
Generate Investigation Links for Priority Facilities

Creates clickable links for:
1. Google Maps - Physical verification
2. CA Secretary of State - Business entity lookup
3. Google News search - Check for prior investigations/news
4. LinkedIn - Find the licensee/owner
"""

import pandas as pd
from urllib.parse import quote
import webbrowser
import time

def generate_sos_search_url(business_name):
    """Generate CA Secretary of State bizfile search URL."""
    # Clean up the business name for search
    name = str(business_name).strip()
    # Remove common suffixes that might cause search issues
    for suffix in [', INC.', ', INC', ' INC.', ' INC', ' LLC', ', LLC', ' L.L.C.', ' CORP', ' CORPORATION']:
        name = name.replace(suffix, '')
    return f"https://bizfileonline.sos.ca.gov/search/business?searchType=Business+Name&searchCriteria={quote(name)}"


def generate_ccld_inspection_url(facility_number):
    """Generate CCLD facility detail page URL for inspection history."""
    if pd.isna(facility_number):
        return ''
    fac_num = str(int(facility_number)) if isinstance(facility_number, float) else str(facility_number)
    return f"https://www.ccld.dss.ca.gov/carefacilitysearch/FacDetail/{fac_num}"


def generate_google_news_url(business_name, city):
    """Generate Google News search URL."""
    query = f'"{business_name}" {city} California daycare'
    return f"https://www.google.com/search?q={quote(query)}&tbm=nws"


def generate_google_search_url(business_name, licensee):
    """Generate general Google search URL."""
    query = f'"{licensee}" OR "{business_name}" California daycare fraud OR investigation OR lawsuit'
    return f"https://www.google.com/search?q={quote(query)}"


def generate_linkedin_url(person_name):
    """Generate LinkedIn search URL for a person."""
    # Only use if it looks like a person name (has comma)
    if ',' in str(person_name):
        # Convert "LASTNAME, FIRSTNAME" to "Firstname Lastname"
        parts = person_name.split(',')
        if len(parts) >= 2:
            name = f"{parts[1].strip()} {parts[0].strip()}"
            return f"https://www.linkedin.com/search/results/all/?keywords={quote(name)}"
    return None


def create_investigation_report():
    """Create comprehensive investigation report with all links."""
    print("Loading priority investigation list...")

    try:
        df = pd.read_csv('PRIORITY_INVESTIGATION_LIST.csv')
    except FileNotFoundError:
        print("ERROR: Run fraud_deep_analysis.py first")
        return

    print(f"Processing {len(df)} high-risk facilities...")

    # Try to merge with raw data to get facility numbers if not present
    if 'facility_number' not in df.columns:
        try:
            raw_centers = pd.read_csv('raw_child_care_centers.csv', low_memory=False)
            raw_homes = pd.read_csv('raw_family_child_care_homes.csv', low_memory=False)
            raw_all = pd.concat([raw_centers, raw_homes], ignore_index=True)

            # Merge on facility_name and licensee
            df = df.merge(
                raw_all[['facility_name', 'licensee', 'facility_number']],
                on=['facility_name', 'licensee'],
                how='left'
            )
            print(f"  Merged facility numbers for {df['facility_number'].notna().sum()} facilities")
        except Exception as e:
            print(f"  Could not merge facility numbers: {e}")
            df['facility_number'] = None

    # Generate all investigation links
    df['sos_business_search'] = df['licensee'].apply(generate_sos_search_url)
    df['google_news_search'] = df.apply(
        lambda r: generate_google_news_url(r['facility_name'], r.get('facility_city', '')),
        axis=1
    )
    df['google_investigation_search'] = df.apply(
        lambda r: generate_google_search_url(r['facility_name'], r['licensee']),
        axis=1
    )
    df['linkedin_search'] = df['licensee'].apply(generate_linkedin_url)
    df['ccld_inspection_history'] = df['facility_number'].apply(generate_ccld_inspection_url)

    # Save enhanced report
    df.to_csv('INVESTIGATION_WITH_LINKS.csv', index=False)
    print(f"Saved to 'INVESTIGATION_WITH_LINKS.csv'")

    # Create HTML report for easy clicking
    html_report = """
<!DOCTYPE html>
<html>
<head>
    <title>California Daycare Fraud Investigation Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        h1 { color: #333; }
        .facility { background: white; padding: 15px; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .facility.score-10 { border-left: 5px solid #ff0000; }
        .facility.score-9 { border-left: 5px solid #ff4444; }
        .facility.score-8 { border-left: 5px solid #ff8800; }
        .facility.score-7 { border-left: 5px solid #ffaa00; }
        .facility.score-6 { border-left: 5px solid #ffcc00; }
        .facility.score-5 { border-left: 5px solid #ffee00; }
        .name { font-size: 18px; font-weight: bold; color: #333; }
        .risk { font-size: 14px; color: #ff0000; font-weight: bold; }
        .detail { margin: 5px 0; color: #666; }
        .links { margin-top: 10px; }
        .links a {
            display: inline-block;
            padding: 5px 10px;
            margin: 2px;
            background: #0066cc;
            color: white;
            text-decoration: none;
            border-radius: 4px;
            font-size: 12px;
        }
        .links a:hover { background: #0055aa; }
        .links a.maps { background: #34a853; }
        .links a.sos { background: #9c27b0; }
        .links a.news { background: #ea4335; }
        .links a.google { background: #fbbc05; color: #333; }
        .summary { background: #fff3cd; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
        .filters { margin-bottom: 20px; }
        .filters button { padding: 8px 15px; margin: 2px; cursor: pointer; }
    </style>
</head>
<body>
    <h1>🔍 California Daycare Fraud Investigation Report</h1>
    <div class="summary">
        <strong>Generated:</strong> """ + pd.Timestamp.now().strftime('%Y-%m-%d %H:%M') + """<br>
        <strong>Total High-Risk Facilities:</strong> """ + str(len(df)) + """<br>
        <strong>Risk Score Range:</strong> """ + str(df['risk_score'].min()) + """ - """ + str(df['risk_score'].max()) + """
    </div>

    <div class="filters">
        <strong>Filter by Risk Score:</strong>
        <button onclick="filterByScore(0)">Show All</button>
        <button onclick="filterByScore(10)">Score 10</button>
        <button onclick="filterByScore(9)">Score 9</button>
        <button onclick="filterByScore(8)">Score 8+</button>
        <button onclick="filterByScore(7)">Score 7+</button>
    </div>

    <div id="facilities">
"""

    for _, row in df.head(200).iterrows():  # Top 200 for HTML report
        score = int(row.get('risk_score', 0))
        score_class = f"score-{min(score, 10)}"

        html_report += f"""
        <div class="facility {score_class}" data-score="{score}">
            <div class="name">{row['facility_name']}</div>
            <div class="risk">Risk Score: {score}</div>
            <div class="detail"><strong>Licensee:</strong> {row['licensee']}</div>
            <div class="detail"><strong>Address:</strong> {row.get('facility_address', 'N/A')}, {row.get('facility_city', '')}, CA {row.get('facility_zip', '')}</div>
            <div class="detail"><strong>County:</strong> {row.get('county_name', 'N/A')}</div>
            <div class="detail"><strong>Status:</strong> {row.get('facility_status', 'N/A')} | <strong>Capacity:</strong> {row.get('facility_capacity', 'N/A')}</div>
            <div class="detail"><strong>Licensed:</strong> {row.get('license_first_date', 'N/A')} | <strong>Closed:</strong> {row.get('closed_date', 'N/A')}</div>
            <div class="detail"><strong>Operated:</strong> {row.get('months_operated', 'N/A')} months</div>
            <div class="detail"><strong>Phone:</strong> {row.get('facility_telephone_number', 'N/A')}</div>
            <div class="links">
                <a href="{row.get('google_maps_url', '#')}" target="_blank" class="maps">📍 Google Maps</a>
                <a href="{row.get('ccld_inspection_history', '#')}" target="_blank" class="sos" style="background:#ff5722;">📋 CCLD Inspections</a>
                <a href="{row['sos_business_search']}" target="_blank" class="sos">🏛️ CA SOS Business</a>
                <a href="{row['google_news_search']}" target="_blank" class="news">📰 News Search</a>
                <a href="{row['google_investigation_search']}" target="_blank" class="google">🔍 Investigation Search</a>
            </div>
        </div>
"""

    html_report += """
    </div>

    <script>
        function filterByScore(minScore) {
            document.querySelectorAll('.facility').forEach(el => {
                const score = parseInt(el.dataset.score);
                el.style.display = (minScore === 0 || score >= minScore) ? 'block' : 'none';
            });
        }
    </script>
</body>
</html>
"""

    with open('INVESTIGATION_REPORT.html', 'w') as f:
        f.write(html_report)

    print(f"Saved interactive HTML report to 'INVESTIGATION_REPORT.html'")

    # Print summary
    print(f"\n{'='*60}")
    print("INVESTIGATION REPORT SUMMARY")
    print('='*60)
    print(f"Total facilities in report: {len(df)}")
    print(f"\nRisk Score Distribution:")
    print(df['risk_score'].value_counts().sort_index(ascending=False))

    print(f"\n{'='*60}")
    print("TOP 10 HIGHEST RISK - IMMEDIATE INVESTIGATION NEEDED")
    print('='*60)

    for i, (_, row) in enumerate(df.head(10).iterrows(), 1):
        print(f"\n{i}. {row['facility_name']}")
        print(f"   Risk Score: {row['risk_score']}")
        print(f"   Licensee: {row['licensee']}")
        print(f"   Location: {row.get('facility_city', 'N/A')}, CA")
        print(f"   ")
        print(f"   VERIFY LINKS:")
        print(f"   - Maps: {row.get('google_maps_url', 'N/A')}")
        print(f"   - SOS: {row['sos_business_search']}")
        print(f"   - News: {row['google_news_search']}")


def open_top_facilities(n=5):
    """Open investigation links for top N facilities in browser."""
    try:
        df = pd.read_csv('INVESTIGATION_WITH_LINKS.csv')
    except FileNotFoundError:
        print("ERROR: Run create_investigation_report() first")
        return

    print(f"Opening investigation links for top {n} facilities...")

    for i, (_, row) in enumerate(df.head(n).iterrows(), 1):
        print(f"\n{i}. Opening links for: {row['facility_name']}")

        # Open Google Maps
        if pd.notna(row.get('google_maps_url')):
            webbrowser.open(row['google_maps_url'])
            time.sleep(0.5)

        # Open SOS search
        webbrowser.open(row['sos_business_search'])
        time.sleep(0.5)

        # Open news search
        webbrowser.open(row['google_news_search'])

        if i < n:
            input(f"\nPress Enter to continue to facility {i+1}...")


if __name__ == "__main__":
    create_investigation_report()

    print("\n" + "="*60)
    print("NEXT STEPS")
    print("="*60)
    print("""
    1. Open 'INVESTIGATION_REPORT.html' in your browser
       - Click links to verify each facility

    2. For each high-risk facility:
       a. Check Google Maps - Does it look like a daycare?
       b. Check CA SOS - Is the business registered? When? Who owns it?
       c. Check News - Any prior investigations or complaints?

    3. File a Public Records Act request to CDSS for:
       - CACFP participating provider list
       - Complaint history for flagged facilities

    4. Cross-reference owners/agents across multiple facilities

    To auto-open links for top facilities, run:
        python3 -c "from generate_investigation_links import open_top_facilities; open_top_facilities(5)"
    """)
