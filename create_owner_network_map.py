#!/usr/bin/env python3
"""
Create a map showing licensees who operate multiple facilities with fraud flags.
Focuses on suspicious patterns rather than legitimate large operators.
"""

import pandas as pd
import folium
from collections import defaultdict

# Load data
print("Loading high risk facilities data...")
df = pd.read_csv('HIGH_RISK_FACILITIES.csv')

# Normalize licensee names
df['licensee_clean'] = df['licensee'].str.upper().str.strip()

# Known legitimate large operators to exclude
legitimate_large_operators = [
    'LAUSD', 'LOS ANGELES UNIFIED', 'BRIGHT HORIZONS', 'KINDERCARE',
    'YMCA', 'BOYS & GIRLS CLUB', 'HEAD START', 'COMMUNITY CHILD CARE COUNCIL',
    'CHILDREN\'S WORLD', 'LA PETITE', 'CHILDTIME', 'TUTOR TIME',
    'PRIMROSE', 'GODDARD', 'MONTESSORI', 'LEARNING TREE',
    'STATE PRESCHOOL', 'SCHOOL DISTRICT', 'UNIFIED SCHOOL',
    'COUNTY OFFICE OF EDUCATION', 'PTSA', 'PTA'
]

def is_legitimate_operator(name):
    name_upper = str(name).upper()
    for legit in legitimate_large_operators:
        if legit in name_upper:
            return True
    return False

# Filter out legitimate large operators
df_suspicious = df[~df['licensee_clean'].apply(is_legitimate_operator)].copy()

# Group by licensee
licensee_groups = df_suspicious.groupby('licensee_clean').agg({
    'facility_number': 'count',
    'facility_name': list,
    'fraud_score': list,
    'facility_status': list,
    'facility_city': list,
    'facility_address': list,
    'facility_telephone_number': list,
    'county_name': list
}).reset_index()

licensee_groups.columns = ['licensee', 'facility_count', 'names', 'scores',
                           'statuses', 'cities', 'addresses', 'phones', 'counties']

# Filter for licensees with 3+ facilities (suspicious for non-large-operators)
suspicious_licensees = licensee_groups[licensee_groups['facility_count'] >= 3].copy()

# Calculate average risk score
suspicious_licensees['avg_score'] = suspicious_licensees['scores'].apply(lambda x: sum(x)/len(x) if x else 0)

# Sort by facility count and average score
suspicious_licensees = suspicious_licensees.sort_values(['facility_count', 'avg_score'], ascending=[False, False])

print(f"Found {len(suspicious_licensees)} licensees with 3+ facilities (excluding known large operators)")
print(f"Top 10 by facility count:")
for _, row in suspicious_licensees.head(10).iterrows():
    print(f"  {row['licensee']}: {row['facility_count']} facilities, avg score: {row['avg_score']:.1f}")

# Get detailed facility info for mapping
facility_details = df_suspicious[['facility_number', 'facility_name', 'licensee', 'licensee_clean',
                                   'facility_address', 'facility_city', 'facility_zip',
                                   'county_name', 'facility_status', 'facility_capacity',
                                   'license_first_date', 'closed_date', 'fraud_score',
                                   'facility_telephone_number', 'fraud_flags']].copy()

# City coordinates for mapping
city_coords = {
    'LOS ANGELES': (34.0522, -118.2437), 'SAN DIEGO': (32.7157, -117.1611),
    'SAN JOSE': (37.3382, -121.8863), 'SAN FRANCISCO': (37.7749, -122.4194),
    'FRESNO': (36.7378, -119.7871), 'SACRAMENTO': (38.5816, -121.4944),
    'LONG BEACH': (33.7701, -118.1937), 'OAKLAND': (37.8044, -122.2712),
    'BAKERSFIELD': (35.3733, -119.0187), 'ANAHEIM': (33.8366, -117.9143),
    'SANTA ANA': (33.7455, -117.8677), 'RIVERSIDE': (33.9533, -117.3962),
    'STOCKTON': (37.9577, -121.2908), 'IRVINE': (33.6846, -117.8265),
    'CHULA VISTA': (32.6401, -117.0842), 'FREMONT': (37.5485, -121.9886),
    'SAN BERNARDINO': (34.1083, -117.2898), 'MODESTO': (37.6391, -120.9969),
    'FONTANA': (34.0922, -117.4350), 'MORENO VALLEY': (33.9425, -117.2297),
    'GLENDALE': (34.1425, -118.2551), 'HUNTINGTON BEACH': (33.6595, -117.9988),
    'SANTA CLARITA': (34.3917, -118.5426), 'GARDEN GROVE': (33.7739, -117.9414),
    'OCEANSIDE': (33.1959, -117.3795), 'RANCHO CUCAMONGA': (34.1064, -117.5931),
    'ONTARIO': (34.0633, -117.6509), 'SANTA ROSA': (38.4405, -122.7144),
    'ELK GROVE': (38.4088, -121.3716), 'CORONA': (33.8753, -117.5664),
    'LANCASTER': (34.6868, -118.1542), 'PALMDALE': (34.5794, -118.1165),
    'SALINAS': (36.6777, -121.6555), 'POMONA': (34.0551, -117.7500),
    'HAYWARD': (37.6688, -122.0808), 'ESCONDIDO': (33.1192, -117.0864),
    'SUNNYVALE': (37.3688, -122.0363), 'TORRANCE': (33.8358, -118.3406),
    'PASADENA': (34.1478, -118.1445), 'ORANGE': (33.7879, -117.8531),
    'FULLERTON': (33.8703, -117.9242), 'THOUSAND OAKS': (34.1706, -118.8376),
    'ROSEVILLE': (38.7521, -121.2880), 'CONCORD': (37.9780, -122.0311),
    'SIMI VALLEY': (34.2694, -118.7815), 'SANTA CLARA': (37.3541, -121.9552),
    'VICTORVILLE': (34.5362, -117.2928), 'VALLEJO': (38.1041, -122.2566),
    'BERKELEY': (37.8716, -122.2727), 'EL MONTE': (34.0686, -118.0276),
    'DOWNEY': (33.9401, -118.1332), 'COSTA MESA': (33.6412, -117.9187),
    'INGLEWOOD': (33.9617, -118.3531), 'CARLSBAD': (33.1581, -117.3506),
    'FAIRFIELD': (38.2494, -122.0400), 'VENTURA': (34.2746, -119.2290),
    'TEMECULA': (33.4936, -117.1484), 'ANTIOCH': (38.0049, -121.8058),
    'MURRIETA': (33.5539, -117.2139), 'RICHMOND': (37.9358, -122.3478),
    'NORWALK': (33.9022, -118.0817), 'DALY CITY': (37.6879, -122.4702),
    'BURBANK': (34.1808, -118.3090), 'EL CAJON': (32.7948, -116.9625),
    'SOUTH GATE': (33.9547, -118.2120), 'COMPTON': (33.8958, -118.2201),
    'VISTA': (33.2000, -117.2425), 'CARSON': (33.8314, -118.2610),
    'HESPERIA': (34.4264, -117.3009), 'REDDING': (40.5865, -122.3917),
    'WESTMINSTER': (33.7514, -117.9939), 'CHICO': (39.7285, -121.8375),
    'NEWPORT BEACH': (33.6189, -117.9289), 'SAN LEANDRO': (37.7249, -122.1561),
    'SAN MARCOS': (33.1434, -117.1661), 'WHITTIER': (33.9792, -118.0328),
    'HAWTHORNE': (33.9164, -118.3526), 'CITRUS HEIGHTS': (38.7071, -121.2810),
    'ALHAMBRA': (34.0953, -118.1270), 'MENIFEE': (33.6972, -117.1851),
    'HEMET': (33.7476, -116.9719), 'LAKEWOOD': (33.8536, -118.1340),
    'MERCED': (37.3022, -120.4830), 'CHINO': (34.0122, -117.6889),
    'INDIO': (33.7206, -116.2156), 'REDWOOD CITY': (37.4852, -122.2364),
    'LAKE FOREST': (33.6469, -117.6891), 'NAPA': (38.2975, -122.2869),
    'TUSTIN': (33.7458, -117.8261), 'BELLFLOWER': (33.8817, -118.1170),
    'MOUNTAIN VIEW': (37.3861, -122.0839), 'CHINO HILLS': (33.9898, -117.7326),
    'BALDWIN PARK': (34.0854, -117.9609), 'ALAMEDA': (37.7652, -122.2416),
    'UPLAND': (34.0975, -117.6484), 'SAN RAMON': (37.7799, -121.9780),
    'FOLSOM': (38.6780, -121.1761), 'PLEASANTON': (37.6624, -121.8747),
    'LYNWOOD': (33.9303, -118.2115), 'ROSEMEAD': (34.0806, -118.0728)
}

def get_coords(city):
    if pd.isna(city):
        return None
    city_upper = str(city).upper().strip()
    if city_upper in city_coords:
        return city_coords[city_upper]
    return None

# Create map
print("Creating map...")
ca_map = folium.Map(location=[37.5, -119.5], zoom_start=6, tiles='cartodbpositron')

# Colors for different licensee groups
colors = ['#e94560', '#3498db', '#2ecc71', '#9b59b6', '#f39c12',
          '#1abc9c', '#e74c3c', '#34495e', '#16a085', '#d35400']

owner_count = 0
facility_count = 0

# Add markers for top 50 suspicious licensees
for idx, row in suspicious_licensees.head(50).iterrows():
    licensee = row['licensee']
    facilities = facility_details[facility_details['licensee_clean'] == licensee]

    if len(facilities) < 3:
        continue

    color = colors[owner_count % len(colors)]

    # Get coordinates for each facility
    fac_coords = []
    for _, fac in facilities.iterrows():
        coords = get_coords(fac['facility_city'])
        if coords:
            # Add small offset for visualization
            import random
            lat = coords[0] + random.uniform(-0.02, 0.02)
            lng = coords[1] + random.uniform(-0.02, 0.02)
            fac_coords.append((lat, lng, fac))

    if len(fac_coords) < 2:
        continue

    owner_count += 1

    # Add markers and lines
    for lat, lng, fac in fac_coords:
        flags = str(fac.get('fraud_flags', '')).replace(';', ', ').strip(', ')

        popup_html = f"""
        <div style="font-family: Arial; font-size: 12px; min-width: 220px;">
            <b style="color: {color};">{fac['facility_name']}</b><br>
            <b>Licensee:</b> {fac['licensee']}<br>
            <b>Address:</b> {fac['facility_address']}, {fac['facility_city']}<br>
            <b>Status:</b> {fac['facility_status']}<br>
            <b>Risk Score:</b> {fac['fraud_score']}<br>
            <b>Phone:</b> {fac['facility_telephone_number']}<br>
            <b>Flags:</b> {flags if flags else 'None'}<br>
            <hr style="margin: 5px 0;">
            <span style="color: {color}; font-weight: bold;">
                This licensee operates {len(facilities)} facilities
            </span>
        </div>
        """

        folium.CircleMarker(
            location=[lat, lng],
            radius=8 + min(len(facilities), 10),  # Larger radius for more facilities
            color=color,
            fill=True,
            fillColor=color,
            fillOpacity=0.7,
            popup=folium.Popup(popup_html, max_width=300)
        ).add_to(ca_map)

        facility_count += 1

    # Draw lines connecting facilities of same licensee
    if len(fac_coords) >= 2:
        coords_only = [(lat, lng) for lat, lng, _ in fac_coords]
        # Connect all points
        for i in range(len(coords_only)):
            for j in range(i + 1, len(coords_only)):
                folium.PolyLine(
                    locations=[coords_only[i], coords_only[j]],
                    color=color,
                    weight=2,
                    opacity=0.5,
                    dash_array='5, 5'
                ).add_to(ca_map)

print(f"Added {facility_count} facilities from {owner_count} suspicious licensees")

# Add header
header_html = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
.site-nav {{
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
}}
.nav-links {{
    display: flex;
    gap: 15px;
    flex-wrap: wrap;
    justify-content: center;
}}
.nav-links a {{
    padding: 12px 28px;
    border-radius: 8px;
    text-decoration: none;
    font-weight: 600;
    font-size: 15px;
    transition: all 0.2s;
}}
.nav-links a.active {{
    background: #e94560;
    color: white;
}}
.nav-links a:not(.active) {{
    background: rgba(255,255,255,0.1);
    color: white;
}}
.nav-links a:hover:not(.active) {{
    background: rgba(255,255,255,0.2);
}}
@media (max-width: 768px) {{
    .site-nav {{ padding: 12px 15px; }}
    .nav-links {{ gap: 8px; }}
    .nav-links a {{ padding: 10px 16px; font-size: 13px; }}
}}
@media (max-width: 480px) {{
    .site-nav {{ padding: 10px 10px; }}
    .nav-links {{ gap: 5px; }}
    .nav-links a {{ padding: 8px 12px; font-size: 11px; }}
}}
.info-panel {{
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
}}
.info-panel h3 {{
    margin: 0 0 12px 0;
    font-size: 16px;
    color: #fff;
}}
.info-panel p {{
    margin: 0 0 10px 0;
    font-size: 12px;
    line-height: 1.5;
}}
.info-panel .highlight {{
    color: #e94560;
    font-weight: 600;
}}
.info-panel .stats-row {{
    display: flex;
    gap: 15px;
    margin: 12px 0;
    padding: 10px;
    background: rgba(255,255,255,0.05);
    border-radius: 6px;
}}
.info-panel .stat {{
    text-align: center;
    flex: 1;
}}
.info-panel .stat-value {{
    font-size: 20px;
    font-weight: 700;
    color: #fff;
}}
.info-panel .stat-label {{
    font-size: 10px;
    color: #8b949e;
}}
.toggle-btn {{
    position: absolute;
    top: 10px;
    right: 10px;
    background: none;
    border: none;
    color: #8b949e;
    cursor: pointer;
    font-size: 14px;
}}
.info-panel.collapsed .panel-content {{ display: none; }}
.info-panel.collapsed {{ padding: 12px 16px; }}
@media (max-width: 768px) {{
    .info-panel {{ top: auto; bottom: 20px; left: 10px; right: 10px; max-width: none; }}
}}
</style>

<nav class="site-nav">
    <div class="nav-links">
        <a href="daycare-investigation.html">Daycare Investigation</a>
        <a href="phone-network-map.html">Phone Networks</a>
        <a href="address-network-map.html">Address Networks</a>
        <a href="owner-network-map.html" class="active">Owner Networks</a>
        <a href="ppp-norcal.html">PPP NorCal</a>
        <a href="ppp-socal.html">PPP SoCal</a>
        <a href="resources.html">Resources</a>
    </div>
</nav>

<div class="info-panel" id="infoPanel">
    <button class="toggle-btn" onclick="document.getElementById('infoPanel').classList.toggle('collapsed'); this.textContent = this.textContent === '−' ? '+' : '−';">−</button>
    <h3>👤 Multi-Facility Licensee Analysis</h3>
    <div class="panel-content">
        <p>This map shows <span class="highlight">individuals or entities operating 3+ childcare facilities</span> (excluding known legitimate large operators like school districts and national chains).</p>

        <div class="stats-row">
            <div class="stat">
                <div class="stat-value">{owner_count}</div>
                <div class="stat-label">Licensee Networks</div>
            </div>
            <div class="stat">
                <div class="stat-value">{facility_count}</div>
                <div class="stat-label">Facilities</div>
            </div>
        </div>

        <p><strong>Why This Matters:</strong></p>
        <p style="margin-left: 10px; font-size: 11px;">
            • Multiple facilities = potential for coordinated fraud<br>
            • Same person controlling many sites can inflate claims<br>
            • Pattern seen in Feeding Our Future case
        </p>

        <p style="margin-top: 10px; font-size: 11px; color: #8b949e;">
            <strong>Note:</strong> Lines connect facilities operated by the same licensee. Larger circles indicate more facilities.
        </p>
    </div>
</div>
"""

ca_map.get_root().html.add_child(folium.Element(header_html))

# Map positioning CSS
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
ca_map.save('owner-network-map.html')
print("Done! Created owner-network-map.html")
