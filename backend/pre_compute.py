import os
import random
import math
import json
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
from neighbors import location_to_neighbor_values
from openai import OpenAI


# Load environment variables from .env file
load_dotenv()
VECTOR_STORE_ID = "vs_690e81d520088191958d81df531fa352"
client = OpenAI(api_key=os.getenv("OPEN_AI"))

# open ai prompt
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
    Calculate prescribed fire risk statistics based on input data.
    Performs web searches for brush, topography, and environmental data internally.
    
    Args:
        input_data (dict): Any location data (coordinates, weather, nearby towns, etc.)
        
    Returns:
        dict: Statistics object with 11 risk scores (0.00-1.00 each)
        
    Example:
        >>> data = {
        ...     "coordinates": {"lat": 40.58654, "lng": -122.391675},
        ...     "name": "Market Street, Redding, CA",
        ...     "weather": {...},
        ...     "nearby-towns": [...]
        ... }
        >>> stats = calculate_fire_statistics(data)
        >>> print(stats)
        {
            "statistics": {
                "safety": 0.72,
                "fire-behavior": 0.26,
                ...
            }
        }
    """
    try:
        # Convert input data to string for the prompt
        data_dump = json.dumps(input_data, indent=2)
        
        # Create comprehensive prompt
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
        
        # Call GPT-5 (o3-mini) with reasoning model
        resp = client.chat.completions.create(
            model="o4-mini",
            messages=[
                {"role": "system", "content": STATISTICS_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            reasoning_effort="medium",
            response_format={"type": "json_schema", "json_schema": JSON_SCHEMA},
        )
        
        # Parse and return the statistics
        result = json.loads(resp.choices[0].message.content)
        print("PARSED FIRST")
        return result
        
    except Exception as e:
        print(f"Error calculating fire statistics: {e}")
        raise


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
    for i in range(4):  # Generate 4 random burn areas
        lat, lng = random.choice(california_coords)
        
        #TODO: CHANGE AREA AND BURN DAYS
        # Generate random ID
        area_id = math.floor(lat * lng) * math.floor(0.2 * lng * lat) + math.floor(random.random() * 1000)
        
        # Generate random last burn date (within last 5 years)
        days_ago = random.randint(0, 1825)  # 5 years
        last_burn_date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
        
                
        # Generate threat ratings (random predictions from malco model)
        threat_rating = round(random.uniform(0.0, 1.0), 3)
        
        # Generate nearby towns (1-4 towns)
        num_towns = random.randint(1, 4)
        nearby_towns = location_to_neighbor_values(lat, lng)
        
        total_population = sum(town["population"] for town in nearby_towns)
        total_value_estimate = sum(town["value-estimate"] for town in nearby_towns)

        town = get_town(lat, lng)

        town_name = "N/A"

        if town:
            town_name = town.get("display_name")

        dump_data = {
            "coordinates": {
                "lat": lat,
                "lng": lng
            },
            "id": area_id,
            "last-burn-date": last_burn_date,
            "name": town_name,
            "weather": get_weather_data(lat, lng),
            "threat-rating": threat_rating,
            "nearby-towns": nearby_towns,
            "total-population": total_population,
            "total-value-estimate": total_value_estimate
        }

        # Generate statistics (all float values from 0-1)
        statistics = calculate_fire_statistics(dump_data)


        # Calculate preliminary feasibility score (average of all statistics)
        stat_values = list(statistics['statistics'].values())
        # Clamp the score to ensure it's between 0 and 1
        preliminary_feasability_score = 1 - (round(sum(stat_values) / len(stat_values), 3))

        burn_area = {
            "coordinates": {
                "lat": lat,
                "lng": lng
            },
            "id": area_id,
            "last-burn-date": last_burn_date,
            "name": town_name,
            "statistics": statistics['statistics'],
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

def main():
    """
    Generate the data and save it to a JSON file.
    """
    print("Generating burn area data...")
    burn_areas = generate_v1_dummy_data()
    
    v1_response = {
        "status": "success",
        "data": burn_areas
    }
    
    # Save to JSON file
    output_file = "precomputed_data.json"
    with open(output_file, 'w') as f:
        json.dump(v1_response, f, indent=2)
    
    print(f"Data generated and saved to {output_file}")
    print(f"Generated {len(burn_areas)} burn areas")

if __name__ == "__main__":
    main()

