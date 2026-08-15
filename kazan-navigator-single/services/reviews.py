"""
Сервис отзывов: Foursquare API + своя SQLite база.
Нужны API ключи Foursquare (бесплатно на developer.foursquare.com).
Без ключей — работает только своя база (пока пустая).
"""
import os
import sqlite3
import requests
from datetime import datetime
from config import DB_PATH
from extensions import cache


FOURSQUARE_API_KEY = os.environ.get("FOURSQUARE_API_KEY", "")
FOURSQUARE_BASE = "https://api.foursquare.com/v3/places"


def get_reviews_db():
    """Подключение к базе отзывов (своя)."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_reviews_db():
    """Создание таблиц отзывов."""
    conn = get_reviews_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            place_id TEXT,
            place_name TEXT,
            place_lat REAL,
            place_lon REAL,
            author_name TEXT NOT NULL,
            rating INTEGER NOT NULL CHECK(rating >= 1 AND rating <= 5),
            text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_reviews_place ON reviews(place_id);
        CREATE INDEX IF NOT EXISTS idx_reviews_created ON reviews(created_at DESC);
    """)
    conn.commit()
    conn.close()


init_reviews_db()


def get_foursquare_place(lat, lon, name=None, radius=200):
    """
    Поиск места в Foursquare по координатам.
    Возвращает rating, отзывы, фото — или None если не найдено.
    """
    if not FOURSQUARE_API_KEY:
        return None

    cache_key = f"fsq:{lat:.5f}:{lon:.5f}:{name or ''}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    headers = {
        "Authorization": FOURSQUARE_API_KEY,
        "Accept": "application/json",
    }
    params = {
        "ll": f"{lat},{lon}",
        "radius": radius,
        "limit": 1,
    }
    if name:
        params["query"] = name

    try:
        r = requests.get(f"{FOURSQUARE_BASE}/search",
                         headers=headers, params=params, timeout=10)
        if r.status_code != 200:
            return None
        data = r.json()
        if not data.get("results"):
            return None
        place = data["results"][0]
        fsq_id = place["fsq_id"]

        # Детали места (рейтинг, отзывы)
        details_r = requests.get(f"{FOURSQUARE_BASE}/{fsq_id}",
                                  headers=headers, timeout=10)
        if details_r.status_code != 200:
            return {"name": place["name"], "rating": None, "reviews": []}
        details = details_r.json()

        result = {
            "fsq_id": fsq_id,
            "name": place["name"],
            "rating": details.get("rating"),
            "rating_signals": details.get("rating_signals", 0),
            "hours": details.get("hours", {}).get("regular"),
            "photos_count": len(details.get("photos", [])),
            "source": "foursquare",
        }
        cache.set(cache_key, result)
        return result
    except Exception as e:
        print(f"Foursquare error: {e}")
        return None


def add_review(place_id, place_name, lat, lon, author, rating, text):
    """Добавить отзыв (своя база)."""
    conn = get_reviews_db()
    cur = conn.execute(
        """INSERT INTO reviews
           (place_id, place_name, place_lat, place_lon,
            author_name, rating, text)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (place_id, place_name, lat, lon, author, rating, text)
    )
    conn.commit()
    review_id = cur.lastrowid
    conn.close()
    return review_id


def get_local_reviews(place_id=None, lat=None, lon=None, radius=200):
    """Получить отзывы из своей базы."""
    conn = get_reviews_db()
    if place_id:
        rows = conn.execute(
            "SELECT * FROM reviews WHERE place_id = ? ORDER BY created_at DESC",
            (place_id,)
        ).fetchall()
    elif lat and lon:
        delta = radius / 111000
        rows = conn.execute(
            """SELECT * FROM reviews
               WHERE place_lat BETWEEN ? AND ? AND place_lon BETWEEN ? AND ?
               ORDER BY created_at DESC""",
            (lat - delta, lat + delta, lon - delta, lon + delta)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM reviews ORDER BY created_at DESC LIMIT 50"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_place_rating(place_id=None, lat=None, lon=None, name=None):
    """
    Получить рейтинг места:
    1. Сначала Foursquare (если есть API ключ)
    2. Потом своя база отзывов
    """
    result = {
        "source": "none",
        "rating": None,
        "reviews_count": 0,
        "reviews": [],
        "foursquare_available": bool(FOURSQUARE_API_KEY),
    }

    # 1. Foursquare
    if FOURSQUARE_API_KEY and lat and lon:
        fsq = get_foursquare_place(lat, lon, name)
        if fsq and fsq.get("rating"):
            result["source"] = "foursquare"
            result["rating"] = fsq["rating"]
            result["rating_signals"] = fsq.get("rating_signals", 0)
            result["hours"] = fsq.get("hours")
            result["photos_count"] = fsq.get("photos_count", 0)
            return result

    # 2. Своя база
    local = get_local_reviews(place_id, lat, lon)
    if local:
        avg_rating = sum(r["rating"] for r in local) / len(local)
        result["source"] = "local"
        result["rating"] = round(avg_rating, 1)
        result["reviews_count"] = len(local)
        result["reviews"] = local
        return result

    return result
