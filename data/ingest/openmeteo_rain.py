import httpx, csv

OUT = "data/processed/openmeteo_rain_grid_1990_2024.csv"
BASE = "https://archive-api.open-meteo.com/v1/era5"
LATS = [lat for lat in range(-10, 35, 5)]
LONS = [lon for lon in range(60, 95, 5)]
YEARS = list(range(1990, 2025))

def url(lat, lon, y):
    return f"{BASE}?latitude={lat}&longitude={lon}&start_date={y}-01-01&end_date={y}-12-31&daily=precipitation_sum&timezone=UTC"

def main():
    with open(OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["year","month","lat","lon","rainfall_mm","disaster_type","event"])
        with httpx.Client(timeout=60) as client:
            for lat in LATS:
                for lon in LONS:
                    for y in YEARS:
                        r = client.get(url(lat, lon, y))
                        if r.status_code != 200:
                            continue
                        js = r.json()
                        days = js.get("daily", {}).get("precipitation_sum", [])
                        times = js.get("daily", {}).get("time", [])
                        monthly = {}
                        for t, val in zip(times, days):
                            m = int(t.split("-")[1])
                            monthly[m] = monthly.get(m, 0.0) + float(val or 0.0)
                        for m, total in monthly.items():
                            event = 1 if total >= 300 else 0
                            w.writerow([y, m, lat, lon, round(total, 2), "flood", event])
                    print(f"[ok] {lat}, {lon}")

if __name__ == "__main__":
    main()
