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
from neighbors import location_to_neighbor_values
import math

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

    if total_population == 0 and total_value_estimate == 0:
        return ((threat_rating * 0.9) + ((preliminary_feasability_score + 0.3) * 0.1))
        

    return (threat_rating * 0.7) + ((preliminary_feasability_score + 0.3) * 0.1) + ((total_population / 52_000 + total_value_estimate / 16_650_000_000) / 6 ) * 0.2

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


    california_coords = [
    (32.534156, -117.127221),  # San Diego
    (33.953349, -117.396156),  # Riverside
    (34.052235, -118.243683),  # Los Angeles
    (36.778259, -119.417931),  # Central California
    (37.774929, -122.419418),  # San Francisco
    (38.581572, -121.494400),  # Sacramento
    (39.728494, -121.837478),  # Chico
    (40.586540, -122.391675),  # Redding
    (41.745870, -122.634075),  # Mount Shasta
    (34.420830, -119.698189),  # Santa Barbara
    (36.974117, -122.030792),  # Santa Cruz
    (32.715736, -117.161087),  # Another point in San Diego
    (38.440429, -122.714054),  # Santa Rosa
    (34.108345, -117.289765),  # San Bernardino
    (36.737797, -119.787125),  # Fresno
]
 
    
    # Generate random burn area data
    burn_areas = []
    for i in range(4):  # Generate 10 random burn areas
        # Generate random coordinates (California area)
        # lat = round(random.uniform(32.0, 42.0), 6)
        # lng = round(random.uniform(-125.0, -114.0), 6)

        lat, lng = random.choice(california_coords)
        

        #TODO: CHANGE AREA AND BURN DAYS
        # Generate random ID
        area_id = math.floor(lat * lng) * math.floor(0.2 * lng * lat) + math.floor(random.random() * 1000)
        
        # Generate random last burn date (within last 5 years)
        days_ago = random.randint(0, 1825)  # 5 years
        last_burn_date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
        
        #TODO: REPLACE WITH GPT QUERIES
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
        preliminary_feasability_score = 1 - (round(sum(stat_values) / len(stat_values), 3))
                
        # Generate threat ratings (random predictions from malco model)
        threat_rating = round(random.uniform(0.0, 1.0), 3)
        
        # Generate nearby towns (1-4 towns)
        num_towns = random.randint(1, 4)
        nearby_towns = location_to_neighbor_values(lat, lng)
        
        total_population = sum(town["population"] for town in nearby_towns)
        total_value_estimate = sum(town["value-estimate"] for town in nearby_towns)

        # get_weather_data(lat, lng)

        town = get_town(lat, lng)


        town_name = "N/A"

        if town:
            town_name = town.get("display_name")

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
            "nearby-towns": nearby_towns,
            "total-population": total_population,
            "total-value-estimate": total_value_estimate
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
