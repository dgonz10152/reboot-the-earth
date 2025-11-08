import pandas as pd
import requests
import urllib.request
import urllib.parse
import urllib.error
import json
import time
import traceback

county_gdp_map = {
    'Alameda':        110_000_000_000,
    'Alpine':         200_000_000,
    'Amador':         1_500_000_000,
    'Butte':          12_000_000_000,
    'Calaveras':      2_000_000_000,
    'Colusa':         1_200_000_000,
    'Contra Costa':   90_000_000_000,
    'Del Norte':      1_000_000_000,
    'El Dorado':      12_000_000_000,
    'Fresno':         45_000_000_000,
    'Glenn':          1_000_000_000,
    'Humboldt':       6_000_000_000,
    'Imperial':       7_000_000_000,
    'Inyo':           900_000_000,
    'Kern':           60_000_000_000,
    'Kings':          6_000_000_000,
    'Lake':           3_000_000_000,
    'Lassen':         1_000_000_000,
    'Los Angeles':   1_200_000_000_000,
    'Madera':         7_000_000_000,
    'Marin':          30_000_000_000,
    'Mariposa':       1_000_000_000,
    'Mendocino':      4_000_000_000,
    'Merced':         8_000_000_000,
    'Modoc':          500_000_000,
    'Mono':           1_500_000_000,
    'Monterey':       25_000_000_000,
    'Napa':           20_000_000_000,
    'Nevada':         5_000_000_000,
    'Orange':        400_000_000_000,
    'Placer':         20_000_000_000,
    'Plumas':         1_000_000_000,
    'Riverside':      130_000_000_000,
    'Sacramento':     150_000_000_000,
    'San Benito':     3_000_000_000,
    'San Bernardino': 220_000_000_000,
    'San Diego':      400_000_000_000,
    'San Francisco':  500_000_000_000,
    'San Joaquin':    35_000_000_000,
    'San Luis Obispo':20_000_000_000,
    'San Mateo':     160_000_000_000,
    'Santa Barbara':  35_000_000_000,
    'Santa Clara':   400_000_000_000,
    'Santa Cruz':     8_700_000_000,
    'Shasta':         7_000_000_000,
    'Sierra':         500_000_000,
    'Siskiyou':       2_000_000_000,
    'Solano':         35_000_000_000,
    'Sonoma':         45_000_000_000,
    'Stanislaus':     25_000_000_000,
    'Sutter':         4_000_000_000,
    'Tehama':         2_000_000_000,
    'Trinity':        1_000_000_000,
    'Tulare':         20_000_000_000,
    'Tuolumne':       2_000_000_000,
    'Ventura':        65_000_000_000,
    'Yolo':           12_000_000_000,
    'Yuba':           3_000_000_000,
}

county_population_map = {
    'Alameda':        1_690_000,
    'Alpine':         1_200,
    'Amador':         39_000,
    'Butte':          225_000,
    'Calaveras':      46_000,
    'Colusa':         22_000,
    'Contra Costa':   1_165_000,
    'Del Norte':      28_000,
    'El Dorado':      192_000,
    'Fresno':         1_030_000,
    'Glenn':          29_000,
    'Humboldt':       136_000,
    'Imperial':       194_000,
    'Inyo':           19_000,
    'Kern':           940_000,
    'Kings':          156_000,
    'Lake':           68_000,
    'Lassen':         30_000,
    'Los Angeles':   10_330_000,
    'Madera':         170_000,
    'Marin':          260_000,
    'Mariposa':       18_000,
    'Mendocino':      88_000,
    'Merced':         300_000,
    'Modoc':          9_000,
    'Mono':           14_000,
    'Monterey':       450_000,
    'Napa':           150_000,
    'Nevada':         102_000,
    'Orange':        3_190_000,
    'Placer':         410_000,
    'Plumas':         20_000,
    'Riverside':      2_530_000,
    'Sacramento':     1_660_000,
    'San Benito':     70_000,
    'San Bernardino': 2_270_000,
    'San Diego':      3_410_000,
    'San Francisco':  875_000,
    'San Joaquin':    795_000,
    'San Luis Obispo':285_000,
    'San Mateo':      780_000,
    'Santa Barbara':  455_000,
    'Santa Clara':   1_990_000,
    'Santa Cruz':     275_000,
    'Shasta':         185_000,
    'Sierra':         3_000,
    'Siskiyou':       45_000,
    'Solano':         450_000,
    'Sonoma':         500_000,
    'Stanislaus':     570_000,
    'Sutter':         100_000,
    'Tehama':         65_000,
    'Trinity':        13_000,
    'Tulare':         490_000,
    'Tuolumne':       55_000,
    'Ventura':        860_000,
    'Yolo':           230_000,
    'Yuba':           85_000,
}


def get_nearby_towns_osm(lat, lon, radius_m=5000, max_retries=2, timeout=10):    
    overpass_url = "https://overpass-api.de/api/interpreter"
    query = f"""
    [out:json];
    node["place"~"town|city"](around:{radius_m},{lat},{lon});
    out;
    """
    # Use urllib directly to avoid OSMnx DNS patching conflicts with requests
    query_bytes = query.encode('utf-8')
    req = urllib.request.Request(overpass_url, data=query_bytes, headers={"Content-Type": "text/plain"})
    
    for attempt in range(max_retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                data = json.loads(response.read().decode('utf-8'))
            
            towns = [{"name": e["tags"].get("name"), "lat": e["lat"], "lng": e["lon"], "population": e["tags"].get("population")} for e in data.get("elements", [])]
            return towns
        except urllib.error.HTTPError as e:
            print(f"[get_nearby_towns_osm] HTTP Error {e.code}: {e.reason} (attempt {attempt + 1}/{max_retries + 1})")
            if attempt < max_retries:
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
            else:
                print(f"[get_nearby_towns_osm] Max retries reached, returning empty list")
                return []
        except urllib.error.URLError as e:
            print(f"[get_nearby_towns_osm] URL Error: {e.reason} (attempt {attempt + 1}/{max_retries + 1})")
            if attempt < max_retries:
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
            else:
                print(f"[get_nearby_towns_osm] Max retries reached, returning empty list")
                return []
        except Exception as e:
            print(f"[get_nearby_towns_osm] Unexpected error: {e} (attempt {attempt + 1}/{max_retries + 1})")
            if attempt < max_retries:
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
            else:
                print(f"[get_nearby_towns_osm] Max retries reached, returning empty list")
                return []
    
    return []

def get_county(lat, lng, max_retries=2):
    url = f"https://geo.fcc.gov/api/census/block/find?latitude={lat}&longitude={lng}&format=json"
    for attempt in range(max_retries + 1):
        try:
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            data = r.json()
            county_name = data['County']['name']
            # Strip 'County' suffix if present
            county_name = county_name.replace(' County', '').strip()
            return county_name
        except requests.exceptions.RequestException as e:
            print(f"[get_county] Request error: {e} (attempt {attempt + 1}/{max_retries + 1})")
            if attempt < max_retries:
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
            else:
                print(f"[get_county] Max retries reached, returning None")
                return None
        except (KeyError, ValueError) as e:
            print(f"[get_county] Data parsing error: {e}")
            return None

def location_to_neighbor_values(lat, lng):
    try:
        locations = get_nearby_towns_osm(lat, lng, 5000)
        if not locations:
            print(f"[location_to_neighbor_values] No nearby towns found or API call failed, returning empty list")
            return []
        
        towns_w_value = []
        county = get_county(lat, lng)
        
        if not county:
            print(f"[location_to_neighbor_values] Could not determine county, returning empty list")
            return []
        
        if county not in county_gdp_map or county not in county_population_map:
            print(f"[location_to_neighbor_values] County '{county}' not found in maps, returning empty list")
            return []

        for i in locations:
            i_lng = i.get("lng")
            i_lat = i.get("lat")
            pop = i.get("population")
            if pop != None:
                pop = int(i.get("population"))
            else:
                pop = 0
            GDP = county_gdp_map[county]
            
            ratio = pop / county_population_map[county]
            value = GDP * ratio

            #add the value to the existing i and push to towns_w_value
            i['population'] = pop
            i['value-estimate'] = value
            towns_w_value.append(i)
        return towns_w_value
    except Exception as e:
        print(f"[location_to_neighbor_values] Unexpected error: {e}")
        print(f"[location_to_neighbor_values] Traceback: {traceback.format_exc()}")
        return []