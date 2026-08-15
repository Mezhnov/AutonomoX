"""
Сервис API-ключей: создание, проверка, лимиты, статистика.
Как у Яндекса/2GIS — разработчик регистрируется и получает ключ.
"""
import sqlite3
import secrets
import time
import threading
from datetime import datetime
from config import DB_PATH


def get_api_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_api_db():
    conn = get_api_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            email TEXT,
            description TEXT,
            tier TEXT DEFAULT 'free',
            requests_limit INTEGER DEFAULT 100,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS api_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            api_key_id INTEGER NOT NULL,
            endpoint TEXT NOT NULL,
            method TEXT NOT NULL,
            status_code INTEGER,
            ip_address TEXT,
            response_time_ms INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (api_key_id) REFERENCES api_keys (id)
        );

        CREATE INDEX IF NOT EXISTS idx_usage_key ON api_usage(api_key_id);
        CREATE INDEX IF NOT EXISTS idx_usage_created ON api_usage(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_keys_key ON api_keys(key);
    """)
    conn.commit()

    # Создаём демо-ключ если его нет
    demo = conn.execute("SELECT id FROM api_keys WHERE key = ?", ("kzn_demo_key_2024",)).fetchone()
    if not demo:
        conn.execute("""
            INSERT INTO api_keys (key, name, email, description, tier, requests_limit)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            "kzn_demo_key_2024",
            "Демо ключ",
            "demo@kazan-navigator.ru",
            "Бесплатный демо-ключ для тестирования API",
            "free", 100
        ))
        conn.commit()
        print("  Создан демо API-ключ: kzn_demo_key_2024")

    conn.close()


init_api_db()


# In-memory rate limiter
_RATE_LIMITS = {}
_RATE_LOCK = threading.Lock()


def create_api_key(name, email=None, description=None, tier="free"):
    """Создать новый API-ключ."""
    limits = {"free": 100, "pro": 1000, "business": 10000}
    key = "kzn_" + secrets.token_hex(16)
    conn = get_api_db()
    cur = conn.execute("""
        INSERT INTO api_keys (key, name, email, description, tier, requests_limit)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (key, name, email, description, tier, limits.get(tier, 100)))
    conn.commit()
    key_id = cur.lastrowid
    conn.close()
    return {"id": key_id, "key": key, "name": name, "tier": tier,
            "requests_limit": limits.get(tier, 100)}


def validate_api_key(api_key):
    """Проверить API-ключ. Возвращает (key_data, error)."""
    if not api_key:
        return None, "API ключ обязателен. Получите на /api/v1/keys/register"
    conn = get_api_db()
    row = conn.execute("SELECT * FROM api_keys WHERE key = ? AND is_active = 1", (api_key,)).fetchone()
    if not row:
        conn.close()
        return None, "Неверный или неактивный API ключ"
    # Обновляем last_used
    conn.execute("UPDATE api_keys SET last_used = ? WHERE id = ?", (datetime.now(), row["id"]))
    conn.commit()
    conn.close()
    return dict(row), None


def check_rate_limit(api_key_id, limit_per_min):
    """Проверить rate limit. Возвращает (allowed, remaining)."""
    now = time.time()
    window_start = now - 60

    with _RATE_LOCK:
        # Чистим старые записи
        if api_key_id in _RATE_LIMITS:
            _RATE_LIMITS[api_key_id] = [
                t for t in _RATE_LIMITS[api_key_id] if t > window_start
            ]
        else:
            _RATE_LIMITS[api_key_id] = []

        count = len(_RATE_LIMITS[api_key_id])
        if count >= limit_per_min:
            return False, 0

        _RATE_LIMITS[api_key_id].append(now)
        return True, limit_per_min - count - 1


def log_api_usage(api_key_id, endpoint, method, status_code, ip, response_time_ms):
    """Логировать использование API."""
    conn = get_api_db()
    conn.execute("""
        INSERT INTO api_usage (api_key_id, endpoint, method, status_code, ip_address, response_time_ms)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (api_key_id, endpoint, method, status_code, ip, response_time_ms))
    conn.commit()
    conn.close()


def get_api_stats(api_key_id=None):
    """Статистика использования API."""
    conn = get_api_db()
    if api_key_id:
        # Статистика конкретного ключа
        total = conn.execute(
            "SELECT COUNT(*) as cnt FROM api_usage WHERE api_key_id = ?",
            (api_key_id,)
        ).fetchone()["cnt"]
        by_endpoint = conn.execute("""
            SELECT endpoint, COUNT(*) as cnt, AVG(response_time_ms) as avg_time
            FROM api_usage WHERE api_key_id = ?
            GROUP BY endpoint ORDER BY cnt DESC LIMIT 10
        """, (api_key_id,)).fetchall()
        recent = conn.execute("""
            SELECT endpoint, method, status_code, response_time_ms, created_at
            FROM api_usage WHERE api_key_id = ?
            ORDER BY created_at DESC LIMIT 20
        """, (api_key_id,)).fetchall()
        conn.close()
        return {
            "total_requests": total,
            "by_endpoint": [dict(r) for r in by_endpoint],
            "recent": [dict(r) for r in recent],
        }
    else:
        # Общая статистика
        total_keys = conn.execute("SELECT COUNT(*) as cnt FROM api_keys").fetchone()["cnt"]
        active_keys = conn.execute("SELECT COUNT(*) as cnt FROM api_keys WHERE is_active = 1").fetchone()["cnt"]
        total_requests = conn.execute("SELECT COUNT(*) as cnt FROM api_usage").fetchone()["cnt"]
        today_requests = conn.execute("""
            SELECT COUNT(*) as cnt FROM api_usage
            WHERE created_at > datetime('now', '-1 day')
        """).fetchone()["cnt"]
        by_endpoint = conn.execute("""
            SELECT endpoint, COUNT(*) as cnt, AVG(response_time_ms) as avg_time
            FROM api_usage GROUP BY endpoint ORDER BY cnt DESC LIMIT 10
        """).fetchall()
        conn.close()
        return {
            "total_api_keys": total_keys,
            "active_api_keys": active_keys,
            "total_requests": total_requests,
            "requests_today": today_requests,
            "by_endpoint": [dict(r) for r in by_endpoint],
        }


def list_api_keys():
    """Список всех API-ключей (для админки)."""
    conn = get_api_db()
    rows = conn.execute("""
        SELECT k.*,
               (SELECT COUNT(*) FROM api_usage u WHERE u.api_key_id = k.id) as requests_count
        FROM api_keys k ORDER BY k.created_at DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]
