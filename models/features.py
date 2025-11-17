import numpy as np
import pandas as pd

# Base feature order the model expects (no scaler columns here)
FEATURE_COLUMNS = [
    "rainfall_mm", "seismic_richter", "river_level_m",
    "soil_moisture_pct", "sat_cloud_pct", "wind_speed_kmh",
    "temperature_c", "slope_deg", "vegetation_dryness", "month"
]

def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # keep original columns + (optional) cyclic encodings if you want
    # model uses FEATURE_COLUMNS, so these extras won't break anything
    df["sin_month"] = np.sin(2 * np.pi * df["month"] / 12)
    df["cos_month"] = np.cos(2 * np.pi * df["month"] / 12)
    return df

def postprocess_score(prob: float):
    if prob < 0.30:   return {"severity": "LOW",     "color": "#22c55e"}
    if prob < 0.60:   return {"severity": "MEDIUM",  "color": "#facc15"}
    if prob < 0.85:   return {"severity": "HIGH",    "color": "#f97316"}
    return {"severity": "EXTREME", "color": "#dc2626"}
