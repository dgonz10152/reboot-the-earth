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
from openai import OpenAI

# import backend.data_processing as dp  # <-- you'll create this
# import backend.io_utils as ioutil      # <-- optional (for file handling)

# Load environment variables from .env file
load_dotenv()

client = OpenAI(api_key=os.getenv("OPEN_AI"))
VECTOR_STORE_ID = "vs_690e81d520088191958d81df531fa352"

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
# OpenAI Prompt
# -------------------------------

STATISTICS_PROMPT = """
You are a scoring agent for prescribed fire risk. Use the reference PDF (retrieved via vector store ID: vs_690e81d520088191958d81df531fa352) to classify user-provided information into risk tiers and convert them to normalized numeric scores.

TASK
Read any user inputs (text, numbers, descriptions, sensor data, summaries, etc.). For each category below, determine a risk level based on the PDF’s criteria, then convert it to a numeric value:

Low → 0.00–0.33 (default 0.20)
Moderate → 0.34–0.66 (default 0.50)
High → 0.67–1.00 (default 0.80)

Always round to two decimals.

If input clearly matches PDF criteria, use that level.
If numeric thresholds apply, compare directly.
If ambiguous or missing, infer conservatively or default to Moderate.
If explicit labels (Low/Moderate/High) are given, map directly.
If user provides numbers already 0–1, accept if reasonable.

Never output anything except valid JSON.

OUTPUT SCHEMA (strict):
{
"statistics": {
"safety": number,
"fire-behavior": number,
"resistance-to-containment": number,
"ignition-procedures-and-methods": number,
"prescribed-fire-duration": number,
"smoke-management": number,
"number-and-dependence-of-activities": number,
"management-organizations": number,
"treatment-resource-objectives": number,
"constraints": number,
"project-logistics": number
}
}

All fields required. Values must be 0.00–1.00. No extra fields. No text outside the JSON.

SCORING STEPS
1. Retrieve relevant PDF information using vector store vs_690e81d520088191958d81df531fa352.
2. Extract user details per category.
3. Assign Low/Moderate/High according to PDF definitions.
4. Convert to numeric value, round to two decimals.
5. Populate the JSON exactly.
"""

JSON_SCHEMA = {
    "name": "fire_statistics",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "statistics": {
                "type": "object",
                "properties": {
                    "safety": {"type": "number"},
                    "fire-behavior": {"type": "number"},
                    "resistance-to-containment": {"type": "number"},
                    "ignition-procedures-and-methods": {"type": "number"},
                    "prescribed-fire-duration": {"type": "number"},
                    "smoke-management": {"type": "number"},
                    "number-and-dependence-of-activities": {"type": "number"},
                    "management-organizations": {"type": "number"},
                    "treatment-resource-objectives": {"type": "number"},
                    "constraints": {"type": "number"},
                    "project-logistics": {"type": "number"}
                },
                "required": [
                    "safety",
                    "fire-behavior",
                    "resistance-to-containment",
                    "ignition-procedures-and-methods",
                    "prescribed-fire-duration",
                    "smoke-management",
                    "number-and-dependence-of-activities",
                    "management-organizations",
                    "treatment-resource-objectives",
                    "constraints",
                    "project-logistics"
                ],
                "additionalProperties": False
            }
        },
        "required": ["statistics"],
        "additionalProperties": False
    }
}

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
    
def score():
    """
    Body (JSON):
    {
      "input": "...free text OR structured fields...",
      "context": "...optional extra notes...",
      "hints": "...optional numeric thresholds or labels provided by user..."
    }
    """
    data = request.get_json(force=True, silent=True) or {}
    user_payload = {
        "input": data.get("input", ""),
        "context": data.get("context", ""),
        "hints": data.get("hints", "")
    }

    try:
        resp = client.responses.create(
            model="o4-mini-2025-04-16",
            messages=[
                {"role": "system", "content": STATISTICS_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Score the following inputs strictly per the schema. "
                                "If any category is missing, infer conservatively.\n\n"
                                f"{user_payload}"
                            ),
                        }
                    ],
                },
            ],
            tools=[{
                "type": "file_search",
                "vector_store_ids": [VECTOR_STORE_ID]
            }],
            # Enforce strict JSON output via schema
            response_format={"type": "json_schema", "json_schema": JSON_SCHEMA},
            # (Optional) Temperature low for deterministic scoring
            temperature=0.1,
        )

        # With response_format=json_schema, the top-level output is valid JSON text
        content = resp.output_text  # SDK exposes parsed text; no extra parsing needed
        return app.response_class(
            response=content,
            status=200,
            mimetype="application/json"
        )

    except Exception as e:
        # Do not leak model output; return a clean error shape
        return jsonify({"error": str(e)}), 500

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

@app.route("/city-metrics", methods=["POST"])
def city_metrics():
    data = request.get_json()
    cities = data.get("cities", [])

    full_prompt = BASE_PROMPT % (
        population_2025,
        average_home_price,
        housing_units_2025,
        city_to_county
    ) + f"\nInput cities: {cities}"

    response = client.chat.completions.create(
        model="gpt-4o-mini-2024-07-18",
        messages=[{"role": "system", "content": full_prompt}],
        response_format={"type": "json"}
    )

    return jsonify(response.choices[0].message.parsed)

# -------------------------------
# Run the Server
# -------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5003, debug=True)
