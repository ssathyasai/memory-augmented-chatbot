
from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pathlib import Path

from pymongo import MongoClient
from pymongo.errors import ConfigurationError, ConnectionFailure

from .config import settings

_mongo_client: Optional[MongoClient] = None
_db = None
_local_memories: List[Dict[str, Any]] = []


def connect_to_mongodb() -> bool:
    # MongoDB is preferred; local fallback keeps the project usable during setup.
    global _mongo_client, _db
    try:
        if not settings.MONGODB_URI:
            return False
        if _mongo_client is None:
            _mongo_client = MongoClient(settings.MONGODB_URI, serverSelectionTimeoutMS=3000)
            _mongo_client.admin.command("ping")
            _db = _mongo_client[settings.MONGODB_DB_NAME]
        return True
    except (ConnectionFailure, ConfigurationError, ValueError) as e:
        print(f"Could not connect to MongoDB: {e}")
        return False


def _memory_document(
    user_id: str,
    memory_type: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    # Memory documents use a shared shape for MongoDB and local fallback.
    now = datetime.utcnow()
    return {
        "_id": str(uuid.uuid4()),
        "user_id": user_id,
        "type": memory_type,
        "content": content,
        "metadata": metadata or {},
        "created_at": now,
        "updated_at": now,
    }


def get_memory_collection():
    # The collection is returned only when MongoDB is available.
    global _db
    if _db is None:
        if not connect_to_mongodb():
            return None
    return _db["memories"]


def add_memory(
    user_id: str,
    memory_type: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    # The assistant writes every long-term memory through this function.
    collection = get_memory_collection()
    memory_doc = _memory_document(user_id, memory_type, content, metadata)
    if collection is not None:
        collection.insert_one(memory_doc)
    else:
        _local_memories.append(memory_doc)
    return memory_doc["_id"]


def get_memories(user_id: str, memory_type: Optional[str] = None) -> List[Dict[str, Any]]:
    # Dashboard listing and chat recall use the same filtered query.
    collection = get_memory_collection()
    query: Dict[str, Any] = {"user_id": user_id}
    if memory_type:
        query["type"] = memory_type
    if collection is not None:
        return list(collection.find(query).sort("updated_at", -1))
    filtered = [m for m in _local_memories if m["user_id"] == user_id]
    if memory_type:
        filtered = [m for m in filtered if m["type"] == memory_type]
    return sorted(filtered, key=lambda item: item["updated_at"], reverse=True)


def search_memories(user_id: str, query: str, limit: int = 5) -> List[Dict[str, Any]]:
    # Memory retrieval is intentionally simple and transparent for this project.
    collection = get_memory_collection()
    if collection is not None:
        return list(
            collection.find(
                {
                    "user_id": user_id,
                    "content": {"$regex": query, "$options": "i"},
                }
            )
            .sort("updated_at", -1)
            .limit(limit)
        )

    lowered = query.lower()
    matches = [
        item
        for item in _local_memories
        if item["user_id"] == user_id and lowered in item["content"].lower()
    ]
    return sorted(matches, key=lambda item: item["updated_at"], reverse=True)[:limit]


def update_memory(
    memory_id: str,
    user_id: str,
    content: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> bool:
    # Memory edits are supported from the memory dashboard.
    collection = get_memory_collection()
    update_data: Dict[str, Any] = {"updated_at": datetime.utcnow()}
    if content is not None:
        update_data["content"] = content
    if metadata is not None:
        update_data["metadata"] = metadata
    if collection is not None:
        result = collection.update_one({"_id": memory_id, "user_id": user_id}, {"$set": update_data})
        return result.modified_count > 0

    for item in _local_memories:
        if item["_id"] == memory_id and item["user_id"] == user_id:
            item.update(update_data)
            return True
    return False


def delete_memory(memory_id: str, user_id: str) -> bool:
    # Memory deletion keeps the dashboard and stored context in sync.
    collection = get_memory_collection()
    if collection is not None:
        result = collection.delete_one({"_id": memory_id, "user_id": user_id})
        return result.deleted_count > 0

    for index, item in enumerate(_local_memories):
        if item["_id"] == memory_id and item["user_id"] == user_id:
            _local_memories.pop(index)
            return True
    return False
