# BACKEND

Flask-based API server for wildfire prediction and location analysis.

## Setup

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Installation

1. Navigate to the backend directory:

   ```bash
   cd backend
   ```

2. Create a virtual environment (recommended):

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Environment Variables

Create a `.env` file in the `backend` directory with the following variables:

```env
OPEN_AI=your_openai_api_key_here
KEY=your_locationiq_api_key_here
```

### API Keys Required

- **OPEN_AI**: Your OpenAI API key for web research and risk scoring
  - Used for: `gpt-4o-mini-search-preview` and `gpt-4o-mini` models
  - Vector Store ID: `vs_690e81d520088191958d81df531fa352` (hardcoded in code)
- **KEY**: Your LocationIQ API key for reverse geocoding
  - Used for: Converting coordinates to location names

## Running the Server

Start the Flask development server:

```bash
python server.py
```

The server will run on `http://localhost:5000` by default.

## API Endpoints

### `/v0`

- **Method**: GET
- **Description**: Returns precomputed wildfire data
- **Response**: JSON object containing wildfire statistics and location data

### `/v1`

- **Method**: GET
- **Description**: Generates real-time wildfire risk assessment for a location
- **Query Parameters**:
  - `lat`: Latitude (float)
  - `lng`: Longitude (float)
- **Response**: JSON object with risk score, statistics, and recommendations

## Precomputed Data

The server loads precomputed data from `precomputed_data.json`. To regenerate this file:

```bash
python pre_compute.py
```

This script:

- Calculates fire statistics using OpenAI
- Fetches weather data from Open-Meteo API
- Retrieves location information using LocationIQ
- Generates threat ratings and risk assessments

## Dependencies

Key dependencies (see `requirements.txt` for full list):

- **Flask**: Web framework
- **flask-cors**: Cross-Origin Resource Sharing support
- **openai**: OpenAI API client
- **python-dotenv**: Environment variable management
- **requests**: HTTP library for external API calls
- **pandas**: Data manipulation
- **numpy**: Numerical computing
- **scikit-learn**: Machine learning utilities
- **joblib**: Model persistence

## Project Structure

```
backend/
├── server.py              # Main Flask application
├── pre_compute.py         # Precomputed data generation script
├── neighbors.py           # Location-to-neighbor values calculation
├── precomputed_data.json  # Precomputed wildfire data
├── cache/                 # API response cache
├── requirements.txt       # Python dependencies
└── .env                   # Environment variables (create this)
```

## Notes

- The server uses CORS to allow cross-origin requests from the frontend
- API responses are cached in the `cache/` directory to reduce API calls
- The OpenAI vector store ID is hardcoded in the codebase
- LocationIQ is used for reverse geocoding (coordinates to location names)
- Open-Meteo API is used for weather data (no API key required)
