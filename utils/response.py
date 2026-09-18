from typing import Any, Optional
from datetime import datetime
from fastapi.responses import JSONResponse


def _make_serializable(obj):
    """Recursively convert non-JSON-serializable types (datetime, ObjectId, etc.)."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if hasattr(obj, '__str__') and type(obj).__name__ == 'ObjectId':
        return str(obj)
    if isinstance(obj, dict):
        return {k: _make_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_make_serializable(item) for item in obj]
    return obj


def api_response(
    success: bool,
    message: str,
    data: Optional[Any] = None,
    errors: Optional[Any] = None,
    status_code: int = 200
) -> JSONResponse:
    content = {
        "success": success,
        "message": message,
        "data": _make_serializable(data),
        "errors": _make_serializable(errors)
    }
    return JSONResponse(content=content, status_code=status_code)
