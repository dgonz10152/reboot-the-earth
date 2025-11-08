import os
import math
import json
import random
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
from neighbors import location_to_neighbor_values
from openai import OpenAI


load_dotenv()
client = OpenAI(api_key=os.getenv("OPEN_AI"))

STATISTICS_PROMPT = """
You are a scoring agent for prescribed fire risk. Use the reference PDF (retrieved via vector store ID: vs_690e81d520088191958d81df531fa352) to classify user-provided information into risk tiers and convert them to normalized numeric scores.

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


def calculate_fire_statistics(input_data):
    """
    Calculate prescribed fire risk statistics based on input data using AI model.

    Args:
        input_data (dict): Location data containing coordinates, weather, nearby towns, etc.

    Returns:
        dict: Statistics object with 11 risk scores (0.00-1.00 each) in the format:
            {
                "statistics": {
                    "safety": float,
                    "fire-behavior": float,
                    ...
                }
            }

    Raises:
        Exception: If the AI model call fails or response cannot be parsed.
    """
    try:
        data_dump = json.dumps(input_data, indent=2)
        user_prompt = f"""
Analyze the following data and calculate prescribed fire risk scores.

INPUT DATA:
{data_dump}

INSTRUCTIONS:
1. First, search the web for relevant information about this location including:
   - Brush and vegetation density
   - Topography and terrain characteristics  
   - Fuel load and vegetation types
   - Historical wildfire data
   - Local weather patterns and fire season conditions

2. Based on the input data AND the web search results, calculate risk scores for all 11 categories.

3. Consider all available information:
   - Coordinates and location details
   - Weather data (temperature, wind speed, weather codes)
   - Population density and nearby towns
   - Historical burn dates
   - Any other relevant data in the input

4. Return ONLY the statistics object with scores from 0.00 to 1.00 for each category.
"""
        
        resp = client.chat.completions.create(
            model="o4-mini",
            messages=[
                {"role": "system", "content": STATISTICS_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            reasoning_effort="medium",
            response_format={"type": "json_schema", "json_schema": JSON_SCHEMA},
        )
        
        return json.loads(resp.choices[0].message.content)
        
    except Exception as e:
        print(f"Error calculating fire statistics: {e}")
        raise


def calculate_threat_rating(preliminary_feasability_score, threat_rating, total_population, total_value_estimate):
    """
    Calculate the threat rating based on feasibility score, threat rating, population, and value.

    Args:
        preliminary_feasability_score (float): Preliminary feasibility score (0.0-1.0).
        threat_rating (float): Base threat rating (0.0-1.0).
        total_population (int): Total population in nearby areas.
        total_value_estimate (float): Total estimated value of nearby areas.

    Returns:
        float: Calculated threat rating.
    """
    if total_population == 0 and total_value_estimate == 0:
        return (threat_rating * 0.9) + ((preliminary_feasability_score + 0.3) * 0.1)
    
    return threat_rating * math.sqrt(total_value_estimate) * math.log(1 + total_population, 10) * preliminary_feasability_score


def get_weather_data(lat, lng):
    """
    Fetch weather data for a given latitude and longitude.

    Args:
        lat (float): Latitude coordinate.
        lng (float): Longitude coordinate.

    Returns:
        dict: Weather data JSON response, or None if request fails.
    """
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lng}&daily=temperature_2m_mean,soil_moisture_0_to_7cm_mean,weathercode,windspeed_10m_mean&timezone=America/Los_Angeles&temperature_unit=fahrenheit"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching weather data: {e}")
        return None


def get_town(lat, lng):
    """
    Get town/location name for given coordinates using reverse geocoding.

    Args:
        lat (float): Latitude coordinate.
        lng (float): Longitude coordinate.

    Returns:
        dict: Location data JSON response, or None if request fails or API key is missing.
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


def generate_v1_dummy_data():
    """
    Generate burn area data matching the v1 endpoint schema.

    Returns:
        list: List of burn area dictionaries, each containing coordinates, statistics,
              threat ratings, weather data, and nearby town information.
    """
    california_coords = [
        {"cords": (-122.705376, 39.997488), "probability": 0.0523},
        {"cords": (-122.741309, 40.051387), "probability": 0.0523},
        {"cords": (-116.102759, 33.448770), "probability": 0.0510},
        {"cords": (-122.867073, 39.853758), "probability": 0.0501},
        {"cords": (-123.639624, 41.524624), "probability": 0.0493},
        {"cords": (-123.010803, 39.638162), "probability": 0.0493},
        {"cords": (-119.920599, 36.556940), "probability": 0.0479},
        {"cords": (-121.025527, 36.071850), "probability": 0.0441},
        {"cords": (-123.666574, 41.497675), "probability": 0.0438},
        {"cords": (-118.402446, 34.580647), "probability": 0.0428},
    ]
    
    burn_areas = []
    for coord_data in california_coords:
        lng, lat = coord_data["cords"]
        threat_rating = coord_data["probability"]
        
        area_id = math.floor(lat * lng) * math.floor(0.2 * lng * lat) + math.floor(random.random() * 1000)
        days_ago = random.randint(0, 1825)
        last_burn_date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
        
        nearby_towns = location_to_neighbor_values(lat, lng)
        total_population = sum(town["population"] for town in nearby_towns)
        total_value_estimate = sum(town["value-estimate"] for town in nearby_towns)
        
        town = get_town(lat, lng)
        town_name = town.get("display_name") if town else "N/A"
        weather_data = get_weather_data(lat, lng)
        
        dump_data = {
            "coordinates": {"lat": lat, "lng": lng},
            "id": area_id,
            "last-burn-date": last_burn_date,
            "name": town_name,
            "weather": weather_data,
            "threat-rating": threat_rating,
            "nearby-towns": nearby_towns,
            "total-population": total_population,
            "total-value-estimate": total_value_estimate
        }
        
        statistics = calculate_fire_statistics(dump_data)
        stat_values = list(statistics['statistics'].values())
        preliminary_feasability_score = 1 - (round(sum(stat_values) / len(stat_values), 3))
        
        burn_area = {
            "coordinates": {"lat": lat, "lng": lng},
            "id": area_id,
            "last-burn-date": last_burn_date,
            "name": town_name,
            "statistics": statistics['statistics'],
            "preliminary-feasability-score": preliminary_feasability_score,
            "weather": weather_data,
            "threat-rating": threat_rating,
            "calculated-threat-rating": calculate_threat_rating(
                preliminary_feasability_score, 
                threat_rating, 
                total_population, 
                total_value_estimate
            ),
            "nearby-towns": nearby_towns,
            "total-population": total_population,
            "total-value-estimate": total_value_estimate
        }
        
        burn_areas.append(burn_area)
    
    return burn_areas


def main():
    """
    Generate burn area data and save it to a JSON file.
    """
    print("Generating burn area data...")
    burn_areas = generate_v1_dummy_data()
    
    v1_response = {
        "status": "success",
        "data": burn_areas
    }
    
    output_file = "precomputed_data.json"
    with open(output_file, 'w') as f:
        json.dump(v1_response, f, indent=2)
    
    print(f"Data generated and saved to {output_file}")
    print(f"Generated {len(burn_areas)} burn areas")


if __name__ == "__main__":
    main()

