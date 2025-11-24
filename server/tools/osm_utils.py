# backend/tools/osm_utils.py
import overpy
import time
import logging
from pathlib import Path
from typing import Dict
from config import config

logger = logging.getLogger(__name__)

# Global Overpass client (reuse connection)
overpass_api = overpy.Overpass()

# Cache file per city (e.g. knowledge/osm_berlin.md)
CACHE_DIR = config.KNOWLEDGE_PATH
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# How long to keep cached OSM data (12 hours = more than enough, OSM changes slowly)
CACHE_TTL_SECONDS = 12 * 60 * 60  # 12 hours


def _cache_path(city: str) -> Path:
    """Standardized cache filename."""
    city_key = city.lower().replace(" ", "_")
    return CACHE_DIR / f"osm_{city_key}.md"


def _is_cache_valid(cache_file: Path) -> bool:
    """Check if cached file exists and is fresh."""
    if not cache_file.exists():
        return False
    age = time.time() - cache_file.stat().st_mtime
    return age < CACHE_TTL_SECONDS


def _save_cache(city: str, markdown: str):
    cache_file = _cache_path(city)
    try:
        cache_file.write_text(markdown, encoding="utf-8")
        logger.info(f"OSM data cached → {cache_file.name}")
    except Exception as e:
        logger.warning(f"Failed to write cache {cache_file}: {e}")


def _load_cache(city: str) -> str | None:
    cache_file = _cache_path(city)
    if _is_cache_valid(cache_file):
        try:
            content = cache_file.read_text(encoding="utf-8")
            logger.info(f"OSM data loaded from cache → {cache_file.name}")
            return content
        except Exception as e:
            logger.warning(f"Failed to read cache {cache_file}: {e}")
    return None

def fetch_city_resources(city: str) -> str:
    """
    Returns markdown with emergency facilities for the given city.
    Uses cached version if fresh, otherwise queries Overpass.
    """
    city_key = city.lower().replace(" ", "_")

    # 1. Try cache first
    cached = _load_cache(city_key)
    if cached:
        return cached

    # 2. CORRECT Overpass query — NO {{ }} — uses proper union with ()
    query = f'''
[out:json][timeout:90];
(
  area["name"="{city}"]["admin_level"="8"];
  area["name:en"="{city}"]["admin_level"="8"];
  area["name:pl"="{city}"]["admin_level"="8"];
  area["name:de"="{city}"]["admin_level"="8"];
  area["name:uk"="{city}"]["admin_level"="8"];
)->.search_area;

(
  nwr["amenity"="social_facility"]["social_facility:for"~"refugee|displaced|homeless"](area.search_area);
  nwr["emergency"="shelter"](area.search_area);
  nwr["amenity"~"clinic|hospital|doctors"](area.search_area);
  nwr["amenity"="food_bank"](area.search_area);
  nwr["office"="ngo"]["operator"~"(Red Cross|UNHCR|Caritas|IOM)"](area.search_area);
  nwr["amenity"="community_centre"]["community_centre:for"~"refugee"](area.search_area);
);
out center meta;
>;
out skel qt;
'''

    try:
        logger.info(f"Querying Overpass for city: {city}")
        result = overpass_api.query(query)

        md = f"# Emergency Resources in {city.title()}\n"
        md += f"_Updated: {time.strftime('%Y-%m-%d %H:%M UTC')}_\n\n"

        if not (result.nodes or result.ways or result.relations):
            md += ("No specific refugee facilities found in OpenStreetMap yet.\n\n"
                   "**Immediate actions:**\n"
                   "- Go to the main train station (often has help desks)\n"
                   "- Look for Red Cross, UNHCR, or government tents\n"
                   "- Call local emergency services\n")
        else:
            for elem in sorted(
                result.nodes + result.ways + result.relations,
                key=lambda x: x.tags.get("name", "zzz").lower()
            ):
                tags = elem.tags
                name = tags.get("name", "Unnamed facility")
                operator = tags.get("operator", "")
                amenity = tags.get("amenity", tags.get("office", "facility"))
                
                lat = lon = None
                if hasattr(elem, "lat"):
                    lat, lon = elem.lat, elem.lon
                elif hasattr(elem, "center_lat"):
                    lat, lon = elem.center_lat, elem.center_lon

                address = tags.get("addr:full") or f"{tags.get('addr:street','')} {tags.get('addr:housenumber','')}".strip()
                if not address.strip():
                    address = "Address not listed"
                phone = tags.get("phone") or tags.get("contact:phone") or "Not listed"

                md += f"### {name}"
                if operator:
                    md += f" – {operator}"
                md += f"\n**Type:** {amenity.replace('_', ' ').title()}\n"
                md += f"- **Address:** {address}\n"
                if phone != "Not listed":
                    md += f"- **Phone:** {phone}\n"
                if lat and lon:
                    md += f"- **Map:** https://osm.org/go/{lat}/{lon}?m=\n"
                md += "\n"

        _save_cache(city_key, md)
        return md

    except Exception as e:
        logger.error(f"Overpass query failed for {city}: {e}")
        fallback = f"# {city.title()} – Limited Data\n\nNo live data available.\n\n**Go to main train station or look for Red Cross / UNHCR tents.**\n"
        _save_cache(city_key, fallback)
        return fallback