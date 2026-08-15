"""Автобусы: маршруты, остановки, GPS-симуляция."""
from flask import Blueprint, request, jsonify

from services.bus_service import (
    BUS_ROUTES, get_real_routes, get_live_buses,
    reset_simulation, search_buses,
)

buses_bp = Blueprint("buses", __name__)


@buses_bp.route("/api/buses")
def api_buses():
    """Справочник автобусов."""
    return jsonify({"routes": BUS_ROUTES, "count": len(BUS_ROUTES)})


@buses_bp.route("/api/buses/<bus_id>")
def api_bus_detail(bus_id):
    """Детали автобуса."""
    for b in BUS_ROUTES:
        if b["id"] == bus_id:
            return jsonify(b)
    return jsonify({"error": "Не найдено"}), 404


@buses_bp.route("/api/buses/search")
def api_bus_search():
    """Поиск автобусов."""
    q = (request.args.get("q") or "").strip().lower()
    results = search_buses(q)
    return jsonify({"routes": results, "count": len(results), "query": q})


@buses_bp.route("/api/buses/real")
def api_buses_real():
    """Реальные маршруты из OpenStreetMap."""
    result = get_real_routes()
    if "error" in result:
        return jsonify(result), 503
    return jsonify(result)


@buses_bp.route("/api/buses/live")
def api_buses_live():
    """GPS-позиции живых автобусов (симуляция)."""
    return jsonify(get_live_buses())


@buses_bp.route("/api/buses/live/<route_id>")
def api_buses_live_route(route_id):
    """Живые автобусы конкретного маршрута."""
    result = get_live_buses(route_id)
    return jsonify(result)


@buses_bp.route("/api/buses/simulation/reset", methods=["POST"])
def api_buses_sim_reset():
    """Сброс симуляции."""
    return jsonify(reset_simulation())
