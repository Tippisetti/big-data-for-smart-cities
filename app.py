import os
import requests
import pandas as pd
from joblib import load
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from models.features import engineer_features, FEATURE_COLUMNS, postprocess_score
import warnings

# --- Suppress harmless sklearn warning ---
warnings.filterwarnings("ignore", message="X does not have valid feature names")

# --- Flask setup ---
app = Flask(__name__)
CORS(app)

MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "model.joblib")
_model = None
_scaler = None

OPEN_METEO = "https://api.open-meteo.com/v1/forecast"

# --- Model loader ---
def get_model():
    global _model, _scaler
    if _model is None:
        loaded = load(MODEL_PATH)  # supports (clf, scaler)
        if isinstance(loaded, tuple):
            _model, _scaler = loaded
        else:
            _model, _scaler = loaded, None
        print(f"[✓] Model loaded from {MODEL_PATH}")
    return _model, _scaler

# --- Routes ---
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/health")
def health():
    return jsonify({"ok": True})

@app.route("/api/predict", methods=["POST"])
def predict():
    data = request.get_json(force=True)

    def sfloat(v, d=0.0):
        try:
            return float(v)
        except (TypeError, ValueError):
            return d

    # sanitize inputs (empty strings → 0)
    payload = {
        "lat": sfloat(data.get("lat")),
        "lon": sfloat(data.get("lon")),
        "month": int(data.get("month", 1)),
        "rainfall_mm": sfloat(data.get("rainfall_mm")),
        "seismic_richter": sfloat(data.get("seismic_richter")),
        "river_level_m": sfloat(data.get("river_level_m")),
        "soil_moisture_pct": sfloat(data.get("soil_moisture_pct")),
        "sat_cloud_pct": sfloat(data.get("sat_cloud_pct")),
        "wind_speed_kmh": sfloat(data.get("wind_speed_kmh")),
        "temperature_c": sfloat(data.get("temperature_c")),
        "slope_deg": sfloat(data.get("slope_deg")),
        "vegetation_dryness": sfloat(data.get("vegetation_dryness")),
    }

    try:
        df = engineer_features(pd.DataFrame([payload]))
        model, scaler = get_model()

        X = df[FEATURE_COLUMNS].values
        if scaler is not None:
            X = scaler.transform(X)

        prob = float(model.predict_proba(X)[:, 1][0])
        post = postprocess_score(prob)

        # --- Multi-hazard detection logic ---
        d = "Normal"
        if payload["rainfall_mm"] > 120 or payload["river_level_m"] > 3.5:
            d = "Flood"
        elif payload["seismic_richter"] >= 4.5:
            d = "Earthquake"
        elif payload["soil_moisture_pct"] > 50 and payload["slope_deg"] > 30:
            d = "Landslide"
        elif payload["wind_speed_kmh"] > 120:
            d = "Cyclone"
        elif payload["temperature_c"] > 42 and payload["vegetation_dryness"] > 80:
            d = "Wildfire"
        elif payload["soil_moisture_pct"] < 10 and payload["rainfall_mm"] < 10:
            d = "Drought"

        return jsonify({
            "ok": True,
            "probability": prob,
            "severity": post["severity"],
            "color": post["color"],
            "predicted_disaster": d,
            "advice": advice_for(d, post["severity"]),
        })

    except Exception as e:
        print("[✗] Prediction error:", e)
        return jsonify({"ok": False, "error": str(e)})

# --- Disaster advice generator ---
def advice_for(disaster, severity):
    tips = {
        "Flood": "Move to higher ground; avoid rivers & low bridges.",
        "Earthquake": "Drop, Cover & Hold On; stay away from glass and power lines.",
        "Landslide": "Avoid steep slopes; watch for cracks and unusual water flow.",
        "Cyclone": "Stay indoors; secure windows; keep emergency kit ready.",
        "Wildfire": "Avoid dry forests; prepare to evacuate; keep water ready.",
        "Drought": "Conserve water; avoid open flames; stay hydrated.",
        "Normal": "No immediate threat. Stay alert and informed."
    }
    if severity in ["HIGH", "EXTREME"] and disaster != "Normal":
        return "⚠️ " + tips.get(disaster, tips["Normal"])
    return "✅ " + tips.get(disaster, tips["Normal"])

# --- Weather API ---
@app.route("/api/weather")
def weather():
    lat = request.args.get("lat")
    lon = request.args.get("lon")
    try:
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": ["temperature_2m", "precipitation", "wind_speed_10m", "cloud_cover"],
            "timezone": "auto"
        }
        r = requests.get(OPEN_METEO, params=params, timeout=10)
        r.raise_for_status()
        cur = r.json().get("current", {})
        return jsonify({"ok": True, "data": cur})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

# --- Run app ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"[RUN] Disaster Early Warning backend on {port}")
    app.run(host="0.0.0.0", port=port, debug=True)
