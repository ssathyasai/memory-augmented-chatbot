import json
from pathlib import Path
from typing import Any, Dict, List

from .config import settings


def _ensure_file(path_str: str, default: Any) -> Path:
    # Small JSON files keep dashboard state available without extra infrastructure.
    path = Path(path_str)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(json.dumps(default, indent=2), encoding="utf-8")
    return path


def _read_json(path_str: str, default: Any) -> Any:
    # Reads resiliently so a broken file does not crash the whole app.
    path = _ensure_file(path_str, default)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        path.write_text(json.dumps(default, indent=2), encoding="utf-8")
        return default


def _write_json(path_str: str, payload: Any) -> None:
    # Writes are centralized to avoid duplicate file handling code.
    path = _ensure_file(path_str, payload)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def register_document(user_id: str, filename: str, num_chunks: int) -> None:
    # Document uploads are tracked for the analytics dashboard.
    documents = _read_json(settings.DOCUMENT_INDEX_FILE, [])
    documents.append(
        {
            "user_id": user_id,
            "filename": filename,
            "num_chunks": num_chunks,
        }
    )
    _write_json(settings.DOCUMENT_INDEX_FILE, documents)


def get_user_documents(user_id: str) -> List[Dict[str, Any]]:
    # The documents page uses this list to restore state.
    documents = _read_json(settings.DOCUMENT_INDEX_FILE, [])
    return [item for item in documents if item["user_id"] == user_id]


def record_chat_analytics(
    user_id: str,
    response_time: float,
    route: str,
    sources_count: int,
    memories_count: int,
    graph_count: int,
    tools_count: int,
) -> None:
    # Each completed chat turn appends a compact analytics event.
    analytics = _read_json(settings.ANALYTICS_FILE, [])
    analytics.append(
        {
            "user_id": user_id,
            "response_time": response_time,
            "route": route,
            "sources_count": sources_count,
            "memories_count": memories_count,
            "graph_count": graph_count,
            "tools_count": tools_count,
        }
    )
    _write_json(settings.ANALYTICS_FILE, analytics)


def get_user_analytics_events(user_id: str) -> List[Dict[str, Any]]:
    # Raw events support future dashboard charts.
    events = _read_json(settings.ANALYTICS_FILE, [])
    return [item for item in events if item["user_id"] == user_id]


def save_user_settings(payload: Dict[str, Any]) -> Dict[str, Any]:
    # Settings are replaced per user to keep the operation idempotent.
    settings_payload = _read_json(settings.SETTINGS_FILE, [])
    filtered = [item for item in settings_payload if item["user_id"] != payload["user_id"]]
    filtered.append(payload)
    _write_json(settings.SETTINGS_FILE, filtered)
    return payload


def get_user_settings(user_id: str) -> Dict[str, Any]:
    # Default settings keep the UI functional before the user saves preferences.
    all_settings = _read_json(settings.SETTINGS_FILE, [])
    for item in all_settings:
        if item["user_id"] == user_id:
            return item
    return {
        "user_id": user_id,
        "display_name": user_id,
        "preferred_theme": "dark",
        "transparency_enabled": True,
    }
