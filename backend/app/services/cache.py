import os
import json
import redis
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

redis_client = redis.from_url(REDIS_URL, decode_responses=True)

VALHALLA_CACHE_TTL = 600  # 10 minutes


def get_cached_match(geohash: str) -> dict | None:
    key = f"valhalla:match:{geohash}"
    cached = redis_client.get(key)
    if cached:
        return json.loads(cached)
    return None


def set_cached_match(geohash: str, result: dict) -> None:
    key = f"valhalla:match:{geohash}"
    redis_client.set(key, json.dumps(result), ex=VALHALLA_CACHE_TTL)


def get_cache_stats() -> dict:
    info = redis_client.info("stats")
    return {
        "hits": info.get("keyspace_hits", 0),
        "misses": info.get("keyspace_misses", 0)
    }