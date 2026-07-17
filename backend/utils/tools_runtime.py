from typing import Dict, List
from urllib.parse import quote

import httpx

from .config import settings


async def weather_tool(query: str) -> Dict[str, str]:
    # This uses Open-Meteo geocoding-compatible defaults for Hyderabad when no city is parsed.
    city = "Hyderabad"
    if " in " in query.lower():
        city = query.split(" in ", 1)[1].strip().rstrip("?")
    geocode_url = f"https://geocoding-api.open-meteo.com/v1/search?name={quote(city)}&count=1"
    async with httpx.AsyncClient(timeout=15) as client:
        geo_response = await client.get(geocode_url)
        geo_response.raise_for_status()
        geo_data = geo_response.json()
        results = geo_data.get("results", [])
        if not results:
            return {"tool_name": "weather", "input_query": query, "output_summary": f"No weather match found for {city}."}
        match = results[0]
        forecast = await client.get(
            settings.OPEN_METEO_BASE_URL,
            params={
                "latitude": match["latitude"],
                "longitude": match["longitude"],
                "current": "temperature_2m,wind_speed_10m,weather_code",
            },
        )
        forecast.raise_for_status()
        current = forecast.json().get("current", {})
    summary = (
        f"Weather in {match['name']}: {current.get('temperature_2m', 'unknown')}°C, "
        f"wind {current.get('wind_speed_10m', 'unknown')} km/h."
    )
    return {"tool_name": "weather", "input_query": query, "output_summary": summary}


async def news_tool(query: str) -> Dict[str, str]:
    # Hacker News search provides fresh news headlines without a private API key.
    topic = query.replace("news", "").strip() or "AI"
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(settings.HN_SEARCH_BASE_URL, params={"query": topic, "tags": "story"})
        response.raise_for_status()
        hits = response.json().get("hits", [])[:3]
    if not hits:
        summary = f"No recent headlines found for {topic}."
    else:
        summary = " | ".join(hit.get("title") or "Untitled story" for hit in hits)
    return {"tool_name": "news", "input_query": query, "output_summary": summary}


async def wikipedia_tool(query: str) -> Dict[str, str]:
    # Wikipedia summary is useful for general knowledge questions outside the uploaded docs.
    topic = query.strip().rstrip("?")
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(f"{settings.WIKIPEDIA_SUMMARY_BASE_URL}/{quote(topic)}")
    if response.status_code >= 400:
        summary = f"No Wikipedia summary found for {topic}."
    else:
        summary = response.json().get("extract", f"No summary found for {topic}.")
    return {"tool_name": "wikipedia", "input_query": query, "output_summary": summary}


async def execute_tools(tool_names: List[str], query: str) -> List[Dict[str, str]]:
    # The router can request one or more tools and this dispatcher runs them sequentially.
    results: List[Dict[str, str]] = []
    for tool_name in tool_names:
        if tool_name == "weather":
            results.append(await weather_tool(query))
        elif tool_name == "news":
            results.append(await news_tool(query))
        elif tool_name == "wikipedia":
            results.append(await wikipedia_tool(query))
    return results
