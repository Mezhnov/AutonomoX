"""
Конфигурация приложения.
Все настройки в одном месте — удобно для разных окружений.
"""
from pathlib import Path
import os


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "static" / "data"

# Flask
SECRET_KEY = os.environ.get("SECRET_KEY", "kazan-nav-dev-secret-change-in-prod")
DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", 5000))

# Казань — координаты и границы
KAZAN_CENTER = (55.796127, 49.106414)
KAZAN_BBOX = "48.95,55.85,49.35,55.75"  # left,top,right,bottom (Nominatim)
KAZAN_OVERPASS_BBOX = "55.72,48.95,55.86,49.30"  # south,west,north,east
KAZAN_BOUNDS = [[55.68, 48.90], [55.90, 49.40]]  # Leaflet maxBounds
KAZAN_RADIUS_M = 30000  # 30 км — считаем "в Казани"

# Базы данных
DB_PATH = DATA_DIR / "navigator.db"            # SQLite: избранное + история
LOCAL_SEARCH_DB = DATA_DIR / "kazan_search.db" # SQLite FTS5: поиск мест
ROUTING_GRAPH = DATA_DIR / "kazan_graph.pkl"   # NetworkX граф дорог

# Внешние API (с fallback)
NOMINATIM_URL = "https://nominatim.openstreetmap.org"
NOMINATIM_HEADERS = {"User-Agent": "KazanNavigator/3.1 (contact@kazan-nav.ru)"}
OSRM_URL = "https://router.project-osrm.org/route/v1"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# Кэш
CACHE_TTL = 86400  # 24 часа

# Скорости по типам дорог (км/ч) — для локального роутинга
ROAD_SPEEDS = {
    "motorway": 90, "trunk": 70, "primary": 60, "secondary": 50,
    "tertiary": 40, "unclassified": 30, "residential": 25,
    "service": 15, "living_street": 20,
    "motorway_link": 50, "trunk_link": 40, "primary_link": 35,
    "secondary_link": 30, "tertiary_link": 25,
}

# Расчёт топлива
FUEL_CONSUMPTION = 8.0     # л/100км
FUEL_PRICE = 55            # руб/л (АИ-95, Казань 2026)
