import time
import html
import httpx
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone

from app.core.config import settings
from app.services.providers.base_provider import BaseProvider, PersistentQuotaTracker


# Curated high-relevance educational videos for common technical skills (zero-API fallback)
CURATED_SKILL_VIDEOS: Dict[str, List[Dict[str, Any]]] = {
    "python": [
        {
            "video_id": "_uQrJ0TkZlc",
            "title": "Python Full Course for Beginners [2026 Edition]",
            "channel_title": "Programming with Mosh",
            "thumbnail_url": "https://i.ytimg.com/vi/_uQrJ0TkZlc/hqdefault.jpg",
            "video_url": "https://www.youtube.com/watch?v=_uQrJ0TkZlc",
            "published_at": "2024-06-15T00:00:00Z",
            "is_curated": True
        },
        {
            "video_id": "rfscVS0vtbw",
            "title": "Learn Python - Full Course for Beginners [Tutorial]",
            "channel_title": "freeCodeCamp.org",
            "thumbnail_url": "https://i.ytimg.com/vi/rfscVS0vtbw/hqdefault.jpg",
            "video_url": "https://www.youtube.com/watch?v=rfscVS0vtbw",
            "published_at": "2023-11-01T00:00:00Z",
            "is_curated": True
        }
    ],
    "fastapi": [
        {
            "video_id": "0sOvCWFmrtA",
            "title": "Python FastAPI Tutorial: Build a Complete REST API",
            "channel_title": "freeCodeCamp.org",
            "thumbnail_url": "https://i.ytimg.com/vi/0sOvCWFmrtA/hqdefault.jpg",
            "video_url": "https://www.youtube.com/watch?v=0sOvCWFmrtA",
            "published_at": "2023-08-20T00:00:00Z",
            "is_curated": True
        },
        {
            "video_id": "gQTRsZpqjAw",
            "title": "FastAPI in 100 Seconds",
            "channel_title": "Fireship",
            "thumbnail_url": "https://i.ytimg.com/vi/gQTRsZpqjAw/hqdefault.jpg",
            "video_url": "https://www.youtube.com/watch?v=gQTRsZpqjAw",
            "published_at": "2023-01-15T00:00:00Z",
            "is_curated": True
        }
    ],
    "docker": [
        {
            "video_id": "fqMOX6JJhGo",
            "title": "Docker Tutorial for Beginners [Full Course]",
            "channel_title": "TechWorld with Nana",
            "thumbnail_url": "https://i.ytimg.com/vi/fqMOX6JJhGo/hqdefault.jpg",
            "video_url": "https://www.youtube.com/watch?v=fqMOX6JJhGo",
            "published_at": "2024-01-10T00:00:00Z",
            "is_curated": True
        },
        {
            "video_id": "pTFZFxd4hOI",
            "title": "Docker in 100 Seconds",
            "channel_title": "Fireship",
            "thumbnail_url": "https://i.ytimg.com/vi/pTFZFxd4hOI/hqdefault.jpg",
            "video_url": "https://www.youtube.com/watch?v=pTFZFxd4hOI",
            "published_at": "2023-05-12T00:00:00Z",
            "is_curated": True
        }
    ],
    "kubernetes": [
        {
            "video_id": "X48VuDVv0do",
            "title": "Kubernetes Tutorial for Beginners [Full Course in 4 Hours]",
            "channel_title": "TechWorld with Nana",
            "thumbnail_url": "https://i.ytimg.com/vi/X48VuDVv0do/hqdefault.jpg",
            "video_url": "https://www.youtube.com/watch?v=X48VuDVv0do",
            "published_at": "2023-09-05T00:00:00Z",
            "is_curated": True
        }
    ],
    "typescript": [
        {
            "video_id": "BwuLxPH8IDs",
            "title": "TypeScript Course for Beginners - Learn TypeScript from Scratch",
            "channel_title": "freeCodeCamp.org",
            "thumbnail_url": "https://i.ytimg.com/vi/BwuLxPH8IDs/hqdefault.jpg",
            "video_url": "https://www.youtube.com/watch?v=BwuLxPH8IDs",
            "published_at": "2023-04-18T00:00:00Z",
            "is_curated": True
        }
    ],
    "angular": [
        {
            "video_id": "3qBXWUpoPHo",
            "title": "Angular Crash Course for Beginners",
            "channel_title": "Traversy Media",
            "thumbnail_url": "https://i.ytimg.com/vi/3qBXWUpoPHo/hqdefault.jpg",
            "video_url": "https://www.youtube.com/watch?v=3qBXWUpoPHo",
            "published_at": "2024-02-14T00:00:00Z",
            "is_curated": True
        }
    ],
    "postgresql": [
        {
            "video_id": "qw--VYLpxG4",
            "title": "PostgreSQL Tutorial for Beginners - Full Course",
            "channel_title": "freeCodeCamp.org",
            "thumbnail_url": "https://i.ytimg.com/vi/qw--VYLpxG4/hqdefault.jpg",
            "video_url": "https://www.youtube.com/watch?v=qw--VYLpxG4",
            "published_at": "2023-07-22T00:00:00Z",
            "is_curated": True
        }
    ],
    "scikit-learn": [
        {
            "video_id": "0B5eIE_1vpU",
            "title": "Machine Learning with Scikit-Learn - Complete Tutorial",
            "channel_title": "freeCodeCamp.org",
            "thumbnail_url": "https://i.ytimg.com/vi/0B5eIE_1vpU/hqdefault.jpg",
            "video_url": "https://www.youtube.com/watch?v=0B5eIE_1vpU",
            "published_at": "2023-10-10T00:00:00Z",
            "is_curated": True
        }
    ]
}


class YouTubeAdapter(BaseProvider):
    """
    YouTube Data API v3 Adapter for discovering educational programming videos.
    Operates under the Zero-Cost Policy:
    - Daily safety cap (25 requests/day = 2,500 units out of 10,000 free quota).
    - Synchronized persistent quota accounting via PersistentQuotaTracker.
    - In-memory result caching (1 hour TTL).
    - Safe graceful fallback to curated tutorials when key is missing or quota is exhausted.
    """
    _cache: Dict[str, Tuple[float, List[Dict[str, Any]]]] = {}

    def __init__(self, api_key: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.api_key = api_key or settings.YOUTUBE_API_KEY
        self.endpoint = "https://www.googleapis.com/youtube/v3/search"
        self.daily_request_cap = getattr(settings, "YOUTUBE_DAILY_QUOTA", 25)

    @property
    def provider_name(self) -> str:
        return "youtube"

    @property
    def display_name(self) -> str:
        return "YouTube Data API"

    @property
    def tier(self) -> int:
        return 2

    @property
    def free_tier_info(self) -> str:
        return "YouTube Data API v3 (10,000 quota units/day free allowance, 100 units/search, ~25 calls/day safe limit)"

    def is_configured(self) -> bool:
        return bool(self.api_key and len(self.api_key.strip()) > 5)

    async def search_jobs(self, *args, **kwargs):
        # Educational video provider does not discover job vacancies
        return []

    async def search_companies(self, *args, **kwargs):
        return []

    def get_curated_videos(self, skill_name: str, limit: int = 3) -> List[Dict[str, Any]]:
        """
        Returns high-quality, verified educational videos from curated catalog.
        Requires zero API calls and zero network requests.
        """
        norm_skill = skill_name.lower().strip().replace(" ", "-").replace("_", "-")
        if norm_skill in CURATED_SKILL_VIDEOS:
            return CURATED_SKILL_VIDEOS[norm_skill][:limit]
        
        # Check partial matching
        for k, videos in CURATED_SKILL_VIDEOS.items():
            if k in norm_skill or norm_skill in k:
                return videos[:limit]
        return []

    async def search_videos(
        self,
        query: str,
        limit: int = 5,
        prefer_curated_fallback: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Searches for technical tutorial videos on YouTube.
        If unconfigured, rate-limited, or quota-exhausted, safely returns curated public tutorials.
        """
        norm_query = query.lower().strip()
        cache_key = f"{norm_query}:{limit}"

        # 1. Check in-memory cache (TTL: 3600 seconds)
        now_ts = time.time()
        if cache_key in self._cache:
            cached_time, cached_results = self._cache[cache_key]
            if now_ts - cached_time < 3600:
                return cached_results

        # 2. Check eligibility & quota
        can_run, reason = self.can_query()
        if not can_run:
            self._last_error = reason
            if prefer_curated_fallback:
                return self.get_curated_videos(query, limit=limit)
            return []

        # 3. Execute YouTube Data API query
        params = {
            "part": "snippet",
            "q": f"{query} programming tutorial developer",
            "type": "video",
            "videoEmbeddable": "true",
            "maxResults": min(max(1, limit), 10),
            "key": self.api_key,
            "relevanceLanguage": "en"
        }

        t0 = time.time()
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(self.endpoint, params=params)

            latency_ms = (time.time() - t0) * 1000

            if resp.status_code == 200:
                data = resp.json()
                items = data.get("items", [])
                videos = []
                for item in items:
                    vid_id = item.get("id", {}).get("videoId")
                    if not vid_id:
                        continue
                    snippet = item.get("snippet", {})
                    videos.append({
                        "video_id": vid_id,
                        "title": html.unescape(snippet.get("title", "")),
                        "channel_title": snippet.get("channelTitle", "YouTube"),
                        "description": snippet.get("description", ""),
                        "thumbnail_url": snippet.get("thumbnails", {}).get("medium", {}).get("url", ""),
                        "video_url": f"https://www.youtube.com/watch?v={vid_id}",
                        "published_at": snippet.get("publishedAt"),
                        "is_curated": False
                    })

                self.record_query_success(latency_ms=latency_ms, results_count=len(videos))
                self._cache[cache_key] = (now_ts, videos)
                return videos

            elif resp.status_code == 403:
                err_text = resp.text.lower()
                if "quotaexceeded" in err_text or "dailylimitexceeded" in err_text:
                    self.record_quota_exhausted("YouTube Data API quota exceeded")
                else:
                    self.record_query_error(f"YouTube 403 error: {resp.text[:120]}", is_auth_error=True)
            elif resp.status_code in (401, 400):
                self.record_query_error(f"YouTube auth/param error ({resp.status_code}): {resp.text[:120]}", is_auth_error=True)
            else:
                self.record_query_error(f"YouTube HTTP {resp.status_code}")

        except httpx.TimeoutException:
            self.record_query_error("YouTube query timed out")
        except Exception as e:
            self.record_query_error(f"YouTube query failed: {str(e)}")

        # Fallback to curated tutorials on any API error or quota limitation
        if prefer_curated_fallback:
            return self.get_curated_videos(query, limit=limit)
        return []
