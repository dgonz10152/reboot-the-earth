"""
Flask server for prescribed fire risk assessment API.

This module provides endpoints for retrieving precomputed burn area data
and integrates with OpenAI for location research and risk scoring.
"""

import json
import math
import os
import random
import time
import traceback
from datetime import datetime, timedelta

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_cors import CORS
from openai import OpenAI

from neighbors import location_to_neighbor_values
from pre_compute import calculate_threat_rating, get_weather_data

load_dotenv()

client = OpenAI(api_key=os.getenv("OPEN_AI"))
VECTOR_STORE_ID = "vs_690e81d520088191958d81df531fa352"

app = Flask(__name__)
CORS(app)

WEB_RESEARCH_AGENT_PROMPT = """You are a Web Research Agent specializing in gathering real-world environmental, geographic,
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

STATISTICS_PROMPT = """You are a scoring agent for prescribed fire risk. Use the reference PDF (retrieved via vector store ID: vs_690e81d520088191958d81df531fa352) to classify user-provided information into risk tiers and convert them to normalized numeric scores.

TASK
Read any user inputs (text, numbers, descriptions, sensor data, summaries, etc.). For each category below, determine a risk level based on the PDF's criteria, then convert it to a numeric value:

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

def load_precomputed_data():
    """
    Load precomputed burn area data from JSON file.

    Returns:
        dict: Precomputed data dictionary with status, data, and message fields.
              Returns error response if file not found or invalid JSON.
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
    """
    Retrieve town information for given coordinates using LocationIQ API.

    Args:
        lat (float): Latitude coordinate.
        lng (float): Longitude coordinate.

    Returns:
        dict: Location data from LocationIQ API, or None on error.
    """
    key = os.getenv("KEY")
    if not key:
        print("Error: KEY not found in environment variables")
        return None

    url = f"https://us1.locationiq.com/v1/reverse.php?key={key}&lat={lat}&lon={lng}&format=json"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching location data: {e}")
        return None


def research_and_score_location(location, context="", hints=""):
    """
    Research a location and score it using OpenAI's research and scoring agents.

    Args:
        location (str): String describing the place to research.
        context (str, optional): Additional context for scoring. Defaults to "".
        hints (str, optional): Numeric thresholds or labels. Defaults to "".

    Returns:
        dict: Statistics dictionary matching JSON_SCHEMA format, or None on error.
    """
    if not location or not location.strip():
        return None

    try:
        research_response = client.chat.completions.create(
            model="gpt-4o-mini-search-preview",
            messages=[
                {"role": "system", "content": WEB_RESEARCH_AGENT_PROMPT},
                {"role": "user", "content": f"Research the following location: {location}"}
            ]
        )

        research_data = research_response.choices[0].message.content
        scoring_input = {
            "input": research_data,
            "context": context,
            "hints": hints
        }

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

        thread = client.beta.threads.create()
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

        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistant.id
        )

        while run.status in ["queued", "in_progress"]:
            time.sleep(0.5)
            run = client.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id
            )

        if run.status != "completed":
            raise Exception(f"Assistant run failed with status: {run.status}")

        messages = client.beta.threads.messages.list(thread_id=thread.id)
        score_json = messages.data[0].content[0].text.value
        result = json.loads(score_json)

        return result.get("statistics", {})

    except Exception as e:
        print(f"Error in research_and_score_location: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return None


def generate_v1_dummy_data():
    """
    Generate dummy burn area data matching the v1 endpoint schema.

    Returns:
        list: List of burn area dictionaries with coordinates, statistics, and metadata.
    """
    burn_areas = []
    lat, lng = 39.997488, -122.705376

    area_id = math.floor(lat * lng) * math.floor(0.2 * lng * lat) + math.floor(random.random() * 1000)
    days_ago = random.randint(0, 1825)
    last_burn_date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")

    town = get_town(lat, lng)
    town_name = town.get("display_name") if town else "N/A"

    nearby_towns = location_to_neighbor_values(lat, lng) or []
    total_population = sum(town.get("population", 0) for town in nearby_towns)
    total_value_estimate = sum(town.get("value-estimate", 0) for town in nearby_towns)

    location_string = town_name if town_name != "N/A" else f"{lat}, {lng}"
    statistics = research_and_score_location(location_string)

    if not statistics:
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
        statistics = {k: round(float(v), 3) for k, v in statistics.items()}

    stat_values = list(statistics.values())
    preliminary_feasability_score = 1 - (round(sum(stat_values) / len(stat_values), 3))
    threat_rating = round(random.uniform(0.0, 1.0), 3)

    burn_area = {
        "coordinates": {"lat": lat, "lng": lng},
        "id": area_id,
        "last-burn-date": last_burn_date,
        "name": town_name,
        "statistics": statistics,
        "preliminary-feasability-score": preliminary_feasability_score,
        "weather": get_weather_data(lat, lng),
        "threat-rating": threat_rating,
        "calculated-threat-rating": calculate_threat_rating(
            preliminary_feasability_score, threat_rating, total_population, total_value_estimate
        ),
        "nearby-towns": nearby_towns,
        "total-population": total_population,
        "total-value-estimate": total_value_estimate
    }

    burn_areas.append(burn_area)
    return burn_areas

@app.route("/v1", methods=["GET"])
def v1():
    """
    Retrieve precomputed burn area data (v1 endpoint).

    Returns:
        JSON response with precomputed burn area data.
    """
    response = load_precomputed_data()
    return jsonify(response), 200


@app.route("/v0", methods=["GET"])
def v0():
    """
    Retrieve precomputed burn area data (v0 endpoint).

    Returns:
        JSON response with precomputed burn area data.
    """
    response = load_precomputed_data()
    return jsonify(response), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5003, debug=True)
