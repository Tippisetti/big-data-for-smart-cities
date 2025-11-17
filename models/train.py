import os
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report
from joblib import dump

BASE = os.path.dirname(__file__)
DATA_PATH = os.path.join(BASE, "../data/samples/synthetic_disasters_1990_2024.csv")
MODEL_PATH = os.path.join(BASE, "model.joblib")

os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)

# --- Synthetic multi-hazard dataset (1990–2024 like) ---
np.random.seed(42)
rows = 2000
df = pd.DataFrame({
    "rainfall_mm":        np.random.gamma(5, 20, rows),
    "seismic_richter":    np.random.uniform(0, 7, rows),
    "river_level_m":      np.random.uniform(0, 6, rows),
    "soil_moisture_pct":  np.random.uniform(5, 90, rows),
    "sat_cloud_pct":      np.random.uniform(10, 100, rows),
    "wind_speed_kmh":     np.random.uniform(5, 200, rows),
    "temperature_c":      np.random.uniform(-5, 50, rows),
    "slope_deg":          np.random.uniform(0, 60, rows),
    "vegetation_dryness": np.random.uniform(0, 100, rows),
    "month":              np.random.randint(1, 13, rows),
})

def rule_disaster(r):
    if r.rainfall_mm > 120 or r.river_level_m > 4:                  return "Flood"
    if r.seismic_richter > 5:                                       return "Earthquake"
    if r.wind_speed_kmh > 130:                                      return "Cyclone"
    if r.temperature_c > 42 and r.vegetation_dryness > 80:          return "Wildfire"
    if r.slope_deg > 35 and r.soil_moisture_pct > 50:               return "Landslide"
    if r.soil_moisture_pct < 10 and r.rainfall_mm < 10:             return "Drought"
    return "Normal"

df["disaster_type"] = df.apply(rule_disaster, axis=1)
df["risk_label"] = (df["disaster_type"] != "Normal").astype(int)

# --- Train ---
X = df.drop(columns=["disaster_type", "risk_label"])
y = df["risk_label"]

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

X_tr, X_te, y_tr, y_te = train_test_split(X_scaled, y, test_size=0.2, random_state=42, stratify=y)
clf = RandomForestClassifier(n_estimators=250, max_depth=10, min_samples_split=4, random_state=42)
clf.fit(X_tr, y_tr)

print(classification_report(y_te, clf.predict(X_te)))
dump((clf, scaler), MODEL_PATH)
print(f"[✓] Model saved → {MODEL_PATH}")
