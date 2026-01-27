#!/usr/bin/env python3
"""
Create a network map showing connections between daycare facilities
that share the same phone number - a key fraud indicator.
"""

import pandas as pd
import folium
from folium import plugins
import json
import html
from collections import defaultdict
import random

print("Loading duplicate phone facilities data...")
df = pd.read_csv('DUPLICATE_PHONE_FACILITIES.csv')
print(f"Loaded {len(df)} facility records")

# Load zip code coordinates for geocoding
print("Loading zip code coordinates...")
zip_coords = pd.read_csv(
    '/Users/corygoat/Desktop/PPP Loans/2023_Gaz_zcta_national.txt',
    sep='\t',
    dtype={'GEOID': str}
)
zip_coords.columns = zip_coords.columns.str.strip()
zip_coords = zip_coords[['GEOID', 'INTPTLAT', 'INTPTLONG']].copy()
zip_coords.columns = ['zip', 'lat', 'lng']
zip_coords['zip'] = zip_coords['zip'].str.strip()
zip_dict = dict(zip(zip_coords['zip'], zip(zip_coords['lat'], zip_coords['lng'])))
print(f"Loaded {len(zip_dict)} zip code coordinates")

# Clean zip codes and add coordinates
df['zip_clean'] = df['facility_zip'].astype(str).str[:5]
df['lat'] = df['zip_clean'].map(lambda z: zip_dict.get(z, (None, None))[0])
df['lng'] = df['zip_clean'].map(lambda z: zip_dict.get(z, (None, None))[1])

# Filter to facilities with valid coordinates
df_valid = df.dropna(subset=['lat', 'lng']).copy()
print(f"Facilities with valid coordinates: {len(df_valid)}")

# Add small random offset to prevent overlapping markers at same location
def add_jitter(val, amount=0.002):
    return val + random.uniform(-amount, amount)

df_valid['lat_jitter'] = df_valid['lat'].apply(lambda x: add_jitter(x))
df_valid['lng_jitter'] = df_valid['lng'].apply(lambda x: add_jitter(x))

# Group by phone number
phone_groups = df_valid.groupby('phone_clean').apply(lambda x: x.to_dict('records')).to_dict()
print(f"Found {len(phone_groups)} unique phone numbers with multiple facilities")

# Filter to only phone numbers with 2+ facilities at different locations
network_groups = {}
for phone, facilities in phone_groups.items():
    if len(facilities) >= 2:
        # Check if there are different zip codes (indicating different locations)
        zips = set(f['zip_clean'] for f in facilities)
        if len(zips) >= 2 or len(facilities) >= 3:  # Different locations OR 3+ at same location
            network_groups[phone] = facilities

print(f"Phone numbers with network connections: {len(network_groups)}")

# Calculate statistics
total_facilities_in_networks = sum(len(f) for f in network_groups.values())
print(f"Total facilities in phone networks: {total_facilities_in_networks}")

# Create the map
print("\nCreating network map...")
ca_map = folium.Map(
    location=[37.5, -119.5],
    zoom_start=6,
    tiles='cartodbpositron'
)

# Color palette for different phone networks
colors = [
    '#e94560', '#f39c12', '#9b59b6', '#3498db', '#1abc9c',
    '#e74c3c', '#2ecc71', '#f1c40f', '#8e44ad', '#16a085',
    '#d35400', '#c0392b', '#27ae60', '#2980b9', '#8e44ad'
]

# Add polylines and markers for each phone network
network_id = 0
all_markers = []

for phone, facilities in network_groups.items():
    color = colors[network_id % len(colors)]
    network_id += 1

    # Get unique locations (by zip)
    locations_by_zip = defaultdict(list)
    for f in facilities:
        locations_by_zip[f['zip_clean']].append(f)

    unique_locations = []
    for zip_code, zip_facilities in locations_by_zip.items():
        # Use first facility's coordinates for this zip
        f = zip_facilities[0]
        unique_locations.append({
            'lat': f['lat_jitter'],
            'lng': f['lng_jitter'],
            'facilities': zip_facilities,
            'zip': zip_code
        })

    # Draw lines between all locations sharing this phone
    if len(unique_locations) >= 2:
        for i in range(len(unique_locations)):
            for j in range(i + 1, len(unique_locations)):
                loc1 = unique_locations[i]
                loc2 = unique_locations[j]

                # Draw polyline
                folium.PolyLine(
                    locations=[
                        [loc1['lat'], loc1['lng']],
                        [loc2['lat'], loc2['lng']]
                    ],
                    color=color,
                    weight=3,
                    opacity=0.7,
                    dash_array='10, 5'
                ).add_to(ca_map)

    # Add markers for each location
    for loc in unique_locations:
        facilities_at_loc = loc['facilities']

        # Build popup content
        phone_formatted = facilities_at_loc[0]['facility_telephone_number']
        facility_count = len(facilities_at_loc)
        network_size = len(facilities)

        popup_html = f'''
        <div style="font-family: 'Inter', sans-serif; width: 320px; background: #0d1117; color: #c9d1d9; border-radius: 8px; overflow: hidden;">
            <div style="background: linear-gradient(90deg, {color}, {color}88); padding: 12px; border-bottom: 2px solid {color};">
                <div style="font-size: 14px; font-weight: 700; color: #fff;">Phone Network Cluster</div>
                <div style="font-size: 20px; font-weight: 700; color: #fff; margin-top: 4px;">{phone_formatted}</div>
            </div>
            <div style="padding: 12px; background: rgba(0,0,0,0.2);">
                <div style="display: flex; gap: 10px; margin-bottom: 10px;">
                    <div style="flex: 1; background: rgba(255,255,255,0.05); border-radius: 6px; padding: 8px; text-align: center;">
                        <div style="font-size: 9px; color: #8b949e;">At This Location</div>
                        <div style="font-size: 18px; font-weight: 700; color: {color};">{facility_count}</div>
                    </div>
                    <div style="flex: 1; background: rgba(255,255,255,0.05); border-radius: 6px; padding: 8px; text-align: center;">
                        <div style="font-size: 9px; color: #8b949e;">Total In Network</div>
                        <div style="font-size: 18px; font-weight: 700; color: #58a6ff;">{network_size}</div>
                    </div>
                </div>
                <div style="font-size: 10px; color: #8b949e; margin-bottom: 6px;">FACILITIES AT THIS LOCATION:</div>
        '''

        for f in facilities_at_loc[:5]:
            name = html.escape(str(f['facility_name'])[:40])
            status = f['facility_status']
            status_color = '#f85149' if status == 'CLOSED' else '#3fb950'
            risk = f['risk_score']
            risk_color = '#f85149' if risk >= 8 else '#fd7e14' if risk >= 6 else '#ffc107' if risk >= 4 else '#3fb950'

            popup_html += f'''
                <div style="background: rgba(255,255,255,0.03); border-radius: 4px; padding: 8px; margin-bottom: 6px;">
                    <div style="font-size: 11px; font-weight: 600; color: #fff; margin-bottom: 4px;">{name}</div>
                    <div style="display: flex; gap: 8px; font-size: 10px;">
                        <span style="color: {status_color};">{status}</span>
                        <span style="color: #8b949e;">Risk: <span style="color: {risk_color}; font-weight: 600;">{risk}</span></span>
                        <span style="color: #8b949e;">{f['facility_city']}</span>
                    </div>
                </div>
            '''

        if len(facilities_at_loc) > 5:
            popup_html += f'<div style="font-size: 10px; color: #8b949e; padding: 4px 0;">+ {len(facilities_at_loc) - 5} more facilities...</div>'

        popup_html += '''
            </div>
            <div style="background: rgba(248,81,73,0.1); padding: 8px 12px; font-size: 10px; color: #f85149;">
                ⚠️ Multiple facilities sharing one phone number is a fraud indicator
            </div>
        </div>
        '''

        # Add marker
        folium.CircleMarker(
            location=[loc['lat'], loc['lng']],
            radius=8 + (facility_count * 2),
            popup=folium.Popup(popup_html, max_width=340),
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.8,
            weight=2
        ).add_to(ca_map)

# Add header with legend
header_html = '''
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
.network-header {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    z-index: 9999;
    background: linear-gradient(135deg, #0d1117 0%, #161b22 50%, #21262d 100%);
    padding: 12px 20px;
    font-family: 'Inter', sans-serif;
    box-shadow: 0 4px 20px rgba(0,0,0,0.5);
    border-bottom: 3px solid #9b59b6;
}
.header-content {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 15px;
}
.brand {
    display: flex;
    align-items: center;
    gap: 12px;
}
.brand-logo {
    width: 40px;
    height: 40px;
    background: linear-gradient(135deg, #9b59b6, #8e44ad);
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
}
.brand h1 {
    margin: 0;
    font-size: 18px;
    font-weight: 700;
    color: #fff;
}
.brand .tagline {
    font-size: 11px;
    color: #8b949e;
}
.nav-links {
    display: flex;
    gap: 8px;
}
.nav-links a {
    padding: 8px 16px;
    border-radius: 5px;
    text-decoration: none;
    font-weight: 500;
    font-size: 13px;
    background: rgba(255,255,255,0.1);
    color: white;
    transition: all 0.2s;
}
.nav-links a:hover {
    background: rgba(255,255,255,0.2);
}
.nav-links a.active {
    background: #9b59b6;
}
.stats {
    display: flex;
    gap: 15px;
}
.stat {
    text-align: center;
}
.stat-value {
    font-size: 20px;
    font-weight: 700;
    color: #fff;
}
.stat-label {
    font-size: 10px;
    color: #8b949e;
}
.legend-bar {
    display: flex;
    align-items: center;
    gap: 20px;
    padding: 8px 20px;
    background: rgba(0,0,0,0.3);
    font-size: 11px;
    color: #8b949e;
}
@media (max-width: 768px) {
    .network-header { padding: 10px 12px; }
    .header-content { gap: 10px; }
    .brand h1 { font-size: 14px; }
    .brand .tagline { display: none; }
    .brand-logo { width: 32px; height: 32px; font-size: 16px; }
    .nav-links a { padding: 6px 10px; font-size: 11px; }
    .stats { gap: 10px; }
    .stat-value { font-size: 16px; }
    .stat-label { font-size: 9px; }
    .legend-bar { flex-wrap: wrap; gap: 10px; padding: 6px 12px; font-size: 10px; }
}
@media (max-width: 480px) {
    .brand h1 { font-size: 12px; }
    .nav-links a { padding: 5px 8px; font-size: 10px; }
    .stat-value { font-size: 14px; }
}
</style>

<div class="network-header">
    <div class="header-content">
        <div class="brand">
            <div class="brand-logo">🔗</div>
            <div>
                <h1>Phone Network Analysis</h1>
                <div class="tagline">Daycare Facilities Sharing Phone Numbers</div>
            </div>
        </div>
        <div class="nav-links">
            <a href="daycare-investigation.html">Daycare Investigation</a>
            <a href="phone-network-map.html" class="active">Phone Networks</a>
            <a href="ppp-norcal.html">PPP NorCal</a>
            <a href="ppp-socal.html">PPP SoCal</a>
        </div>
        <div class="stats">
            <div class="stat">
                <div class="stat-value">''' + str(len(network_groups)) + '''</div>
                <div class="stat-label">Phone Networks</div>
            </div>
            <div class="stat">
                <div class="stat-value">''' + str(total_facilities_in_networks) + '''</div>
                <div class="stat-label">Facilities</div>
            </div>
        </div>
    </div>
    <div class="legend-bar">
        <span>📞 Lines connect facilities sharing the same phone number</span>
        <span>⚠️ Shared phones are a key fraud indicator from the Feeding Our Future case</span>
    </div>
</div>
'''

map_style = '''
<style>
.folium-map {
    position: fixed !important;
    top: 95px !important;
    bottom: 0 !important;
    left: 0 !important;
    right: 0 !important;
    height: auto !important;
}
@media (max-width: 768px) {
    .folium-map { top: 110px !important; }
}
@media (max-width: 480px) {
    .folium-map { top: 105px !important; }
}
.leaflet-popup-content-wrapper {
    max-width: 90vw !important;
}
.leaflet-popup-content {
    margin: 8px !important;
}
</style>
'''

ca_map.get_root().html.add_child(folium.Element(header_html))
ca_map.get_root().html.add_child(folium.Element(map_style))

# Save the map
output_path = 'phone-network-map.html'
ca_map.save(output_path)
print(f"\nMap saved to: {output_path}")

import os
file_size = os.path.getsize(output_path) / (1024 * 1024)
print(f"File size: {file_size:.1f} MB")
