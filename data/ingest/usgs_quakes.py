import httpx, time, csv
from datetime import datetime

OUT = "data/processed/usgs_quakes_1990_2024.csv"

def fetch_year(year: int):
    params = {
        "format": "geojson",
        "starttime": f"{year}-01-01",
        "endtime": f"{year}-12-31",
        "minmagnitude": 3.0,
        "orderby": "time-asc",
        "limit": 20000,
    }
    with httpx.Client(timeout=60) as client:
        r = client.get("https://earthquake.usgs.gov/fdsnws/event/1/query", params=params)
        r.raise_for_status()
        return r.json()

def main():
    years = list(range(1990, 2025))
    with open(OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["year","month","lat","lon","seismic_richter","depth_km","place","disaster_type","event"])
        for y in years:
            try:
                data = fetch_year(y)
            except Exception as e:
                print(f"[warn] {y}: {e}")
                continue
            feats = data.get("features", [])
            for ft in feats:
                props = ft.get("properties", {})
                geom = ft.get("geometry", {})
                coords = geom.get("coordinates", [None, None, None])
                if not coords or coords[1] is None:
                    continue
                t = props.get("time")
                if not t:
                    continue
                dt = datetime.utcfromtimestamp(int(t/1000))
                mag = props.get("mag") or 0.0
                depth = coords[2] if len(coords) > 2 else 0
                event = 1 if mag >= 5.0 else 0
                w.writerow([dt.year, dt.month, coords[1], coords[0], mag, depth, props.get("place",""), "earthquake", event])
            print(f"[ok] {y}: {len(feats)}")
            time.sleep(0.5)

if __name__ == "__main__":
    main()
