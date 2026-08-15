"""
Сервис автобусов: локальная база маршрутов + GPS-симуляция.
"""
import time
import math
import threading
import requests

from config import OVERPASS_URL, KAZAN_OVERPASS_BBOX
from extensions import cache
from utils import haversine, format_distance


# Локальная справочная база маршрутов (примерные данные)
BUS_ROUTES = [
    {"id": "1", "number": "1", "name": "Автобус №1", "type": "bus",
     "route": "ЦУМ — Авиастроительный район",
     "stops": ["ЦУМ", "Площадь Тукая", "Татарстан", "Сайдашева", "Яшьлек",
               "Аметьево", "Сухая Река", "31-й квартал", "Авиастроительная"],
     "color": "#e74c3c", "interval_min": 10, "work_hours": "05:00-23:00"},
    {"id": "2", "number": "2", "name": "Автобус №2", "type": "bus",
     "route": "ЦУМ — Жилой массив Азино",
     "stops": ["ЦУМ", "Площадь Свободы", "Тукая", "Рихард Зорге",
               "Академика Сахарова", "Мавлетова", "Азино-1", "Азино-2"],
     "color": "#3498db", "interval_min": 8, "work_hours": "05:30-23:30"},
    {"id": "5", "number": "5", "name": "Автобус №5", "type": "bus",
     "route": "ЦУМ — Солнечный город",
     "stops": ["ЦУМ", "Площадь Тукая", "Восстания-Победилово",
               "Оренбургский тракт", "Солнечный город"],
     "color": "#9b59b6", "interval_min": 15, "work_hours": "05:30-22:30"},
    {"id": "15", "number": "15", "name": "Автобус №15", "type": "bus",
     "route": "Аметьево — ул. Гаврилова",
     "stops": ["Аметьево", "Сайдашева", "Татарстан", "Тукая",
               "Петербургская", "Баумана", "Гаврилова"],
     "color": "#f39c12", "interval_min": 7, "work_hours": "05:30-23:30"},
    {"id": "23", "number": "23", "name": "Автобус №23", "type": "bus",
     "route": "Аэропорт — ЦУМ",
     "stops": ["Аэропорт", "Больница", "Магистральная", "Яшьлек",
               "Сайдашева", "Тукая", "ЦУМ"],
     "color": "#e67e22", "interval_min": 20, "work_hours": "06:00-22:00"},
    {"id": "35", "number": "35", "name": "Автобус №35", "type": "bus",
     "route": "ЦУМ — Горки",
     "stops": ["ЦУМ", "Тукая", "Рихард Зорге", "Сахарова",
               "Гаврилова", "Горки-1", "Горки-2"],
     "color": "#d35400", "interval_min": 9, "work_hours": "05:30-23:00"},
    {"id": "37", "number": "37", "name": "Автобус №37", "type": "bus",
     "route": "ЦУМ — Азино",
     "stops": ["ЦУМ", "Тукая", "Рихард Зорге", "Мавлетова", "Азино"],
     "color": "#27ae60", "interval_min": 10, "work_hours": "05:00-23:30"},
    {"id": "47", "number": "47", "name": "Автобус №47", "type": "bus",
     "route": "ЦУМ — Кулон-2",
     "stops": ["ЦУМ", "Тукая", "Яшьлек", "Сахарова",
               "Академическая", "Кулон-1", "Кулон-2"],
     "color": "#2980b9", "interval_min": 12, "work_hours": "05:30-22:30"},
    {"id": "54", "number": "54", "name": "Автобус №54", "type": "bus",
     "route": "Аметьево — Жилкомбинат",
     "stops": ["Аметьево", "Сайдашева", "Тукая", "Гагарина", "Жилкомбинат"],
     "color": "#7f8c8d", "interval_min": 16, "work_hours": "05:00-22:30"},
    {"id": "63", "number": "63", "name": "Автобус №63", "type": "bus",
     "route": "ЦУМ — Аэропорт",
     "stops": ["ЦУМ", "Тукая", "Яшьлек", "Сухая Река",
               "Авиастроительная", "Аэропорт"],
     "color": "#e74c3c", "interval_min": 22, "work_hours": "06:00-22:00"},
    {"id": "72", "number": "72", "name": "Автобус №72", "type": "bus",
     "route": "ЦУМ — Солнечный город",
     "stops": ["ЦУМ", "Тукая", "Восстания", "Солнечный город"],
     "color": "#9b59b6", "interval_min": 14, "work_hours": "05:30-22:30"},
    {"id": "75", "number": "75", "name": "Автобус №75", "type": "bus",
     "route": "Универсиада-1 — ЦУМ",
     "stops": ["Универсиада-1", "Сахарова", "Рихард Зорге", "Тукая", "ЦУМ"],
     "color": "#f39c12", "interval_min": 11, "work_hours": "05:30-23:00"},
    {"id": "91", "number": "91", "name": "Автобус №91", "type": "bus",
     "route": "ЦУМ — Сухая Река",
     "stops": ["ЦУМ", "Тукая", "Аметьево", "Сухая Река"],
     "color": "#c0392b", "interval_min": 17, "work_hours": "05:30-22:30"},
]


# GPS-симуляция живых автобусов
SIMULATION_STATE = {}
SIMULATION_LOCK = threading.Lock()


def get_real_routes():
    """Загружает реальные маршруты из OSM (Overpass)."""
    cache_key = "buses:real:routes"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    query = f'''
    [out:json][timeout:60];
    (
      relation["route"="bus"]({KAZAN_OVERPASS_BBOX});
      node["highway"="bus_stop"]({KAZAN_OVERPASS_BBOX});
    );
    out body;
    >;
    out skel qt;
    '''
    try:
        r = requests.post(OVERPASS_URL, data={"data": query}, timeout=60,
                          headers={"User-Agent": "KazanNavigator/3.1"})
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        return {"error": f"Overpass недоступен: {e}", "fallback": BUS_ROUTES}

    nodes = {}
    routes = []
    stops = []

    for el in data.get("elements", []):
        if el["type"] == "node":
            nodes[el["id"]] = {"lat": el["lat"], "lon": el["lon"]}
            if el.get("tags", {}).get("highway") == "bus_stop":
                tags = el.get("tags", {})
                stops.append({
                    "id": el["id"],
                    "name": tags.get("name") or tags.get("name:ru") or "Остановка",
                    "lat": el["lat"], "lon": el["lon"],
                })
        elif el["type"] == "relation" and el.get("tags", {}).get("route") == "bus":
            tags = el.get("tags", {})
            members = el.get("members", [])
            path_coords = []
            stop_members = []
            for m in members:
                if m["type"] == "node" and m["ref"] in nodes:
                    n = nodes[m["ref"]]
                    if m.get("role") in ("stop", "stop_entry_only", "stop_exit_only"):
                        stop_members.append({
                            "id": m["ref"], "lat": n["lat"], "lon": n["lon"],
                            "name": next((s["name"] for s in stops if s["id"] == m["ref"]), "Остановка"),
                        })
                    path_coords.append([n["lat"], n["lon"]])
            if len(path_coords) < 3:
                continue
            ref = tags.get("ref") or tags.get("name") or "?"
            routes.append({
                "id": f"osm_{el['id']}",
                "ref": ref,
                "name": tags.get("name") or f"Автобус {ref}",
                "from": tags.get("from", ""),
                "to": tags.get("to", ""),
                "operator": tags.get("operator", ""),
                "colour": tags.get("colour") or "#fc3f1d",
                "path": path_coords,
                "stops": stop_members,
                "stops_count": len(stop_members),
            })

    routes.sort(key=lambda r: (r["ref"].isdigit(), r["ref"] if r["ref"].isdigit() else 999))
    response = {
        "routes": routes, "stops": stops,
        "routes_count": len(routes), "stops_count": len(stops),
        "source": "OpenStreetMap",
    }
    cache.set(cache_key, response)
    return response


def _init_simulation():
    """Инициализация GPS-симуляции."""
    global SIMULATION_STATE
    with SIMULATION_LOCK:
        if SIMULATION_STATE:
            return SIMULATION_STATE

        routes_data = cache.get("buses:real:routes")
        if not routes_data or "routes" not in routes_data:
            return {}

        now = time.time()
        sim = {}
        for route in routes_data["routes"]:
            path = route.get("path", [])
            if len(path) < 2:
                continue
            n_buses = max(1, min(6, len(path) // 15))
            buses = []
            for i in range(n_buses):
                phase = i / n_buses
                buses.append({
                    "id": f"{route['id']}_bus_{i}",
                    "route_id": route["id"],
                    "route_ref": route["ref"],
                    "route_name": route["name"],
                    "colour": route["colour"],
                    "phase": phase,
                    "direction": 1,
                    "speed": 0.0002 + (hash(route["id"] + str(i)) % 100) / 100 * 0.0002,
                    "last_update": now,
                })
            sim[route["id"]] = {"path": path, "buses": buses}
        SIMULATION_STATE = sim
        return sim


def _interpolate_path(path, phase):
    """Линейная интерполяция координаты по пути."""
    if not path:
        return 0, 0, 0
    if len(path) == 1:
        return path[0][0], path[0][1], 0
    n = len(path) - 1
    pos = phase * n
    i = int(pos)
    if i >= n:
        i = n - 1
    frac = pos - i
    p1, p2 = path[i], path[i + 1]
    lat = p1[0] + (p2[0] - p1[0]) * frac
    lon = p1[1] + (p2[1] - p1[1]) * frac
    heading = math.degrees(math.atan2(p2[0] - p1[0], p2[1] - p1[1]))
    return lat, lon, heading


def get_live_buses(route_id=None):
    """Возвращает позиции живых автобусов (симуляция)."""
    sim = _init_simulation()
    if not sim:
        return {"buses": [], "count": 0, "error": "Нет данных о маршрутах"}

    now = time.time()
    live_buses = []

    with SIMULATION_LOCK:
        routes_to_check = {route_id: sim[route_id]} if route_id and route_id in sim else sim
        for rid, route_sim in routes_to_check.items():
            path = route_sim["path"]
            if not path or len(path) < 2:
                continue
            for bus in route_sim["buses"]:
                elapsed = now - bus["last_update"]
                bus["phase"] += bus["speed"] * elapsed * bus["direction"]
                bus["last_update"] = now
                if bus["phase"] >= 1.0:
                    bus["phase"] = 1.0
                    bus["direction"] = -1
                elif bus["phase"] <= 0.0:
                    bus["phase"] = 0.0
                    bus["direction"] = 1
                lat, lon, heading = _interpolate_path(path, bus["phase"])
                live_buses.append({
                    "id": bus["id"], "route_id": bus["route_id"],
                    "route_ref": bus["route_ref"], "route_name": bus["route_name"],
                    "colour": bus["colour"], "lat": lat, "lon": lon,
                    "heading": heading,
                    "direction": "forward" if bus["direction"] == 1 else "backward",
                    "phase": round(bus["phase"], 4),
                })

    return {"buses": live_buses, "count": len(live_buses),
            "type": "live_simulation"}


def reset_simulation():
    """Сброс симуляции."""
    global SIMULATION_STATE
    with SIMULATION_LOCK:
        SIMULATION_STATE = {}
    return {"status": "reset"}


def search_buses(query):
    """Поиск автобусов по номеру/имени/остановке."""
    if not query:
        return BUS_ROUTES
    q = query.lower()
    results = []
    for b in BUS_ROUTES:
        if q in b["number"].lower() or q in b["name"].lower() or q in b["route"].lower():
            results.append(b)
            continue
        for stop in b.get("stops", []):
            if q in stop.lower():
                results.append(b)
                break
    return results
