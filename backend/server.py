from flask import Flask, request, jsonify
from joblib import load
from joblib import Parallel, delayed
import os
import numpy as np
import pandas as pd
import json
from flask_cors import CORS
import requests
from dotenv import load_dotenv
from neighbors import location_to_neighbor_values
import math
import json
import time
from openai import OpenAI
import traceback

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
# OpenAI Prompts
# -------------------------------

WEB_RESEARCH_AGENT_PROMPT = """
You are a Web Research Agent specializing in gathering real-world environmental, geographic,
cultural, and logistical information for prescribed fire planning.
Your job is to use online sources—including government data portals, land-management agencies,
scientific literature, maps, satellite tools, and regional planning documents—to collect accurate,
verifiable information about a given project location.

GOAL
When provided a location (coordinates, address, region name, or project boundary),
research the location and produce factual, sourced answers to each of the assessment questions.

RESEARCH REQUIREMENTS
- Use authoritative sources whenever possible.
- Prioritize the most recent available data.
- Summarize findings concisely but with sufficient detail for risk analysis.
- Include citations with URLs for each answer.
- If data cannot be found, state what is missing and which sources were searched.
- Do not invent information.

OUTPUT FORMAT
Return a JSON object with the following fields:

{
  "resources_inside_boundary": "",
  "sensitive_adjacent_resources": "",
  "public_interest_level": "",
  "environmental_hazards": "",
  "nearest_ems_facilities": "",
  "fuel_models_and_variability": "",
  "terrain_and_wind_effects": "",
  "probability_of_external_ignitions": "",
  "containment_dependencies": "",
  "suppression_constraints_if_slopover": "",
  "accessibility_and_remoteness": "",
  "sources": []
}

RESEARCH TASKS
For the given location, find and summarize:
1. Natural, cultural, or human resources inside the project boundary
2. Significant developments or sensitive resources just outside the boundary
3. Degree of public/political sensitivity or concern
4. Environmental hazards onsite or along travel routes
5. Nearest EMS facilities and transport times
6. Dominant fuel models and variability
7. Wind/microclimate impacts from terrain
8. Ignition probability outside the unit (spotting or slopover)
9. Dependence on natural fuel breaks and heavy-fuel concerns
10. Suppression restrictions if the fire escapes into nearby areas
11. Accessibility, remoteness, travel/vehicle limitations
"""

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
# Helper: Load Precomputed Data
# -------------------------------

def load_precomputed_data():
    """
    Load the precomputed data from JSON file.
    """
    try:
        with open("precomputed_data.json", 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("Warning: precomputed_data.json not found. Run pre_compute.py first.")
        return {
            "status": "error",
            "data": [],
            "message": "Precomputed data not found. Please run pre_compute.py first."
        }
    except json.JSONDecodeError as e:
        print(f"Error parsing precomputed_data.json: {e}")
        return {
            "status": "error",
            "data": [],
            "message": "Error parsing precomputed data file."
        }

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


def research_and_score_location(location, context="", hints=""):
    """
    Combined function that researches a location and then scores it using the statistics schema.
    
    Args:
        location: String describing the place to research
        context: Optional extra context for scoring
        hints: Optional numeric thresholds or labels
    
    Returns:
        Dictionary with statistics matching JSON_SCHEMA format, or None on error
    """
    print(f"[research_and_score_location] Called with location: {location}")
    if not location or not location.strip():
        print("[research_and_score_location] Location is empty, returning None")
        return None
    
    try:
        # Step 1: Research the location using the web research agent
        print(f"[research_and_score_location] Making research API call for location: {location}")
        research_response = client.chat.completions.create(
            model="gpt-4o-mini-search-preview",   # or whichever model you are using
            messages=[
                {"role": "system", "content": WEB_RESEARCH_AGENT_PROMPT},
                {"role": "user", "content": f"Research the following location: {location}"}
            ]
        )
        
        # Extract research output
        research_data = research_response.choices[0].message.content
        print(f"[research_and_score_location] Research data output: {research_data}")
        
        # Step 2: Use research data as input to the scoring agent via Assistants API
        # Combine research data with any additional context/hints
        scoring_input = {
            "input": research_data,
            "context": context,
            "hints": hints
        }
        
        print(f"[research_and_score_location] Creating assistant for scoring with vector store")
        
        # Create an assistant with file_search tool and vector store
        assistant = client.beta.assistants.create(
            name="Fire Risk Scoring Assistant",
            instructions=STATISTICS_PROMPT,
            model="gpt-4o-mini",
            tools=[{"type": "file_search"}],
            tool_resources={
                "file_search": {
                    "vector_store_ids": [VECTOR_STORE_ID]
                }
            },
            temperature=0.1,
        )
        
        # Create a thread
        thread = client.beta.threads.create()
        
        # Add the user message
        user_message = (
            "Score the following inputs strictly per the schema. "
            "If any category is missing, infer conservatively.\n\n"
            f"{json.dumps(scoring_input, indent=2)}\n\n"
            "IMPORTANT: You must return ONLY valid JSON matching this exact schema:\n"
            f"{json.dumps(JSON_SCHEMA['schema'], indent=2)}"
        )
        
        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=user_message
        )
        
        # Run the assistant
        print(f"[research_and_score_location] Running assistant thread")
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistant.id
        )
        
        # Poll for completion
        while run.status in ["queued", "in_progress"]:
            time.sleep(0.5)
            run = client.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id
            )
        
        if run.status != "completed":
            raise Exception(f"Assistant run failed with status: {run.status}")
        
        # Retrieve the response
        messages = client.beta.threads.messages.list(thread_id=thread.id)
        score_json = messages.data[0].content[0].text.value
        
        print(f"[research_and_score_location] Assistant response: {score_json}")
        
        # Parse the JSON string to get the statistics dict
        result = json.loads(score_json)
        
        # Return just the statistics object (matching the format used in v1 endpoint)
        return result.get("statistics", {})
        
    except Exception as e:
        print(f"[research_and_score_location] Error occurred: {e}")
        print(f"[research_and_score_location] Traceback: {traceback.format_exc()}")
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
    for i in range(1):  # Generate 10 random burn areas
        # Generate random coordinates (California area)
        # lat = round(random.uniform(32.0, 42.0), 6)
        # lng = round(random.uniform(-125.0, -114.0), 6)

        lat, lng = 39.997488, -122.705376
        

        #TODO: CHANGE AREA AND BURN DAYS
        # Generate random ID
        area_id = math.floor(lat * lng) * math.floor(0.2 * lng * lat) + math.floor(random.random() * 1000)
        
        # Generate random last burn date (within last 5 years)
        days_ago = random.randint(0, 1825)  # 5 years
        last_burn_date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
        
        # Get town name first to use for location research
        town = get_town(lat, lng)
        town_name = "N/A"
        if town:
            town_name = town.get("display_name")
        
        # Generate nearby towns (1-4 towns)
        num_towns = random.randint(1, 4)
        print(f"[generate_v1_dummy_data] Fetching nearby towns for location: {lat}, {lng}")
        nearby_towns = location_to_neighbor_values(lat, lng)
        
        if not nearby_towns:
            print(f"[generate_v1_dummy_data] No nearby towns found, using empty list")
            nearby_towns = []
        
        total_population = sum(town.get("population", 0) for town in nearby_towns)
        total_value_estimate = sum(town.get("value-estimate", 0) for town in nearby_towns)
        
        # Use combined research and scoring function
        # Create location string from town name or coordinates
        location_string = town_name if town_name != "N/A" else f"{lat}, {lng}"
        
        # Call the combined research and scoring function
        print(f"[generate_v1_dummy_data] Calling research_and_score_location for: {location_string}")
        statistics = research_and_score_location(location_string)
        
        # Fallback to random statistics if research/scoring fails
        if not statistics:
            print(f"[generate_v1_dummy_data] Research/scoring failed, using fallback random statistics")
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
        else:
            print(f"[generate_v1_dummy_data] Successfully received statistics from research_and_score_location")
            # Ensure all values are rounded to 3 decimal places
            statistics = {k: round(float(v), 3) for k, v in statistics.items()}
        
        # Calculate preliminary feasibility score (average of all statistics)
        stat_values = list(statistics.values())
        # Clamp the score to ensure it's between 0 and 1
        preliminary_feasability_score = 1 - (round(sum(stat_values) / len(stat_values), 3))
                
        # Generate threat ratings (random predictions from malco model)
        threat_rating = round(random.uniform(0.0, 1.0), 3)

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
    Return the v1 endpoint with precomputed data.
    """
    v1_response = load_precomputed_data()
    return jsonify(v1_response), 200

@app.route("/v0", methods=["GET"])
def v0():
    """
    Return the v0 endpoint with precomputed data.
    """
    v0_response = load_precomputed_data()
    return jsonify(v0_response), 200

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
