
import re
from typing import Any, Dict, List, Tuple

from neo4j import GraphDatabase, exceptions

from .config import settings

_driver = None
_local_graph: Dict[str, Dict[str, Any]] = {}


def connect_to_neo4j() -> bool:
    # Neo4j is optional at startup but used when credentials are available.
    global _driver
    try:
        if not settings.NEO4J_PASSWORD:
            return False
        if _driver is None:
            _driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
            )
            _driver.verify_connectivity()
        return True
    except (exceptions.Neo4jError, exceptions.ServiceUnavailable, ValueError) as e:
        print(f"Neo4j connection error: {e}")
        return False


def get_neo4j_session():
    # The caller can still fall back to the local graph if Neo4j is not reachable.
    global _driver
    if _driver is None and not connect_to_neo4j():
        return None
    try:
        _driver.verify_connectivity()
        return _driver.session()
    except (exceptions.Neo4jError, exceptions.ServiceUnavailable, ValueError):
        _driver = None
        return None


def _entity_id(user_id: str, entity_name: str) -> str:
    # Entity IDs are normalized so users never collide with each other.
    return f"{user_id}_{re.sub(r'[^a-zA-Z0-9]+', '_', entity_name.strip()).strip('_').lower()}"


def add_entity(user_id: str, entity_name: str, entity_type: str = "Concept") -> str:
    # This creates or updates an entity node for the current user.
    entity_id = _entity_id(user_id, entity_name)
    session = get_neo4j_session()
    if session is not None:
        with session:
            session.run(
                """
                MERGE (e:Entity {id: $entity_id})
                SET e.name = $entity_name,
                    e.entity_type = $entity_type,
                    e.user_id = $user_id
                """,
                entity_id=entity_id,
                entity_name=entity_name,
                entity_type=entity_type,
                user_id=user_id,
            )
    else:
        _local_graph.setdefault(user_id, {"entities": {}, "relationships": []})
        _local_graph[user_id]["entities"][entity_id] = {
            "id": entity_id,
            "name": entity_name,
            "entity_type": entity_type,
        }
    return entity_id


def add_relationship(user_id: str, from_entity: str, to_entity: str, relationship: str) -> None:
    # Relationships create the semantic knowledge graph edge.
    from_id = add_entity(user_id, from_entity)
    to_id = add_entity(user_id, to_entity)
    session = get_neo4j_session()
    if session is not None:
        with session:
            session.run(
                """
                MATCH (a:Entity {id: $from_id, user_id: $user_id})
                MATCH (b:Entity {id: $to_id, user_id: $user_id})
                MERGE (a)-[r:RELATIONSHIP {type: $relationship, user_id: $user_id}]->(b)
                """,
                from_id=from_id,
                to_id=to_id,
                relationship=relationship,
                user_id=user_id,
            )
    else:
        _local_graph.setdefault(user_id, {"entities": {}, "relationships": []})
        edge = {"from": from_id, "to": to_id, "type": relationship}
        if edge not in _local_graph[user_id]["relationships"]:
            _local_graph[user_id]["relationships"].append(edge)


def extract_relationship_candidates(text: str) -> Tuple[List[Tuple[str, str]], List[Tuple[str, str, str]]]:
    # These heuristics keep extraction deterministic and cheap for the project.
    entity_matches = sorted(set(re.findall(r"\b[A-Z][a-zA-Z0-9\-]{2,}(?:\s+[A-Z][a-zA-Z0-9\-]{2,})*\b", text)))
    entities = [(name, "Concept") for name in entity_matches[:20]]
    triples: List[Tuple[str, str, str]] = []
    sentence_patterns = [
        (r"([A-Z][A-Za-z0-9 ]+)\s+uses\s+([A-Z][A-Za-z0-9 ]+)", "uses"),
        (r"([A-Z][A-Za-z0-9 ]+)\s+is a\s+([A-Z][A-Za-z0-9 ]+)", "is_a"),
        (r"([A-Z][A-Za-z0-9 ]+)\s+includes\s+([A-Z][A-Za-z0-9 ]+)", "includes"),
    ]
    for pattern, relation in sentence_patterns:
        for left, right in re.findall(pattern, text, flags=re.IGNORECASE):
            triples.append((left.strip(), relation, right.strip()))
    return entities, triples[:30]


def ingest_text_into_graph(user_id: str, text: str) -> Dict[str, int]:
    # PDF processing sends extracted text here to populate the graph.
    entities, triples = extract_relationship_candidates(text)
    for entity_name, entity_type in entities:
        add_entity(user_id, entity_name, entity_type)
    for left, relation, right in triples:
        add_relationship(user_id, left, right, relation)
    return {
        "entities_extracted": len(entities),
        "relationships_extracted": len(triples),
    }


def query_knowledge_graph(user_id: str, query: str) -> List[Dict[str, Any]]:
    # Query results are shaped for direct frontend rendering.
    session = get_neo4j_session()
    if session is not None:
        with session:
            result = session.run(
                """
                MATCH (e:Entity {user_id: $user_id})
                WHERE toLower(e.name) CONTAINS toLower($query)
                OPTIONAL MATCH (e)-[r:RELATIONSHIP]->(other:Entity {user_id: $user_id})
                RETURN e, collect({relation: r.type, entity: other.name}) AS relations
                LIMIT 10
                """,
                user_id=user_id,
                query=query,
            )
            output: List[Dict[str, Any]] = []
            for record in result:
                entity = record["e"]
                output.append(
                    {
                        "entity": entity.get("name"),
                        "entity_type": entity.get("entity_type", "Concept"),
                        "relations": [item for item in record["relations"] if item.get("entity")],
                    }
                )
            return output

    user_graph = _local_graph.get(user_id, {"entities": {}, "relationships": []})
    lowered = query.lower()
    output = []
    for entity in user_graph["entities"].values():
        if lowered not in entity["name"].lower():
            continue
        relations = []
        for edge in user_graph["relationships"]:
            if edge["from"] == entity["id"]:
                target = user_graph["entities"].get(edge["to"])
                if target:
                    relations.append({"relation": edge["type"], "entity": target["name"]})
        output.append(
            {
                "entity": entity["name"],
                "entity_type": entity["entity_type"],
                "relations": relations,
            }
        )
    return output[:10]


def get_all_entities(user_id: str) -> List[Dict[str, Any]]:
    # The dashboard uses this to render graph node cards.
    session = get_neo4j_session()
    if session is not None:
        with session:
            result = session.run(
                """
                MATCH (e:Entity {user_id: $user_id})
                OPTIONAL MATCH (e)-[r:RELATIONSHIP]-()
                RETURN e, count(r) AS relation_count
                ORDER BY relation_count DESC, e.name ASC
                """,
                user_id=user_id,
            )
            return [
                {
                    "entity_id": record["e"].get("id"),
                    "name": record["e"].get("name"),
                    "entity_type": record["e"].get("entity_type", "Concept"),
                    "relation_count": record["relation_count"],
                }
                for record in result
            ]

    user_graph = _local_graph.get(user_id, {"entities": {}, "relationships": []})
    entities = []
    for entity in user_graph["entities"].values():
        relation_count = sum(
            1
            for edge in user_graph["relationships"]
            if edge["from"] == entity["id"] or edge["to"] == entity["id"]
        )
        entities.append(
            {
                "entity_id": entity["id"],
                "name": entity["name"],
                "entity_type": entity["entity_type"],
                "relation_count": relation_count,
            }
        )
    return sorted(entities, key=lambda item: (-item["relation_count"], item["name"]))


def get_graph_counts(user_id: str) -> Dict[str, int]:
    # Analytics consumes lightweight graph counts.
    session = get_neo4j_session()
    if session is not None:
        with session:
            result = session.run(
                """
                MATCH (e:Entity {user_id: $user_id})
                OPTIONAL MATCH ()-[r:RELATIONSHIP {user_id: $user_id}]->()
                RETURN count(DISTINCT e) AS nodes, count(DISTINCT r) AS relationships
                """,
                user_id=user_id,
            ).single()
            return {
                "nodes": result["nodes"],
                "relationships": result["relationships"],
            }

    user_graph = _local_graph.get(user_id, {"entities": {}, "relationships": []})
    return {
        "nodes": len(user_graph["entities"]),
        "relationships": len(user_graph["relationships"]),
    }


def clear_user_graph(user_id: str) -> None:
    # This supports resetting the current user's graph from the dashboard.
    session = get_neo4j_session()
    if session is not None:
        with session:
            session.run(
                """
                MATCH (e:Entity {user_id: $user_id})
                DETACH DELETE e
                """,
                user_id=user_id,
            )
    _local_graph[user_id] = {"entities": {}, "relationships": []}
