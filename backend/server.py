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
