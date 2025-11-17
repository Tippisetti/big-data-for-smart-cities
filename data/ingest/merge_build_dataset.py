import numpy as np
import pandas as pd
import os

RAIN = "data/processed/openmeteo_rain_grid_1990_2024.csv"
QUAKE = "data/processed/usgs_quakes_1990_2024.csv"
OUT  = "data/samples/realish_disasters_1990_2024.csv"

def bin5(x): return int(round(x / 5.0) * 5)

if __name__ == "__main__":
    dfs = []

    if os.path.exists(RAIN):
        df_r = pd.read_csv(RAIN)
    else:
        # minimal fallback so the script always produces something
        df_r = pd.DataFrame({
            "year":[2024]*6, "month":[6,7,8,9,10,11],
            "lat":[13,13,18,18,23,23], "lon":[77,77,77,77,77,77],
            "rainfall_mm":[50,120,360,40,20,15], "disaster_type":["flood"]*6, "event":[0,0,1,0,0,0]
        })

    if os.path.exists(QUAKE):
        df_q = pd.read_csv(QUAKE)
        df_q["lat"] = df_q["lat"].apply(bin5)
        df_q["lon"] = df_q["lon"].apply(bin5)
        agg_q = (
            df_q.groupby(["year","month","lat","lon"], as_index=False)
                .agg(seismic_richter=("seismic_richter","max"),
                     quake_event=("event","max"))
        )
    else:
        agg_q = pd.DataFrame(columns=["year","month","lat","lon","seismic_richter","quake_event"])

    df = pd.merge(df_r, agg_q, on=["year","month","lat","lon"], how="left")
    df["seismic_richter"] = pd.to_numeric(df["seismic_richter"], errors="coerce").fillna(0)
    df["quake_event"] = pd.to_numeric(df["quake_event"], errors="coerce").fillna(0)

    # crude engineered proxies
    df["river_level_m"] = (df["rainfall_mm"] / 100).clip(0, 6)
    df["soil_moisture_pct"] = df["rainfall_mm"].rolling(2, min_periods=1).mean().clip(0, 80)
    df["sat_cloud_pct"] = (df["rainfall_mm"] * 0.25).clip(0, 100)

    # extra indicators (randomized placeholders; swap with real feeds later)
    rng = np.random.default_rng(42)
    df["wind_speed_kmh"] = rng.uniform(0, 180, len(df))           # cyclone proxy
    df["temperature_c"] = rng.uniform(15, 45, len(df))            # drought proxy
    df["slope_deg"] = rng.uniform(0, 45, len(df))                 # landslide proxy
    df["vegetation_dryness"] = rng.uniform(0, 100, len(df))       # drought proxy

    # label by strongest signal (heuristic)
    def classify(r):
        if r["seismic_richter"] >= 5.5: return "earthquake"
        if r["rainfall_mm"] >= 350:     return "flood"
        if r["wind_speed_kmh"] >= 130:  return "cyclone"
        if r["slope_deg"] > 30 and r["soil_moisture_pct"] > 60: return "landslide"
        if r["temperature_c"] > 38 and r["vegetation_dryness"] > 70: return "drought"
        return "normal"

    df["disaster_type"] = df.apply(classify, axis=1)
    df["event"] = (df["disaster_type"] != "normal").astype(int)

    cols = [
        "year","month","lat","lon",
        "rainfall_mm","seismic_richter","river_level_m","soil_moisture_pct","sat_cloud_pct",
        "wind_speed_kmh","temperature_c","slope_deg","vegetation_dryness",
        "disaster_type","event"
    ]
    df[cols].to_csv(OUT, index=False)
    print(f"[done] {OUT}  rows={len(df)}")
