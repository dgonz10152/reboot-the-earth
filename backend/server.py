from flask import Flask, request, jsonify
from joblib import load
from joblib import Parallel, delayed
import os
import numpy as np
import pandas as pd
import random
from datetime import datetime, timedelta
from flask_cors import CORS
import requests
from dotenv import load_dotenv
# import backend.data_processing as dp  # <-- you'll create this
# import backend.io_utils as ioutil      # <-- optional (for file handling)

# Load environment variables from .env file
load_dotenv()

# -------------------------------
# Load Model Bundle
# -------------------------------
try:
    bundle = load("prescribed_fire_model.joblib")
    model = bundle["model"]
    feature_columns = bundle["columns"]
    label_encoder = bundle.get("label_encoder")  # optional if classification
except FileNotFoundError:
    model = None
    feature_columns = []
    label_encoder = None
    print("Warning: Model file not found. Some endpoints may not work.")

# -------------------------------
# Flask App Initialization
# -------------------------------
app = Flask(__name__)
CORS(app)
# -------------------------------
# Helper: Run Model Inference
# -------------------------------

def calculate_threat_rating(preliminary_feasability_score, threat_rating, total_population, total_value_estimate):
    """
    Calculate the threat rating based on the preliminary feasability score, threat rating, total population, and total value estimate.
    """
    return (threat_rating * 0.7) + (preliminary_feasability_score * 0.1) + ((total_population / 52_000 + total_value_estimate / 16_650_000_000) / 2 ) * 0.2

def get_weather_data(lat, lng):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lng}&daily=temperature_2m_mean,soil_moisture_0_to_7cm_mean,weathercode,windspeed_10m_mean&timezone=America/Los_Angeles&temperature_unit=fahrenheit"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Raises an exception for bad status codes
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching weather data: {e}")
        return None

def get_town(lat, lng):
    key = os.getenv("KEY")
    if not key:
        print("Error: KEY not found in environment variables")
        return None
    url = f"https://us1.locationiq.com/v1/reverse.php?key={key}&lat={lat}&lon={lng}&format=json"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Raises an exception for bad status codes
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching location data: {e}")
        return None

def get_towns_within_radius(lat, lon, radius_km, username="dgonz209"):
    """
    Returns nearby towns within a radius, including population and bounding box data.
    Requires a free GeoNames account (https://www.geonames.org/login).
    """
    # Step 1: find towns within radius
    url = "http://api.geonames.org/findNearbyPlaceNameJSON"
    params = {
        "lat": lat,
        "lng": lon,
        "radius": radius_km,
        "maxRows": 20,
        "username": username,
    }
    response = requests.get(url, params=params)
    data = response.json()

    if "geonames" not in data:
        return []

    towns = []
    for g in data["geonames"]:
        geoname_id = g["geonameId"]

        # Step 2: get bounding box + more metadata for each town
        details_url = f"http://api.geonames.org/getJSON"
        details_params = {"geonameId": geoname_id, "username": username}
        details_resp = requests.get(details_url, params=details_params)
        details = details_resp.json()

        bbox = details.get("bbox", {})
        bbox_coords = None
        if bbox:
            bbox_coords = {
                "north": bbox.get("north"),
                "south": bbox.get("south"),
                "east": bbox.get("east"),
                "west": bbox.get("west"),
            }

        towns.append({
            "name": g["name"],
            "country": g.get("countryName"),
            "lat": g["lat"],
            "lon": g["lng"],
            "population": g.get("population"),
            "distance_km": g.get("distance"),
            "bbox": bbox_coords,
        })

    return towns


def generate_v0_dummy_data():
    """
    Generate dummy data matching the v1 endpoint schema.
    """
    # Sample town names for generating dummy data
    
    nearby_town_names = [
        "Hillsborough", "Valley Springs", "Forest Hills", "Meadowbrook",
        "Canyon Ridge", "Desert View", "Mountain Peak", "River Bend",
        "Coastal Bay", "Prairie Town", "Timberland", "Silver Lake"
    ]
    
 
    
    # Generate random burn area data
    burn_areas = []
    for i in range(5):  # Generate 10 random burn areas
        # Generate random coordinates (California area)
        lat = round(random.uniform(32.0, 42.0), 6)
        lng = round(random.uniform(-125.0, -114.0), 6)
        
        # Generate random ID
        area_id = random.randint(1000, 9999)
        
        # Generate random last burn date (within last 5 years)
        days_ago = random.randint(0, 1825)  # 5 years
        last_burn_date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
        
        
        # Generate statistics (all float values from 0-1)
        statistics = {
            "safety": round(random.uniform(0.0, 1.0), 3),
            "fire-behavior": round(random.uniform(0.0, 1.0), 3),
            "resistance-to-containment": round(random.uniform(0.0, 1.0), 3),
            "ignition-procedures-and-methods": round(random.uniform(0.0, 1.0), 3),
            "prescribed-fire-duration": round(random.uniform(0.0, 1.0), 3),
            "smoke-management": round(random.uniform(0.0, 1.0), 3),
            "number-and-dependence-of-activities": round(random.uniform(0.0, 1.0), 3),
            "management-organizations": round(random.uniform(0.0, 1.0), 3),
            "treatment-resource-objectives": round(random.uniform(0.0, 1.0), 3),
            "constraints": round(random.uniform(0.0, 1.0), 3),
            "project-logistics": round(random.uniform(0.0, 1.0), 3)
        }
        
        # Calculate preliminary feasibility score (average of all statistics)
        stat_values = list(statistics.values())
        preliminary_feasability_score = round(sum(stat_values) / len(stat_values), 3)
                
        # Generate threat ratings (random predictions from malco model)
        threat_rating = random.uniform(0.0, 1.0)
        
        # Generate nearby towns (1-4 towns)
        num_towns = random.randint(1, 4)
        nearby_towns = []
        used_town_names = set()
        
        for _ in range(num_towns):
            # Ensure unique town names
            town_name = random.choice(nearby_town_names)
            while town_name in used_town_names:
                town_name = random.choice(nearby_town_names)
            used_town_names.add(town_name)
            
            nearby_towns.append({
                "name": town_name,
                "population": random.randint(500, 50000),
                "value-estimate": round(random.uniform(1000000, 50000000), 2)  # GDP estimate in dollars
            })
        
        total_population = sum(town["population"] for town in nearby_towns)
        total_value_estimate = sum(town["value-estimate"] for town in nearby_towns)

        # get_weather_data(lat, lng)

        town = get_town(lat, lng)


        town_name = "N/A"

        if town:
            town_name = town.get("display_name")
            print(town.get("boundingbox"))

        burn_area = {
            "coordinates": {
                "lat": lat,
                "lng": lng
            },
            "id": area_id,
            "last-burn-date": last_burn_date,
            "name": town_name,
            "statistics": statistics,
            "preliminary-feasability-score": preliminary_feasability_score,
            "weather": get_weather_data(lat, lng),
            "threat-rating": threat_rating,
            "calculated-threat-rating": calculate_threat_rating(preliminary_feasability_score, threat_rating, total_population, total_value_estimate),
            "nearby-towns": nearby_towns
        }
        
        burn_areas.append(burn_area)
    
    return burn_areas


def generate_v1_dummy_data():
    """
    Generate dummy data matching the v1 endpoint schema.
    """
    # Sample town names for generating dummy data
    
    nearby_town_names = [
        "Hillsborough", "Valley Springs", "Forest Hills", "Meadowbrook",
        "Canyon Ridge", "Desert View", "Mountain Peak", "River Bend",
        "Coastal Bay", "Prairie Town", "Timberland", "Silver Lake"
    ]

    threat_rating = random.uniform(0.0, 1.0)



 
    
    # Generate random burn area data
    burn_areas = []
    for i in range(1):  # Generate 10 random burn areas
        # Generate random coordinates (California area)
        lat = round(random.uniform(32.0, 42.0), 6)
        lng = round(random.uniform(-125.0, -114.0), 6)
        
        # Generate random ID
        area_id = random.randint(1000, 9999)
        
        # Generate random last burn date (within last 5 years)
        days_ago = random.randint(0, 1825)  # 5 years
        last_burn_date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
        
        
        # Generate statistics (all float values from 0-1)
        statistics = {
            "safety": round(random.uniform(0.0, 1.0), 3),
            "fire-behavior": round(random.uniform(0.0, 1.0), 3),
            "resistance-to-containment": round(random.uniform(0.0, 1.0), 3),
            "ignition-procedures-and-methods": round(random.uniform(0.0, 1.0), 3),
            "prescribed-fire-duration": round(random.uniform(0.0, 1.0), 3),
            "smoke-management": round(random.uniform(0.0, 1.0), 3),
            "number-and-dependence-of-activities": round(random.uniform(0.0, 1.0), 3),
            "management-organizations": round(random.uniform(0.0, 1.0), 3),
            "treatment-resource-objectives": round(random.uniform(0.0, 1.0), 3),
            "constraints": round(random.uniform(0.0, 1.0), 3),
            "project-logistics": round(random.uniform(0.0, 1.0), 3)
        }
        
        # Calculate preliminary feasibility score (average of all statistics)
        stat_values = list(statistics.values())
        # Clamp the score to ensure it's between 0 and 1
        preliminary_feasability_score = (round(sum(stat_values) / len(stat_values), 3))
                
        # Generate threat ratings (random predictions from malco model)
        threat_rating = round(random.uniform(0.0, 1.0), 3)
        
        # Generate nearby towns (1-4 towns)
        num_towns = random.randint(1, 4)
        nearby_towns = []
        used_town_names = set()
        
        for _ in range(num_towns):
            # Ensure unique town names
            town_name = random.choice(nearby_town_names)
            while town_name in used_town_names:
                town_name = random.choice(nearby_town_names)
            used_town_names.add(town_name)
            
            nearby_towns.append({
                "name": town_name,
                "population": random.randint(500, 50000),
                "value-estimate": round(random.uniform(1000000, 50000000), 2)  # GDP estimate in dollars
            })
        
        total_population = sum(town["population"] for town in nearby_towns)
        total_value_estimate = sum(town["value-estimate"] for town in nearby_towns)

        # get_weather_data(lat, lng)

        town = get_town(lat, lng)


        town_name = "N/A"

        if town:
            town_name = town.get("display_name")
            print(town.get("boundingbox"))

        burn_area = {
            "coordinates": {
                "lat": lat,
                "lng": lng
            },
            "id": area_id,
            "last-burn-date": last_burn_date,
            "name": town_name,
            "statistics": statistics,
            "preliminary-feasability-score": preliminary_feasability_score,
            "weather": get_weather_data(lat, lng),
            "threat-rating": threat_rating,
            "calculated-threat-rating": calculate_threat_rating(preliminary_feasability_score, threat_rating, total_population, total_value_estimate),
            "nearby-towns": nearby_towns
        }
        
        burn_areas.append(burn_area)
    
    return burn_areas

@app.route("/v1", methods=["GET"])
def v1():
    """
    Return the v1 endpoint with dummy data matching the specified schema.
    """
    burn_areas = generate_v1_dummy_data()
    
    v1_response = {
        "status": "success",
        "message": "This is the v1 endpoint",
        "data": burn_areas
    }
    return jsonify(v1_response), 200

@app.route("/v0", methods=["GET"])
def v0():
    """
    Return the v1 endpoint with dummy data matching the specified schema.
    """
    burn_areas = generate_v0_dummy_data()
    
    v1_response = {
        "status": "success",
        "data": burn_areas
    }
    return jsonify(v1_response), 200

# -------------------------------
# Run the Server
# -------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5003, debug=True)
