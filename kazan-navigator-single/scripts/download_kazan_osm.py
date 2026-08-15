"""
Скачивает OSM-данные Казани через Overpass API.
Только важные типы данных (дороги, здания, остановки, маршруты) — не весь город.
Это быстрее и меньше по размеру.
"""
import requests
import sys
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent.parent / "static" / "data"
OUT_DIR.mkdir(parents=True, exist_ok=True)

BBOX = "55.65,48.85,55.92,49.45"

QUERY = f"""
[out:xml][timeout:300];
(
  way["highway"]({BBOX});
  node["highway"="bus_stop"]({BBOX});
  node["public_transport"]({BBOX});
  relation["route"="bus"]({BBOX});
  node["amenity"~"restaurant|cafe|fast_food|bar|pub|fuel|pharmacy|hospital|bank|atm|parking|school|university|cinema|theatre"]({BBOX});
  node["shop"]({BBOX});
  node["tourism"~"attraction|museum|hotel|viewpoint|artwork|gallery"]({BBOX});
  node["leisure"~"park|garden|playground|sports_centre|stadium"]({BBOX});
  way["leisure"~"park|garden|playground"]({BBOX});
  way["building"]({BBOX});
);
out body;
>;
out skel qt;
"""

def main():
    out_file = OUT_DIR / "kazan.osm"
    print(f"Скачиваю OSM-данные Казани в {out_file}...")
    print(f"Bounding box: {BBOX}")
    print(f"Это займёт 2-5 минут...")

    servers = [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
        "https://overpass.openstreetmap.fr/api/interpreter",
    ]

    for i, server in enumerate(servers, 1):
        print(f"\nПопытка {i}/{len(servers)}: {server}")
        try:
            r = requests.post(
                server,
                data={"data": QUERY},
                timeout=300,
                headers={"User-Agent": "KazanNavigator/3.1"},
            )
            if r.status_code == 200 and r.text:
                size_mb = len(r.content) / 1024 / 1024
                print(f"  OK! Размер: {size_mb:.1f} MB")
                with open(out_file, "wb") as f:
                    f.write(r.content)
                print(f"  Сохранено в {out_file}")
                nodes = r.text.count("<node")
                ways = r.text.count("<way")
                rels = r.text.count("<relation")
                print(f"  Nodes: {nodes}, Ways: {ways}, Relations: {rels}")
                return 0
            else:
                print(f"  HTTP {r.status_code}")
        except Exception as e:
            print(f"  Error: {e}")

    print("\nВсе серверы Overpass недоступны.")
    print("Альтернатива — Geofabrik + osmium:")
    print("  https://download.geofabrik.de/russia/volga-fed-district-latest.osm.pbf")
    print("  osmium extract --bbox=48.85,55.65,49.45,55.92 volga.osm.pbf kazan.osm.pbf")
    return 1

if __name__ == "__main__":
    sys.exit(main())
