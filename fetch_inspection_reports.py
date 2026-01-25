"""
Fetch Inspection/Complaint Reports from CA CCLD Transparency API

The API endpoint format:
https://www.ccld.dss.ca.gov/transparencyapi/api/FacilityReports?facNum={facility_number}&inx={index}

This script fetches available inspection reports for high-risk facilities.
"""

import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import re
import os
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# API endpoints
FACILITY_VISITS_URL = "https://www.ccld.dss.ca.gov/carefacilitysearch/FacDetail/{facility_number}"
REPORT_API_URL = "https://www.ccld.dss.ca.gov/transparencyapi/api/FacilityReports"


def get_facility_visits_page(facility_number):
    """Fetch the facility detail page to find inspection report links."""
    url = FACILITY_VISITS_URL.format(facility_number=facility_number)
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            return response.text
    except Exception as e:
        print(f"    Error fetching facility page: {e}")
    return None


def parse_inspection_links(html_content):
    """Parse inspection report links from facility detail page."""
    if not html_content:
        return []

    soup = BeautifulSoup(html_content, 'html.parser')
    reports = []

    # Look for links to inspection reports
    # The reports are typically linked with parameters like facNum and inx
    for link in soup.find_all('a', href=True):
        href = link.get('href', '')
        if 'FacilityReports' in href or 'transparencyapi' in href.lower():
            reports.append({
                'url': href if href.startswith('http') else f"https://www.ccld.dss.ca.gov{href}",
                'text': link.get_text(strip=True)
            })

    # Also look for visit history tables
    tables = soup.find_all('table')
    for table in tables:
        rows = table.find_all('tr')
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 2:
                # Check for date patterns in cells
                for cell in cells:
                    text = cell.get_text(strip=True)
                    if re.search(r'\d{1,2}/\d{1,2}/\d{4}', text):
                        link = cell.find('a')
                        if link and link.get('href'):
                            reports.append({
                                'date': text,
                                'url': link.get('href'),
                                'text': link.get_text(strip=True)
                            })

    return reports


def fetch_report_content(url):
    """Fetch and parse an inspection report."""
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract key information from the report
            report_data = {
                'url': url,
                'raw_text': soup.get_text(separator=' ', strip=True)[:5000]  # First 5000 chars
            }

            # Look for violation types
            text = report_data['raw_text'].upper()
            report_data['has_type_a'] = 'TYPE A' in text
            report_data['has_type_b'] = 'TYPE B' in text
            report_data['has_violations'] = 'VIOLATION' in text or 'DEFICIENCY' in text
            report_data['has_complaint'] = 'COMPLAINT' in text

            return report_data
    except Exception as e:
        print(f"    Error fetching report: {e}")
    return None


def check_facility_reports(facility_number, facility_name):
    """Check for inspection reports for a specific facility."""
    print(f"  Checking {facility_name} ({facility_number})...")

    # Try direct API call with different indices
    reports_found = []

    for inx in range(5):  # Check first 5 possible report indices
        url = f"{REPORT_API_URL}?facNum={facility_number}&inx={inx}"
        try:
            response = requests.get(url, timeout=15)
            if response.status_code == 200 and len(response.text) > 500:
                # Parse the report
                soup = BeautifulSoup(response.text, 'html.parser')
                text = soup.get_text(separator=' ', strip=True)

                if 'facility' in text.lower() and len(text) > 100:
                    # Extract date if present
                    date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', text)
                    report_date = date_match.group(1) if date_match else 'Unknown'

                    # Check for violations
                    text_upper = text.upper()
                    has_type_a = 'TYPE A' in text_upper
                    has_type_b = 'TYPE B' in text_upper
                    has_violations = 'VIOLATION' in text_upper or 'DEFICIENCY' in text_upper or 'CITATION' in text_upper
                    has_complaint = 'COMPLAINT' in text_upper

                    reports_found.append({
                        'report_index': inx,
                        'url': url,
                        'date': report_date,
                        'has_type_a_violation': has_type_a,
                        'has_type_b_violation': has_type_b,
                        'has_any_violation': has_violations,
                        'is_complaint_investigation': has_complaint,
                        'text_preview': text[:500]
                    })
                    print(f"    Found report {inx}: Date={report_date}, Violations={has_violations}, TypeA={has_type_a}")

            time.sleep(0.3)  # Rate limiting

        except Exception as e:
            pass  # Skip errors silently for missing reports

    return reports_found


def analyze_high_risk_facilities():
    """Fetch inspection data for all high-risk facilities."""
    print("="*60)
    print("FETCHING INSPECTION REPORTS FOR HIGH-RISK FACILITIES")
    print("="*60)

    # Load priority investigation list
    try:
        df = pd.read_csv('PRIORITY_INVESTIGATION_LIST.csv')
    except FileNotFoundError:
        print("ERROR: PRIORITY_INVESTIGATION_LIST.csv not found")
        print("Run fraud_deep_analysis.py first")
        return

    print(f"Loaded {len(df)} high-risk facilities")

    # Focus on highest risk (score >= 7)
    high_risk = df[df['risk_score'] >= 7].copy()
    print(f"Checking {len(high_risk)} facilities with risk score >= 7")

    all_reports = []
    facilities_with_violations = []

    for i, (_, row) in enumerate(high_risk.iterrows()):
        facility_number = row.get('facility_number')
        facility_name = row.get('facility_name', 'Unknown')

        if pd.isna(facility_number):
            continue

        # Convert to string and clean
        facility_number = str(int(facility_number)) if not pd.isna(facility_number) else None
        if not facility_number:
            continue

        print(f"\n[{i+1}/{len(high_risk)}] {facility_name}")

        reports = check_facility_reports(facility_number, facility_name)

        if reports:
            for report in reports:
                report['facility_number'] = facility_number
                report['facility_name'] = facility_name
                report['licensee'] = row.get('licensee', '')
                report['risk_score'] = row.get('risk_score', 0)
                report['facility_status'] = row.get('facility_status', '')
                all_reports.append(report)

                if report.get('has_any_violation') or report.get('has_type_a_violation'):
                    facilities_with_violations.append({
                        'facility_number': facility_number,
                        'facility_name': facility_name,
                        'licensee': row.get('licensee', ''),
                        'risk_score': row.get('risk_score', 0),
                        'report_date': report.get('date', ''),
                        'type_a_violation': report.get('has_type_a_violation', False),
                        'type_b_violation': report.get('has_type_b_violation', False),
                        'complaint_investigation': report.get('is_complaint_investigation', False),
                        'report_url': report.get('url', '')
                    })

        # Rate limiting
        time.sleep(0.5)

        # Progress checkpoint
        if (i + 1) % 50 == 0:
            print(f"\n--- Progress: {i+1}/{len(high_risk)} facilities checked ---")
            print(f"--- Reports found: {len(all_reports)} ---")
            print(f"--- Facilities with violations: {len(facilities_with_violations)} ---\n")

    # Save results
    if all_reports:
        reports_df = pd.DataFrame(all_reports)
        reports_df.to_csv('inspection_reports_found.csv', index=False)
        print(f"\nSaved {len(reports_df)} inspection reports to 'inspection_reports_found.csv'")

    if facilities_with_violations:
        violations_df = pd.DataFrame(facilities_with_violations)
        violations_df = violations_df.sort_values('risk_score', ascending=False)
        violations_df.to_csv('FACILITIES_WITH_VIOLATIONS.csv', index=False)
        print(f"Saved {len(violations_df)} facilities with violations to 'FACILITIES_WITH_VIOLATIONS.csv'")

        # Print summary
        print(f"\n{'='*60}")
        print("FACILITIES WITH VIOLATIONS FOUND")
        print("="*60)

        type_a_count = violations_df['type_a_violation'].sum()
        type_b_count = violations_df['type_b_violation'].sum()
        complaint_count = violations_df['complaint_investigation'].sum()

        print(f"Total facilities with violations: {len(violations_df)}")
        print(f"Type A violations (most serious): {type_a_count}")
        print(f"Type B violations: {type_b_count}")
        print(f"Complaint investigations: {complaint_count}")

        print(f"\nTop facilities with violations:")
        for _, row in violations_df.head(20).iterrows():
            flags = []
            if row['type_a_violation']:
                flags.append("TYPE A")
            if row['type_b_violation']:
                flags.append("TYPE B")
            if row['complaint_investigation']:
                flags.append("COMPLAINT")

            print(f"\n  {row['facility_name']}")
            print(f"    Licensee: {row['licensee']}")
            print(f"    Risk Score: {row['risk_score']} | Violations: {', '.join(flags)}")
            print(f"    Report: {row['report_url']}")

    # Summary
    print(f"\n{'='*60}")
    print("INSPECTION REPORT ANALYSIS COMPLETE")
    print("="*60)
    print(f"Facilities checked: {len(high_risk)}")
    print(f"Reports found: {len(all_reports)}")
    print(f"Facilities with violations: {len(facilities_with_violations)}")
    print(f"\nOutput files:")
    print(f"  - inspection_reports_found.csv")
    print(f"  - FACILITIES_WITH_VIOLATIONS.csv")


if __name__ == "__main__":
    analyze_high_risk_facilities()
