#!/usr/bin/env python3
"""
Fetch CACFP (Child and Adult Care Food Program) participating sites from California
and cross-reference with flagged daycare facilities.

CACFP provides meal reimbursements to daycares - this was the program exploited
in the $250M Feeding Our Future fraud case in Minnesota.
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
from difflib import SequenceMatcher

# California counties
CA_COUNTIES = [
    "Alameda", "Alpine", "Amador", "Butte", "Calaveras", "Colusa", "Contra Costa",
    "Del Norte", "El Dorado", "Fresno", "Glenn", "Humboldt", "Imperial", "Inyo",
    "Kern", "Kings", "Lake", "Lassen", "Los Angeles", "Madera", "Marin", "Mariposa",
    "Mendocino", "Merced", "Modoc", "Mono", "Monterey", "Napa", "Nevada", "Orange",
    "Placer", "Plumas", "Riverside", "Sacramento", "San Benito", "San Bernardino",
    "San Diego", "San Francisco", "San Joaquin", "San Luis Obispo", "San Mateo",
    "Santa Barbara", "Santa Clara", "Santa Cruz", "Shasta", "Sierra", "Siskiyou",
    "Solano", "Sonoma", "Stanislaus", "Sutter", "Tehama", "Trinity", "Tulare",
    "Tuolumne", "Ventura", "Yolo", "Yuba"
]

def fetch_county_cacfp(county_name):
    """Fetch CACFP sites for a single county"""
    url = f"https://cacfp.dss.ca.gov/Centers/PartialCounty?countyName={county_name.replace(' ', '+')}"

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        sites = []

        # Find all site entries - the page structure uses cards or divs for each sponsor
        # Parse the content to extract facility information
        content = soup.get_text()

        # The page lists sponsors and their sites
        # We need to parse the structure

        # Look for address patterns and facility names
        # This is a simplified approach - may need refinement based on actual HTML structure

        cards = soup.find_all(['div', 'section'], class_=lambda x: x and ('card' in str(x).lower() or 'site' in str(x).lower() or 'facility' in str(x).lower()))

        if not cards:
            # Try finding any structured content
            cards = soup.find_all('div', class_=True)

        # Extract text content that looks like addresses
        address_pattern = r'(\d+\s+[\w\s]+(?:Street|St|Avenue|Ave|Boulevard|Blvd|Road|Rd|Drive|Dr|Lane|Ln|Way|Court|Ct)[\w\s,]*(?:CA|California)\s*\d{5})'

        addresses_found = re.findall(address_pattern, content, re.IGNORECASE)

        return {
            'county': county_name,
            'url': url,
            'addresses_found': len(addresses_found),
            'raw_text_length': len(content)
        }

    except Exception as e:
        print(f"  Error fetching {county_name}: {e}")
        return {'county': county_name, 'error': str(e)}

def normalize_name(name):
    """Normalize facility name for matching"""
    if not name:
        return ''
    name = str(name).upper().strip()
    # Remove common suffixes
    name = re.sub(r'\s*(LLC|INC|CORP|L\.L\.C\.|INCORPORATED|CORPORATION)\s*$', '', name)
    # Remove punctuation
    name = re.sub(r'[^\w\s]', '', name)
    # Normalize whitespace
    name = re.sub(r'\s+', ' ', name).strip()
    return name

def name_similarity(name1, name2):
    """Calculate similarity between two names"""
    n1 = normalize_name(name1)
    n2 = normalize_name(name2)
    return SequenceMatcher(None, n1, n2).ratio()

print("Loading flagged daycare facilities...")
# Load high-risk facilities
high_risk = pd.read_csv('HIGH_RISK_FACILITIES.csv')
print(f"Loaded {len(high_risk)} flagged facilities")

# Show columns
print(f"Columns: {list(high_risk.columns)[:10]}")

print("\nSample of flagged facilities:")
if 'facility_name' in high_risk.columns:
    name_col = 'facility_name'
elif 'FACILITY_NAME' in high_risk.columns:
    name_col = 'FACILITY_NAME'
else:
    name_col = high_risk.columns[0]

print(high_risk[name_col].head(10).tolist())

print("\n" + "="*60)
print("CACFP DATA SOURCES")
print("="*60)
print("""
To cross-reference flagged daycares with CACFP participants, you can:

1. MANUAL CHECK: Visit the CACFP site search
   https://cacfp.dss.ca.gov/Centers/Search

2. COUNTY LISTS: Browse by county
   https://cacfp.dss.ca.gov/Centers/PartialCounty?countyName=Los+Angeles
   (Replace county name as needed)

3. DATA REQUEST: Contact CDSS for bulk data
   Email: cacfpinfo@dss.ca.gov
   Phone: (833) 559-2418

4. PUBLIC RECORDS REQUEST: File a request for CACFP participant list
   https://www.cdss.ca.gov/inforesources/public-records-request
""")

# Test fetching one county
print("\nTesting fetch for San Francisco County...")
result = fetch_county_cacfp("San Francisco")
print(f"Result: {result}")

print("\n" + "="*60)
print("IMPORTANT FRAUD INDICATORS")
print("="*60)
print("""
Facilities receiving CACFP reimbursements + having these flags = HIGH PRIORITY:

1. SHORT-LIVED FACILITIES - Opened and closed quickly (pop-up fraud)
2. NO CHILDREN PRESENT - Claiming reimbursements for non-existent children
3. DUPLICATE PHONE NUMBERS - Multiple facilities controlled by same person
4. COVID-ERA LICENSES - Opened during reduced oversight period
5. PPP LOANS - Double-dipping federal funds

The Feeding Our Future case showed fraudsters:
- Created fake daycares
- Claimed meal reimbursements for children who didn't exist
- Submitted false invoices
- Used shell companies to launder money
""")
