"""
Сервис маршрутизации: локальный NetworkX + OSRM fallback.
"""
import pickle
import networkx as nx
import requests

from config import ROUTING_GRAPH, OSRM_URL, KAZAN_RADIUS_M, KAZAN_CENTER, ROAD_SPEEDS
from extensions import cache
from utils import (haversine, format_distance, format_duration,
                   estimate_fuel, estimate_calories)


_ROUTING_GRAPH = None
_GRAPH_LOADED = False


def get_routing_graph():
    """Ленивая загрузка графа дорог."""
    global _ROUTING_GRAPH, _GRAPH_LOADED
    if _GRAPH_LOADED:
        return _ROUTING_GRAPH
    if not ROUTING_GRAPH.exists():
        _GRAPH_LOADED = True
        return None
    try:
        with open(ROUTING_GRAPH, "rb") as f:
            _ROUTING_GRAPH = pickle.load(f)
        _GRAPH_LOADED = True
        print(f"  Граф загружен: {_ROUTING_GRAPH.number_of_nodes()} нод, "
              f"{_ROUTING_GRAPH.number_of_edges()} рёбер")
        return _ROUTING_GRAPH
    except Exception as e:
        print(f"  Ошибка загрузки графа: {e}")
        _GRAPH_LOADED = True
        return None


def find_nearest_node(graph, lat, lon):
    """Находит ближайшую ноду в графе к координате."""
    best_node = None
    best_dist = float("inf")
    for node_id, data in graph.nodes(data=True):
        d = haversine(lat, lon, data["lat"], data["lon"])
        if d < best_dist:
            best_dist = d
            best_node = node_id
            if d < 20:
                break
    return best_node, best_dist


def route_local(start_lat, start_lon, end_lat, end_lon):
    """
    Локальный расчёт маршрута через NetworkX.
    Без интернета, без Docker.
    """
    graph = get_routing_graph()
    if not graph:
        return {"error": "Граф дорог не построен"}

    start_node, start_dist = find_nearest_node(graph, start_lat, start_lon)
    end_node, end_dist = find_nearest_node(graph, end_lat, end_lon)
    if not start_node or not end_node:
        return {"error": "Не найдены ближайшие дороги"}

    try:
        path = nx.shortest_path(graph, start_node, end_node, weight="time")
    except nx.NetworkXNoPath:
        return {"error": "Маршрут не найден (нет связи между точками)"}
    except nx.NodeNotFound:
        return {"error": "Узел не найден в графе"}

    coords = []
    total_distance = 0
    total_time = 0
    steps = []
    current_street = None

    for node_id in path:
        node_data = graph.nodes[node_id]
        coords.append([node_data["lat"], node_data["lon"]])

    for i in range(len(path) - 1):
        edge = graph.edges[path[i], path[i + 1]]
        total_distance += edge["length"]
        total_time += edge["time"]
        street = edge.get("name", "")
        if street and street != current_street:
            if current_street is not None:
                steps.append({
                    "instruction": f"Продолжайте по {current_street}",
                    "distance": edge["length"],
                    "name": current_street,
                    "icon": "arrow-up",
                })
            current_street = street
        elif street and i == 0:
            current_street = street

    if current_street:
        steps.append({
            "instruction": f"Продолжайте по {current_street}",
            "distance": 0, "name": current_street, "icon": "arrow-up",
        })
    steps.append({
        "instruction": "Вы прибудете в пункт назначения",
        "distance": 0, "name": "", "icon": "flag-checkered",
    })

    return {
        "routes": [{
            "index": 0,
            "distance": total_distance,
            "distance_text": format_distance(total_distance),
            "duration": total_time,
            "duration_text": format_duration(total_time),
            "geometry": {
                "type": "LineString",
                "coordinates": [[c[1], c[0]] for c in coords],
            },
            "steps": steps,
            "is_alternative": False,
            "fuel_estimate": estimate_fuel(total_distance, "driving"),
            "calories_estimate": None,
            "start_node_dist": int(start_dist),
            "end_node_dist": int(end_dist),
        }],
        "code": "Ok",
        "profile": "driving",
        "engine": "networkx_local",
        "nodes_in_path": len(path),
    }


def route_osrm(start_lat, start_lon, end_lat, end_lon, profile="driving"):
    """Онлайн-роутинг через OSRM (fallback)."""
    if profile not in ("driving", "foot", "cycling"):
        profile = "driving"

    cache_key = f"route:{start_lat},{start_lon},{end_lat},{end_lon},{profile}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        coords = f"{start_lon},{start_lat};{end_lon},{end_lat}"
        r = requests.get(
            f"{OSRM_URL}/{profile}/{coords}",
            params={"alternatives": "true", "steps": "true",
                    "overview": "full", "geometries": "geojson"},
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        return {"error": f"OSRM недоступен: {e}"}

    if data.get("code") != "Ok":
        return {"error": data.get("message", "Ошибка маршрута")}

    routes = []
    for i, route in enumerate(data.get("routes", [])):
        steps = []
        for leg in route.get("legs", []):
            for step in leg.get("steps", []):
                m = step.get("maneuver", {})
                instr = _build_instruction(step, m.get("modifier", ""), m.get("type", ""))
                if instr:
                    steps.append({
                        "instruction": instr,
                        "distance": step.get("distance", 0),
                        "duration": step.get("duration", 0),
                        "name": step.get("name", ""),
                        "icon": _maneuver_icon(m.get("type", ""), m.get("modifier", "")),
                    })
        dist = route.get("distance", 0)
        dur = route.get("duration", 0)
        routes.append({
            "index": i,
            "distance": dist,
            "distance_text": format_distance(dist),
            "duration": dur,
            "duration_text": format_duration(dur),
            "geometry": route.get("geometry", {}),
            "steps": steps,
            "is_alternative": i > 0,
            "fuel_estimate": estimate_fuel(dist, profile),
            "calories_estimate": estimate_calories(dist, dur, profile),
        })

    result = {"routes": routes, "code": data.get("code"), "profile": profile,
              "engine": "osrm_online"}
    cache.set(cache_key, result)
    return result


def _build_instruction(step, modifier, mtype):
    """Формирует человекочитаемую инструкцию на русском."""
    name = step.get("name", "")
    name_part = f" на {name}" if name else ""
    dist = step.get("distance", 0)
    dist_part = f" через {format_distance(dist)}" if dist > 30 else ""

    if mtype == "depart": return f"Отправляйтесь{name_part}"
    if mtype == "arrive": return f"Вы прибудете в пункт назначения{name_part}"
    if mtype == "turn":
        m = {"left": "Поверните налево", "right": "Поверните направо",
             "slight left": "Плавно налево", "slight right": "Плавно направо",
             "sharp left": "Резко налево", "sharp right": "Резко направо",
             "straight": "Двигайтесь прямо", "uturn": "Развернитесь"}
        return f"{m.get(modifier, 'Поверните')}{name_part}{dist_part}"
    if mtype == "new name": return f"Продолжайте{dist_part}{name_part}"
    if mtype == "merge": return f"Перестройтесь{name_part}{dist_part}"
    if mtype == "on ramp": return f"Выезжайте на дорогу{name_part}{dist_part}"
    if mtype == "off ramp": return f"Съезжайте{name_part}{dist_part}"
    if mtype == "fork":
        if "left" in modifier: return f"Держитесь левее{name_part}"
        if "right" in modifier: return f"Держитесь правее{name_part}"
        return f"На развилке{name_part}"
    if mtype == "continue": return f"Продолжайте{dist_part}{name_part}"
    if mtype in ("roundabout", "rotary"):
        return f"На круговом движении{name_part}{dist_part}"
    return f"Двигайтесь{dist_part}{name_part}"


def _maneuver_icon(mtype, modifier):
    """Иконка для манёвра."""
    if mtype == "depart": return "play"
    if mtype == "arrive": return "flag-checkered"
    if mtype == "turn":
        if modifier == "left": return "arrow-turn-up rotate-left"
        if modifier == "right": return "arrow-turn-up"
        if modifier == "uturn": return "rotate-left"
        return "arrow-up"
    if mtype in ("roundabout", "rotary"): return "circle-notch"
    if mtype == "merge": return "code-merge"
    if mtype == "fork": return "code-fork"
    return "arrow-up"
