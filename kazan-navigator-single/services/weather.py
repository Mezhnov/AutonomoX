"""
Сервис погоды: Open-Meteo (бесплатно, без ключа).
"""
import requests
from config import OPEN_METEO_URL
from extensions import cache


def get_weather():
    """Текущая погода в Казани."""
    cache_key = "weather:kazan"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    try:
        r = requests.get(
            OPEN_METEO_URL,
            params={
                "latitude": 55.7961, "longitude": 49.1064,
                "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m,wind_direction_10m",
                "timezone": "Europe/Moscow",
            },
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        return {"error": str(e)}

    cur = data.get("current", {})
    code = cur.get("weather_code", 0)
    response = {
        "temperature": round(cur.get("temperature_2m", 0)),
        "feels_like": round(cur.get("apparent_temperature", 0)),
        "humidity": cur.get("relative_humidity_2m", 0),
        "wind_speed": round(cur.get("wind_speed_10m", 0)),
        "wind_direction": cur.get("wind_direction_10m", 0),
        "weather_code": code,
        "description": _weather_desc(code),
        "icon": _weather_icon(code),
        "city": "Казань",
    }
    cache.set(cache_key, response)
    return response


def _weather_desc(code):
    m = {0: "Ясно", 1: "Преимущественно ясно", 2: "Переменная облачность",
         3: "Пасмурно", 45: "Туман", 48: "Изморозь",
         51: "Морось", 53: "Морось", 55: "Сильная морось",
         61: "Дождь", 63: "Дождь", 65: "Сильный дождь",
         71: "Снег", 73: "Снег", 75: "Сильный снег",
         80: "Ливень", 81: "Ливень", 82: "Сильный ливень",
         95: "Гроза", 96: "Гроза с градом"}
    return m.get(code, "Неизвестно")


def _weather_icon(code):
    if code == 0: return "sun"
    if code in (1, 2): return "cloud-sun"
    if code == 3: return "cloud"
    if code in (45, 48): return "smog"
    if 51 <= code <= 67: return "cloud-rain"
    if 71 <= code <= 77: return "snowflake"
    if 80 <= code <= 82: return "cloud-showers-heavy"
    if code >= 95: return "cloud-bolt"
    return "cloud"
