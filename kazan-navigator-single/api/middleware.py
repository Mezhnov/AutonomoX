"""
Декоратор для проверки API-ключа и rate limiting.
Встраивается в каждый endpoint v1 API.
"""
import time
from functools import wraps
from flask import request, jsonify, g

from services.api_keys import (
    validate_api_key, check_rate_limit, log_api_usage,
)


def require_api_key(f):
    """Декоратор: требует валидный API-ключ в header X-API-Key или ?api_key=."""
    @wraps(f)
    def decorated(*args, **kwargs):
        start_time = time.time()
        api_key = request.headers.get("X-API-Key") or request.args.get("api_key")

        key_data, error = validate_api_key(api_key)
        if error:
            response = jsonify({"error": error, "code": "INVALID_API_KEY"})
            response.status_code = 401
            return response

        # Rate limiting
        allowed, remaining = check_rate_limit(key_data["id"], key_data["requests_limit"])
        if not allowed:
            response = jsonify({
                "error": f"Превышен лимит запросов ({key_data['requests_limit']}/мин)",
                "code": "RATE_LIMIT_EXCEEDED",
                "retry_after_seconds": 60,
            })
            response.status_code = 429
            response.headers["X-RateLimit-Limit"] = str(key_data["requests_limit"])
            response.headers["X-RateLimit-Remaining"] = "0"
            return response

        # Сохраняем данные ключа для использования в endpoint
        g.api_key_data = key_data

        # Выполняем запрос
        result = f(*args, **kwargs)

        # Логируем
        response_time_ms = int((time.time() - start_time) * 1000)
        status_code = result[1] if isinstance(result, tuple) else getattr(result, "status_code", 200)
        log_api_usage(
            key_data["id"], request.path, request.method,
            status_code, request.remote_addr, response_time_ms
        )

        # Добавляем rate limit headers
        if hasattr(result, "headers"):
            result.headers["X-RateLimit-Limit"] = str(key_data["requests_limit"])
            result.headers["X-RateLimit-Remaining"] = str(remaining)
        return result
    return decorated
