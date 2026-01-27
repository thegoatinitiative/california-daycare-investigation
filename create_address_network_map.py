#!/usr/bin/env python3
"""
Create a map showing facilities that share the same physical address.
Similar to phone network map but for addresses.
"""

import pandas as pd
import folium
from collections import defaultdict
import re

# Load data
print("Loading duplicate address data...")
df = pd.read_csv('fraud_flag_duplicate_addresses.csv')

# Normalize addresses for grouping
df['address_key'] = df['address_normalized'].str.upper().str.strip()

# Group by normalized address
address_groups = df.groupby('address_key').agg({
    'facility_name': 'count',
    'facility_number': list,
    'licensee': list,
    'facility_city': 'first',
    'facility_zip': 'first',
    'county_name': 'first',
    'facility_status': list,
    'facility_capacity': list,
    'facility_address': 'first',
    'facility_telephone_number': list
}).reset_index()

address_groups.columns = ['address_key', 'facility_count', 'facility_numbers', 'licensees',
                          'city', 'zip_code', 'county', 'statuses', 'capacities',
                          'address', 'phones']

# Filter for addresses with 2+ facilities AND different licensees (more suspicious)
suspicious_addresses = address_groups[address_groups['facility_count'] >= 2].copy()

# Check if licensees are different (more suspicious than same licensee at same address)
def has_different_licensees(licensees):
    unique = set([l.upper().strip() for l in licensees if pd.notna(l)])
    return len(unique) > 1

suspicious_addresses['different_licensees'] = suspicious_addresses['licensees'].apply(has_different_licensees)

# Filter for addresses with different licensees (most suspicious)
most_suspicious = suspicious_addresses[suspicious_addresses['different_licensees']].copy()

print(f"Total addresses with 2+ facilities: {len(suspicious_addresses)}")
print(f"Addresses with DIFFERENT licensees: {len(most_suspicious)}")

# Get facility details for mapping
facility_details = df[['facility_number', 'facility_name', 'licensee', 'facility_address',
                       'facility_city', 'facility_zip', 'county_name', 'facility_status',
                       'facility_capacity', 'license_first_date', 'closed_date',
                       'facility_telephone_number', 'fraud_score', 'address_key']].copy()

# Load coordinates from the high risk facilities or raw data
print("Loading coordinates...")
try:
    coords_df = pd.read_csv('HIGH_RISK_FACILITIES.csv')
    # Check if lat/lng columns exist
    if 'latitude' in coords_df.columns:
        coords = coords_df[['facility_number', 'latitude', 'longitude']].drop_duplicates()
        facility_details = facility_details.merge(coords, on='facility_number', how='left')
except:
    pass

# If no coords, use zip code centroids
if 'latitude' not in facility_details.columns or facility_details['latitude'].isna().all():
    print("Using zip code centroids for coordinates...")
    # California zip code centroids (approximate)
    zip_coords = {
        '90001': (33.9425, -118.2551), '90002': (33.9490, -118.2470),
        '90210': (34.0901, -118.4065), '91101': (34.1478, -118.1445),
        '92101': (32.7157, -117.1611), '94102': (37.7749, -122.4194),
        '95814': (38.5816, -121.4944),
    }
    # For simplicity, use city-based approximate coords
    city_coords = {
        'LOS ANGELES': (34.0522, -118.2437), 'SAN DIEGO': (32.7157, -117.1611),
        'SAN JOSE': (37.3382, -121.8863), 'SAN FRANCISCO': (37.7749, -122.4194),
        'FRESNO': (36.7378, -119.7871), 'SACRAMENTO': (38.5816, -121.4944),
        'LONG BEACH': (33.7701, -118.1937), 'OAKLAND': (37.8044, -122.2712),
        'BAKERSFIELD': (35.3733, -119.0187), 'ANAHEIM': (33.8366, -117.9143),
    }

    def get_coords(row):
        city = str(row['facility_city']).upper() if pd.notna(row['facility_city']) else ''
        if city in city_coords:
            return city_coords[city]
        # Default to LA
        return (34.0522, -118.2437)

    facility_details['coords'] = facility_details.apply(get_coords, axis=1)
    facility_details['latitude'] = facility_details['coords'].apply(lambda x: x[0])
    facility_details['longitude'] = facility_details['coords'].apply(lambda x: x[1])

# Create map
print("Creating map...")
ca_map = folium.Map(location=[37.5, -119.5], zoom_start=6, tiles='cartodbpositron')

# Color palette for different address groups
colors = ['#e94560', '#3498db', '#2ecc71', '#9b59b6', '#f39c12', '#1abc9c', '#e74c3c', '#34495e']

# Add markers and lines for suspicious addresses
address_count = 0
facility_count = 0

for idx, row in most_suspicious.head(100).iterrows():  # Limit to top 100 most suspicious
    address_key = row['address_key']
    facilities = facility_details[facility_details['address_key'] == address_key]

    if len(facilities) < 2:
        continue

    color = colors[address_count % len(colors)]
    address_count += 1

    # Add markers for each facility
    coords_list = []
    for _, fac in facilities.iterrows():
        lat = fac.get('latitude')
        lng = fac.get('longitude')

        if pd.isna(lat) or pd.isna(lng):
            continue

        # Add small random offset so markers don't overlap
        import random
        lat += random.uniform(-0.001, 0.001)
        lng += random.uniform(-0.001, 0.001)

        coords_list.append((lat, lng))

        popup_html = f"""
        <div style="font-family: Arial; font-size: 12px; min-width: 200px;">
            <b style="color: {color};">{fac['facility_name']}</b><br>
            <b>Licensee:</b> {fac['licensee']}<br>
            <b>Address:</b> {fac['facility_address']}, {fac['facility_city']}<br>
            <b>Status:</b> {fac['facility_status']}<br>
            <b>Capacity:</b> {fac['facility_capacity']}<br>
            <b>Phone:</b> {fac['facility_telephone_number']}<br>
            <b>Licensed:</b> {fac['license_first_date']}<br>
            <hr style="margin: 5px 0;">
            <span style="color: #e94560; font-weight: bold;">
                {len(facilities)} facilities at this address
            </span>
        </div>
        """

        folium.CircleMarker(
            location=[lat, lng],
            radius=10,
            color=color,
            fill=True,
            fillColor=color,
            fillOpacity=0.8,
            popup=folium.Popup(popup_html, max_width=300)
        ).add_to(ca_map)

        facility_count += 1

print(f"Added {facility_count} facilities from {address_count} suspicious address groups")

# Add custom header
header_html = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
.site-nav {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    z-index: 9999;
    background: linear-gradient(135deg, #0d1117 0%, #161b22 50%, #21262d 100%);
    padding: 15px 20px;
    font-family: 'Inter', sans-serif;
    box-shadow: 0 4px 20px rgba(0,0,0,0.5);
    border-bottom: 3px solid #e94560;
    display: flex;
    justify-content: center;
    align-items: center;
}
.nav-links {
    display: flex;
    gap: 15px;
}
.nav-links a {
    padding: 12px 28px;
    border-radius: 8px;
    text-decoration: none;
    font-weight: 600;
    font-size: 15px;
    transition: all 0.2s;
}
.nav-links a.active {
    background: #e94560;
    color: white;
}
.nav-links a:not(.active) {
    background: rgba(255,255,255,0.1);
    color: white;
}
.nav-links a:hover:not(.active) {
    background: rgba(255,255,255,0.2);
}
@media (max-width: 768px) {
    .site-nav { padding: 12px 15px; }
    .nav-links { gap: 8px; }
    .nav-links a { padding: 10px 16px; font-size: 13px; }
}
@media (max-width: 480px) {
    .site-nav { padding: 10px 10px; }
    .nav-links { gap: 5px; }
    .nav-links a { padding: 8px 12px; font-size: 11px; }
}
.info-panel {
    position: fixed;
    top: 75px;
    left: 20px;
    z-index: 9998;
    background: rgba(22,27,34,0.95);
    border-radius: 10px;
    padding: 16px 20px;
    font-family: 'Inter', sans-serif;
    color: #c9d1d9;
    box-shadow: 0 4px 20px rgba(0,0,0,0.4);
    max-width: 340px;
    border: 1px solid rgba(255,255,255,0.1);
}
.info-panel h3 {
    margin: 0 0 12px 0;
    font-size: 16px;
    color: #fff;
}
.info-panel p {
    margin: 0 0 10px 0;
    font-size: 12px;
    line-height: 1.5;
}
.info-panel .highlight {
    color: #e94560;
    font-weight: 600;
}
.info-panel .stats-row {
    display: flex;
    gap: 15px;
    margin: 12px 0;
    padding: 10px;
    background: rgba(255,255,255,0.05);
    border-radius: 6px;
}
.info-panel .stat {
    text-align: center;
    flex: 1;
}
.info-panel .stat-value {
    font-size: 20px;
    font-weight: 700;
    color: #fff;
}
.info-panel .stat-label {
    font-size: 10px;
    color: #8b949e;
}
.toggle-btn {
    position: absolute;
    top: 10px;
    right: 10px;
    background: none;
    border: none;
    color: #8b949e;
    cursor: pointer;
    font-size: 14px;
}
.info-panel.collapsed .panel-content { display: none; }
.info-panel.collapsed { padding: 12px 16px; }
@media (max-width: 768px) {
    .info-panel { top: auto; bottom: 20px; left: 10px; right: 10px; max-width: none; }
}
</style>

<nav class="site-nav">
    <div class="nav-links">
        <a href="daycare-investigation.html">Daycare Investigation</a>
        <a href="phone-network-map.html">Phone Networks</a>
        <a href="address-network-map.html" class="active">Address Networks</a>
        <a href="ppp-norcal.html">PPP NorCal</a>
        <a href="ppp-socal.html">PPP SoCal</a>
    </div>
</nav>

<div class="info-panel" id="infoPanel">
    <button class="toggle-btn" onclick="document.getElementById('infoPanel').classList.toggle('collapsed'); this.textContent = this.textContent === '−' ? '+' : '−';">−</button>
    <h3>🏠 Shared Address Analysis</h3>
    <div class="panel-content">
        <p>This map shows <span class="highlight">multiple daycare facilities registered at the same physical address</span> with different licensees.</p>

        <div class="stats-row">
            <div class="stat">
                <div class="stat-value">""" + str(address_count) + """</div>
                <div class="stat-label">Address Clusters</div>
            </div>
            <div class="stat">
                <div class="stat-value">""" + str(facility_count) + """</div>
                <div class="stat-label">Facilities</div>
            </div>
        </div>

        <p><strong>Why This Matters:</strong></p>
        <p style="margin-left: 10px; font-size: 11px;">
            • Multiple licenses at same address = potential shell facilities<br>
            • Different licensees at same address = possible coordinated fraud<br>
            • Can indicate fictitious businesses or capacity inflation
        </p>

        <p style="margin-top: 10px; font-size: 11px; color: #8b949e;">
            <strong>Note:</strong> Some shared addresses are legitimate (e.g., multi-suite buildings). Click markers for details.
        </p>
    </div>
</div>
"""

# Add to map
ca_map.get_root().html.add_child(folium.Element(header_html))

# Add CSS for map positioning
map_css = """
<style>
.folium-map {
    position: fixed !important;
    top: 65px !important;
    bottom: 0 !important;
    left: 0 !important;
    right: 0 !important;
    height: auto !important;
}
@media (max-width: 768px) {
    .folium-map { top: 58px !important; }
}
@media (max-width: 480px) {
    .folium-map { top: 52px !important; }
}
</style>
"""
ca_map.get_root().html.add_child(folium.Element(map_css))

# Save
print("Saving map...")
ca_map.save('address-network-map.html')
print("Done! Created address-network-map.html")
