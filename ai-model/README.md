# AI MODEL

Machine learning model for wildfire prediction using California wildfire data.

## Setup

### Prerequisites

- Python 3.8 or higher
- Jupyter Notebook (for running the notebook)
- pip (Python package manager)

### Installation

1. Navigate to the ai-model directory:

   ```bash
   cd ai-model
   ```

2. Create a virtual environment (recommended):

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install pandas numpy matplotlib seaborn scikit-learn joblib jupyter
   ```

## Data Requirements

### Dataset

- **File**: `California_Wildfire_Features_105K_Imbalanced.csv`
- **Size**: ~105,000 samples
- **Fire Rate**: ~5% (1:20 ratio of fires to non-fires)
- **Format**: CSV with wildfire features and target variable

### Required Data Files

Ensure the following file is present in the `ai-model` directory:

- `California_Wildfire_Features_105K_Imbalanced.csv` - Main training dataset

## Running the Model

### Option 1: Jupyter Notebook

1. Start Jupyter Notebook:

   ```bash
   jupyter notebook
   ```

2. Open `super_model.ipynb`

3. Run all cells to:
   - Load and analyze the dataset
   - Engineer features (dist_from_coast, temp_precip_ratio, vegetation_dryness)
   - Train Random Forest and Gradient Boosting models
   - Evaluate model performance
   - Generate visualizations

### Option 2: Python Script

Convert the notebook to a Python script and run:

```bash
jupyter nbconvert --to script super_model.ipynb
python super_model.py
```

## Model Details

### Model Architecture

- **Primary Model**: Random Forest Classifier (Calibrated)
- **Alternative**: Gradient Boosting Classifier
- **Calibration**: CalibratedClassifierCV for probability calibration

### Features

The model uses 16 engineered features:

1. NDVI (Normalized Difference Vegetation Index)
2. LST (Land Surface Temperature)
3. Precipitation
4. Elevation
5. Wind Speed
6. Evapotranspiration
7. Distance to Roads (km)
8. Distance to Urban Areas (km)
9. Slope
10. Temperature-Precipitation Ratio
11. Precipitation Deficit
12. Vegetation Dryness
13. Fire Weather Index
14. Wind-Dry Vegetation Index
15. Extreme Heat
16. Severe Drought

### Optimization Strategy

The model is optimized for **recall** (detecting fires):

- **Class Weights**: 1.5x aggressive weighting (prioritize fire detection)
- **Cost Model**: $150K per missed fire
- **Threshold Optimization**: Multi-strategy favoring recall
- **Requirements**:
  - Minimum Recall: ≥70%
  - Minimum Precision: ≥40%
  - Maximum Alert Rate: ≤12%

### Model Performance

Based on `model-results.md`:

- **Recall**: 77.8% ✅
- **Precision**: 45.0% ✅
- **Alert Rate**: 8.6% ✅
- **ROI**: ~$507 Million in prevented fire damage

## Output Files

After training, the model generates:

- `wildfire_production_model.pkl` - Trained and calibrated model
- `wildfire_scaler.pkl` - Feature scaling parameters
- `feature_names.pkl` - Feature list and order
- `deployment_config.pkl` - Threshold and operational parameters
- `wildfire_realistic_imbalanced.png` - Performance visualizations

## Dependencies

Key Python packages required:

- **pandas**: Data manipulation and analysis
- **numpy**: Numerical computing
- **matplotlib**: Plotting and visualization
- **seaborn**: Statistical data visualization
- **scikit-learn**: Machine learning algorithms
  - RandomForestClassifier
  - GradientBoostingClassifier
  - CalibratedClassifierCV
- **joblib**: Model persistence (saving/loading models)

## Project Structure

```
ai-model/
├── super_model.ipynb                    # Main training notebook
├── California_Wildfire_Features_105K_Imbalanced.csv  # Training dataset
├── model-results.md                     # Performance documentation
├── FHSZ_SRA_LRA_Combined_*.geojson     # Fire hazard zone data (optional)
├── nasa_firms.json                      # NASA FIRMS data (optional)
└── README.md                            # This file
```

## Model Usage

### Loading the Trained Model

```python
import joblib

# Load the model and scaler
model = joblib.load('wildfire_production_model.pkl')
scaler = joblib.load('wildfire_scaler.pkl')

# Prepare features (16 features in correct order)
features = prepare_features(your_data)

# Scale features
scaled_features = scaler.transform(features)

# Predict probability
probability = model.predict_proba(scaled_features)[:, 1]

# Apply threshold (0.06 for production)
prediction = (probability >= 0.06).astype(int)
```

### Feature Engineering

The model requires engineered features. Key engineered features include:

- `dist_from_coast`: Distance from coastline
- `temp_precip_ratio`: Temperature to precipitation ratio
- `vegetation_dryness`: Vegetation dryness index

See the notebook for complete feature engineering pipeline.

## Notes

- The model is trained on California-specific data
- Performance may vary for other regions
- Model requires all 16 features in the correct order
- Threshold of 0.06 is optimized for production deployment
- The model prioritizes recall over precision to catch more fires

## References

- See `model-results.md` for detailed performance metrics and deployment guidelines
- Model meets all deployment requirements (recall ≥70%, precision ≥40%, alert rate ≤12%)
