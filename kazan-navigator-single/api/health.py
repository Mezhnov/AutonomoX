"""Health и статус эндпоинты."""
from flask import Blueprint, jsonify
from datetime import datetime
from pathlib import Path

from config import LOCAL_SEARCH_DB, ROUTING_GRAPH, DATA_DIR
from extensions import cache
from services.bus_service import BUS_ROUTES
from api.attractions import ATTRACTIONS

health_bp = Blueprint("health", __name__)


@health_bp.route("/api/health")
def api_health():
    """Статус сервера."""
    return jsonify({
        "status": "ok",
        "service": "Казань Навигатор API",
        "version": "4.0.0",
        "city": "Казань",
        "architecture": "modular",
        "attractions_count": len(ATTRACTIONS),
        "bus_routes_count": len(BUS_ROUTES),
        "features": [
            "local_search_sqlite_fts5",
            "local_routing_networkx",
            "live_gps_simulation",
            "offline_tiles_cache",
        ],
        "time": datetime.now().isoformat(),
    })


@health_bp.route("/api/local/status")
def api_local_status():
    """Статус локальных баз данных."""
    return jsonify({
        "search_db": {
            "exists": LOCAL_SEARCH_DB.exists(),
            "size_mb": round(LOCAL_SEARCH_DB.stat().st_size / 1024 / 1024, 2) if LOCAL_SEARCH_DB.exists() else 0,
            "path": LOCAL_SEARCH_DB.name,
        },
        "routing_graph": {
            "exists": ROUTING_GRAPH.exists(),
            "size_mb": round(ROUTING_GRAPH.stat().st_size / 1024 / 1024, 2) if ROUTING_GRAPH.exists() else 0,
        },
        "osm_files": [
            {"name": f.name, "size_mb": round(f.stat().st_size / 1024 / 1024, 2)}
            for f in DATA_DIR.glob("kazan*.osm") if f.exists()
        ],
    })


@health_bp.route("/api/cache/clear", methods=["POST"])
def api_cache_clear():
    """Очистка кэша."""
    cache.clear()
    return jsonify({"status": "cache cleared"})
