"""
Парсит OSM-файлы Казани и создаёт локальную базу для поиска.
Поддерживает nodes И ways (с вычислением центроида).
SQLite с полнотекстовым поиском (FTS5).
"""
import osmium
import sqlite3
import sys
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "static" / "data"
OSM_FILES = [
    DATA_DIR / "kazan-poi.osm",      # POI + адреса
    DATA_DIR / "kazan-roads.osm",    # Дороги + автобусы
]
DB_FILE = DATA_DIR / "kazan_search.db"


class SearchBuilder(osmium.SimpleHandler):
    def __init__(self):
        super().__init__()
        self.places = []
        self.count = 0
        self.way_count = 0

    def _categorize(self, tags):
        """Определяет категорию и иконку по тегам OSM."""
        if "amenity" in tags:
            amenity = tags["amenity"]
            icon_map = {
                "restaurant": "utensils", "cafe": "mug-hot", "fast_food": "burger",
                "bar": "wine-glass", "pub": "beer-mug-empty",
                "fuel": "gas-pump", "pharmacy": "prescription-bottle-medical",
                "hospital": "hospital", "clinic": "hospital",
                "bank": "building-columns", "atm": "credit-card",
                "parking": "square-parking", "school": "school",
                "university": "graduation-cap", "cinema": "film",
                "theatre": "masks-theater", "place_of_worship": "mosque",
                "police": "shield-halved", "post_office": "envelope",
                "library": "book", "marketplace": "store",
            }
            return amenity, icon_map.get(amenity, "circle-dot")
        if "shop" in tags:
            shop = tags["shop"]
            icon_map = {
                "supermarket": "cart-shopping", "convenience": "store",
                "clothes": "shirt", "bakery": "bread-slice",
                "electronics": "laptop", "mobile_phone": "mobile-screen",
                "books": "book", "jewelry": "gem", "alcohol": "wine-bottle",
                "kiosk": "store", "mall": "cart-shopping",
            }
            return "shop_" + shop, icon_map.get(shop, "bag-shopping")
        if "highway" in tags:
            if tags["highway"] == "bus_stop":
                return "bus_stop", "bus"
            return "road", "road"
        if "public_transport" in tags:
            return "transport", "bus"
        if "tourism" in tags:
            t = tags["tourism"]
            icon_map = {
                "attraction": "camera", "museum": "landmark",
                "hotel": "bed", "viewpoint": "binoculars",
                "artwork": "palette", "gallery": "image",
            }
            return "tourism_" + t, icon_map.get(t, "camera")
        if "leisure" in tags:
            l = tags["leisure"]
            icon_map = {
                "park": "tree", "garden": "seedling",
                "playground": "children", "sports_centre": "dumbbell",
                "stadium": "futbol", "swimming_pool": "water-ladder",
            }
            return "leisure_" + l, icon_map.get(l, "tree")
        if "railway" in tags:
            r = tags["railway"]
            if r in ("station", "tram_stop"):
                return "railway_" + r, "train"
        if "building" in tags:
            return "building", "building"
        if "place" in tags:
            p = tags["place"]
            icon_map = {"city": "city", "town": "city", "suburb": "location-dot"}
            return "place_" + p, icon_map.get(p, "location-dot")
        if "office" in tags:
            return "office", "briefcase"
        if "natural" in tags:
            return "natural_" + tags["natural"], "tree"
        if "historic" in tags:
            return "historic", "landmark"
        return "other", "map-pin"

    def _extract_place(self, tags, lat, lon):
        if not tags:
            return None
        # Имя
        name = tags.get("name") or tags.get("name:ru") or tags.get("brand") or tags.get("operator")
        if not name:
            # Адрес?
            street = tags.get("addr:street")
            house = tags.get("addr:housenumber")
            if street and house:
                name = f"{street}, {house}"
            elif street:
                name = street
            else:
                return None

        # Категория и иконка
        category, icon = self._categorize(tags)

        # Адрес
        street = tags.get("addr:street", "")
        house = tags.get("addr:housenumber", "")
        addr = ""
        if street:
            addr = street + (", " + house if house else "")

        return (name, addr, category, icon, lat, lon)

    def node(self, n):
        tags = n.tags
        if not tags:
            return
        place = self._extract_place(tags, n.location.lat, n.location.lon)
        if place:
            self.places.append(place)
            self.count += 1

    def way(self, w):
        tags = w.tags
        if not tags or not w.nodes:
            return
        # Только с именем или тегами
        name = tags.get("name") or tags.get("name:ru")
        if not name and "amenity" not in tags and "shop" not in tags and "highway" not in tags:
            return
        # Вычисляем центроид по нодам
        try:
            coords = []
            for node in w.nodes:
                if node.lat and node.lon:
                    coords.append((node.lat, node.lon))
            if not coords:
                return
            lat = sum(c[0] for c in coords) / len(coords)
            lon = sum(c[1] for c in coords) / len(coords)
            place = self._extract_place(tags, lat, lon)
            if place:
                self.places.append(place)
                self.way_count += 1
        except Exception:
            return


def build_db():
    for f in OSM_FILES:
        if not f.exists():
            print(f"WARN: {f} не найден, пропускаю")

    print("Парсю OSM файлы...")
    builder = SearchBuilder()
    for f in OSM_FILES:
        if f.exists():
            print(f"  {f.name} ({f.stat().st_size / 1024 / 1024:.1f} MB)")
            builder.apply_file(str(f), locations=True)

    print(f"\nНайдено мест: {builder.count} (nodes: {builder.count - builder.way_count}, ways: {builder.way_count})")

    # Удаляем дубликаты (по имени + координатам)
    seen = set()
    unique = []
    for p in builder.places:
        key = (p[0].lower(), round(p[4], 5), round(p[5], 5))
        if key not in seen:
            seen.add(key)
            unique.append(p)
    print(f"Уникальных: {len(unique)}")

    # Создаём БД
    if DB_FILE.exists():
        DB_FILE.unlink()

    print(f"\nСоздаю SQLite: {DB_FILE.name}")
    conn = sqlite3.connect(str(DB_FILE))
    conn.execute("""
        CREATE TABLE places (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            address TEXT,
            category TEXT,
            icon TEXT,
            lat REAL,
            lon REAL
        )
    """)
    conn.execute("""
        CREATE VIRTUAL TABLE places_fts USING fts5(
            name, address, category,
            content='places', content_rowid='id',
            tokenize='unicode61'
        )
    """)
    conn.execute("CREATE INDEX idx_places_cat ON places(category)")
    conn.execute("CREATE INDEX idx_places_lat ON places(lat)")
    conn.execute("CREATE INDEX idx_places_lon ON places(lon)")

    print("Записываю в БД...")
    cur = conn.cursor()
    cur.executemany(
        "INSERT INTO places (name, address, category, icon, lat, lon) VALUES (?, ?, ?, ?, ?, ?)",
        unique,
    )
    conn.execute("""
        INSERT INTO places_fts (rowid, name, address, category)
        SELECT id, name, address, category FROM places
    """)
    conn.commit()

    # Статистика
    total = cur.execute("SELECT COUNT(*) FROM places").fetchone()[0]
    cats = cur.execute("""
        SELECT category, COUNT(*) FROM places GROUP BY category ORDER BY COUNT(*) DESC LIMIT 20
    """).fetchall()

    print(f"\nИтого записей: {total}")
    print("Топ категорий:")
    for cat, cnt in cats:
        print(f"  {cat}: {cnt}")

    conn.close()
    db_size = DB_FILE.stat().st_size / 1024 / 1024
    print(f"\nРазмер БД: {db_size:.1f} MB")
    print(f"Готово: {DB_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(build_db())
