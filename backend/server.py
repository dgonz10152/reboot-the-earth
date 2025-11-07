from flask import Flask, request, jsonify
from joblib import load
from joblib import Parallel, delayed
import os
import numpy as np
import pandas as pd
from flask_cors import CORS
# import backend.data_processing as dp  # <-- you’ll create this
# import backend.io_utils as ioutil      # <-- optional (for file handling)

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
def predict_area(file_path):
    """
    Given an input data file (CSV, JSON, etc.), extract features,
    make a prediction, and return results.
    """
    # import backend.data_processing as dp  # Uncomment when module is created
    # features = dp.extract_features(file_path)   # Your custom function
    # features = features.reindex(columns=feature_columns, fill_value=0)
    #
    # # Example: regression (priority score)
    # prediction = model.predict(features)[0]
    #
    # # Example: classification (high / medium / low priority)
    # if label_encoder:
    #     category = label_encoder.inverse_transform([int(round(prediction))])[0]
    # else:
    #     category = "priority_score"
    #
    # return {
    #     "file": os.path.basename(file_path),
    #     "prediction": float(prediction),
    #     "category": category
    # }
    
    # Placeholder until dp module is implemented
    return {
        "file": os.path.basename(file_path),
        "prediction": 0.5,
        "category": "not_implemented"
    }

# -------------------------------
# API Endpoint: Batch Predict
# -------------------------------
@app.route("/predict", methods=["POST"])
def predict_batch():
    """
    POST JSON payload:
    {
      "path": "/data/input",
      "files": ["region1.csv", "region2.csv"],
      "threshold": 0.7
    }
    """
    data = request.json
    folder = data["path"]
    files = data["files"]
    threshold = float(data.get("threshold", 0.5))

    # Run all predictions in parallel
    tasks = [delayed(predict_area)(os.path.join(folder, f)) for f in files]
    results = Parallel(n_jobs=-1, backend="threading")(tasks)

    # Optional: filter or categorize
    summary = {}
    for res in results:
        if res["prediction"] >= threshold:
            status = "high_priority"
        else:
            status = "low_priority"
        summary[status] = summary.get(status, 0) + 1

    return jsonify({
        "results": results,
        "summary": summary
    }), 200

# -------------------------------
# API Endpoint: Extract Features
# -------------------------------
@app.route("/features", methods=["POST"])
def extract_features():
    """
    Return the processed feature vector for a single file.
    """
    # import backend.data_processing as dp  # Uncomment when module is created
    # in_file = request.json["file"]
    # features = dp.extract_features(in_file)
    # return jsonify(features.to_dict(orient="records")[0]), 200
    
    # Placeholder until dp module is implemented
    return jsonify({"error": "Feature extraction not yet implemented"}), 501

# -------------------------------
# API Endpoint: Dummy Data
# -------------------------------
@app.route("/dummy", methods=["GET"])
def dummy_data():
    """
    Return dummy data for testing purposes.
    """
    dummy_response = {
        "status": "success",
        "message": "This is dummy data",
        "data": {
            "regions": [
                {
                    "id": "1",
                    "name": "North Ridge Valley",
                    "threatLevel": 5,
                    "lastBurnDate": "2024-03-15",
                    "coordinates": { "lat": 34.0522, "lng": -118.2437 },
                    "statistics": {
                        "dryness": 5,
                        "fuelLoad": 4,
                        "windSpeed": 5,
                        "vegetationDensity": 4,
                        "temperature": 4
                    },
                    "weatherForecast": "Hot and dry, high winds expected",
                    "region": "Northern"
                },
                {
                    "id": "2",
                    "name": "Coastal Pine Forest",
                    "threatLevel": 2,
                    "lastBurnDate": "2024-09-20",
                    "coordinates": { "lat": 34.1, "lng": -118.35 },
                    "statistics": {
                        "dryness": 2,
                        "fuelLoad": 3,
                        "windSpeed": 2,
                        "vegetationDensity": 3,
                        "temperature": 2
                    },
                    "weatherForecast": "Moderate conditions, light breeze",
                    "region": "Coastal"
                },
            ],
        }
    }
    return jsonify(dummy_response), 200

# -------------------------------
# Run the Server
# -------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5003)
