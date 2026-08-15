"""
Строит граф дорог Казани из OSM XML для локального роутинга.
Использует xml.etree для надёжного парсинга.
NetworkX + pickle — работает без интернета и Docker.
"""
import xml.etree.ElementTree as ET
import networkx as nx
import pickle
import sys
import math
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "static" / "data"
OSM_FILE = DATA_DIR / "kazan-roads.osm"
GRAPH_FILE = DATA_DIR / "kazan_graph.pkl"


def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlmb/2)**2
    return 2 * R * math.asin(math.sqrt(a))


ROAD_SPEEDS = {
    "motorway": 90, "trunk": 70, "primary": 60, "secondary": 50,
    "tertiary": 40, "unclassified": 30, "residential": 25,
    "service": 15, "living_street": 20,
    "motorway_link": 50, "trunk_link": 40, "primary_link": 35,
    "secondary_link": 30, "tertiary_link": 25,
}


def build_graph():
    if not OSM_FILE.exists():
        print(f"ERROR: {OSM_FILE} не найден")
        return 1

    print(f"Парсю {OSM_FILE.name} ({OSM_FILE.stat().st_size / 1024 / 1024:.1f} MB)...")
    tree = ET.parse(str(OSM_FILE))
    root = tree.getroot()

    # 1. Собираем все ноды (id → (lat, lon))
    nodes = {}
    for node in root.findall("node"):
        nid = int(node.get("id"))
        lat = float(node.get("lat"))
        lon = float(node.get("lon"))
        nodes[nid] = (lat, lon)
    print(f"Нод: {len(nodes)}")

    # 2. Строим граф дорог
    G = nx.DiGraph()
    # Добавляем все ноды
    for nid, (lat, lon) in nodes.items():
        G.add_node(nid, lat=lat, lon=lon)

    road_count = 0
    edge_count = 0

    for way in root.findall("way"):
        tags = {t.get("k"): t.get("v") for t in way.findall("tag")}
        highway = tags.get("highway")
        if not highway or highway not in ROAD_SPEEDS:
            continue

        # Получаем refs
        nd_refs = [int(nd.get("ref")) for nd in way.findall("nd")]
        if len(nd_refs) < 2:
            continue

        name = tags.get("name", "")
        oneway = tags.get("oneway", "no") in ("yes", "true", "1")
        speed = ROAD_SPEEDS[highway]

        # Добавляем рёбра
        for i in range(len(nd_refs) - 1):
            n1 = nd_refs[i]
            n2 = nd_refs[i + 1]
            if n1 not in nodes or n2 not in nodes:
                continue
            lat1, lon1 = nodes[n1]
            lat2, lon2 = nodes[n2]
            length = haversine(lat1, lon1, lat2, lon2)
            if length < 1:
                continue
            time_sec = (length / 1000) / speed * 3600
            G.add_edge(n1, n2, length=length, time=time_sec, speed=speed, name=name, type=highway)
            edge_count += 1
            if not oneway:
                G.add_edge(n2, n1, length=length, time=time_sec, speed=speed, name=name, type=highway)
                edge_count += 1
        road_count += 1

    print(f"Дорог: {road_count}")
    print(f"Рёбер: {edge_count}")
    print(f"Граф: {G.number_of_nodes()} нод, {G.number_of_edges()} рёбер")

    # Удаляем изолированные ноды
    isolated = list(nx.isolates(G))
    G.remove_nodes_from(isolated)
    print(f"Удалено изолированных нод: {len(isolated)}")
    print(f"Финальный граф: {G.number_of_nodes()} нод, {G.number_of_edges()} рёбер")

    print(f"\nСохраняю в {GRAPH_FILE.name}...")
    with open(GRAPH_FILE, "wb") as f:
        pickle.dump(G, f, protocol=pickle.HIGHEST_PROTOCOL)

    size_mb = GRAPH_FILE.stat().st_size / 1024 / 1024
    print(f"Размер: {size_mb:.1f} MB")
    print(f"Готово: {GRAPH_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(build_graph())
