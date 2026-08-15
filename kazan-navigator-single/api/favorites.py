"""Избранное и история поиска."""
from flask import Blueprint, request, jsonify

from extensions import get_db

favorites_bp = Blueprint("favorites", __name__)


@favorites_bp.route("/api/favorites", methods=["GET", "POST", "DELETE"])
def api_favorites():
    conn = get_db()
    if request.method == "GET":
        rows = conn.execute("SELECT * FROM favorites ORDER BY created_at DESC").fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])

    if request.method == "POST":
        d = request.get_json()
        if not d or "lat" not in d:
            return jsonify({"error": "lat, lon обязательны"}), 400
        cur = conn.execute(
            "INSERT INTO favorites (lat, lon, name, address, category, icon) VALUES (?,?,?,?,?,?)",
            (float(d["lat"]), float(d["lon"]), d.get("name", "Без названия"),
             d.get("address", ""), d.get("category", "other"), d.get("icon", "star")))
        conn.commit()
        fid = cur.lastrowid
        conn.close()
        return jsonify({"id": fid, "status": "added"})

    # DELETE
    fid = request.args.get("id")
    if fid:
        conn.execute("DELETE FROM favorites WHERE id = ?", (fid,))
    else:
        conn.execute("DELETE FROM favorites")
    conn.commit()
    conn.close()
    return jsonify({"status": "deleted"})


@favorites_bp.route("/api/history", methods=["GET", "POST", "DELETE"])
def api_history():
    conn = get_db()
    if request.method == "GET":
        rows = conn.execute("SELECT * FROM history ORDER BY created_at DESC LIMIT 20").fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])

    if request.method == "POST":
        d = request.get_json()
        if not d or "query" not in d:
            return jsonify({"error": "query обязателен"}), 400
        cur = conn.execute(
            "INSERT INTO history (query, lat, lon, display_name) VALUES (?,?,?,?)",
            (d["query"], d.get("lat"), d.get("lon"), d.get("display_name", "")))
        conn.commit()
        hid = cur.lastrowid
        conn.close()
        return jsonify({"id": hid, "status": "added"})

    # DELETE
    conn.execute("DELETE FROM history")
    conn.commit()
    conn.close()
    return jsonify({"status": "cleared"})
