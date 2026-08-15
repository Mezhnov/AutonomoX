"""
Расширения приложения: db, cache.
Инициализируются один раз, используются во всех модулях.
"""
import sqlite3
import time
import threading
from pathlib import Path

from config import DB_PATH, CACHE_TTL


class TTLCache:
    """Потокобезопасный кэш в памяти с TTL."""

    def __init__(self, ttl=CACHE_TTL):
        self.ttl = ttl
        self._store = {}
        self._lock = threading.Lock()

    def get(self, key):
        with self._lock:
            item = self._store.get(key)
            if not item:
                return None
            if time.time() - item["ts"] > self.ttl:
                del self._store[key]
                return None
            return item["val"]

    def set(self, key, val):
        with self._lock:
            self._store[key] = {"val": val, "ts": time.time()}

    def clear(self):
        with self._lock:
            self._store.clear()


# Глобальный кэш
cache = TTLCache()


def get_db():
    """Подключение к SQLite (избранное + история)."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Создание таблиц, если их нет."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lat REAL NOT NULL,
            lon REAL NOT NULL,
            name TEXT NOT NULL,
            address TEXT,
            category TEXT DEFAULT 'other',
            icon TEXT DEFAULT 'star',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT NOT NULL,
            lat REAL,
            lon REAL,
            display_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_fav_cat ON favorites(category);
        CREATE INDEX IF NOT EXISTS idx_hist_ts ON history(created_at DESC);
    """)
    conn.commit()
    conn.close()


# Инициализируем при импорте
init_db()
