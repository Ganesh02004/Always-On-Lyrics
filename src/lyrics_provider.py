import httpx
import re
import os
import json

# Import our shared logger
from utils import logger

class LyricsProvider:
    def __init__(self, cache_dir=None):
        if cache_dir is None:
            # Save cache in the standard local AppData folder
            self.cache_dir = os.path.join(os.path.expanduser("~"), ".lyrics_overlay_cache")
        else:
            self.cache_dir = cache_dir
            
        os.makedirs(self.cache_dir, exist_ok=True)

    async def get_lyrics(self, title: str, artist: str, duration: float = 0.0) -> dict:
        """
        Fetches lyrics for a track, checks local cache first, queries LRCLIB API with search fallbacks,
        applies background English translations, and saves hits to cache.
        """
        if not title or not artist:
            return self._empty_response()

        # Generate cache key based on title and artist
        cache_key = self._get_cache_key(title, artist)
        cache_path = os.path.join(self.cache_dir, f"{cache_key}.json")

        # 1. Check local cache
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    cached_data = json.load(f)
                    
                # Upgrade cache dynamically if it lacks translation data from older versions
                needs_update = False
                if cached_data.get("synced") and len(cached_data["synced"]) > 0:
                    if "translation" not in cached_data["synced"][0]:
                        needs_update = True
                elif cached_data.get("static") and len(cached_data["static"]) > 0:
                    if "static_translation" not in cached_data:
                        needs_update = True

                if needs_update:
                    logger.info(f"Upgrading cache file to include translations for: {title} - {artist}")
                    cached_data = await self.translate_lyrics(cached_data)
                    try:
                        with open(cache_path, "w", encoding="utf-8") as f:
                            json.dump(cached_data, f, ensure_ascii=False, indent=2)
                    except Exception as ex:
                        logger.error(f"Failed to update cache with translations: {ex}")

                logger.info(f"Loaded cached lyrics for: {title} - {artist}")
                return cached_data
            except Exception as e:
                logger.error(f"Error reading cache: {e}")

        # 2. Query LRCLIB API using a local client bound to the active thread's event loop
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                lyrics_data = await self._fetch_from_lrclib(client, title, artist, duration)
                if lyrics_data:
                    # Parse synced & static formats
                    parsed = self._parse_lyrics_response(lyrics_data)
                    
                    # Apply background English batch translation
                    parsed = await self.translate_lyrics(parsed)
                    
                    # Write to cache
                    try:
                        with open(cache_path, "w", encoding="utf-8") as f:
                            json.dump(parsed, f, ensure_ascii=False, indent=2)
                    except Exception as e:
                        logger.error(f"Error saving to cache: {e}")
                        
                    return parsed
        except Exception as e:
            logger.error(f"LRCLIB request failed: {e}")

        return self._empty_response()

    def _get_cache_key(self, title: str, artist: str) -> str:
        """Generates a safe filename key for caching."""
        combined = f"{artist.lower()}_{title.lower()}"
        return re.sub(r'[^a-z0-9_]', '_', combined)[:100]

    async def _fetch_from_lrclib(self, client: httpx.AsyncClient, title: str, artist: str, duration: float) -> dict:
        """Queries the LRCLIB API using the provided thread-safe client."""
        # 1. Try exact lookup first
        url = "https://lrclib.net/api/get"
        params = {
            "artist_name": artist,
            "track_name": title
        }
        if duration > 0:
            params["duration"] = int(duration)

        logger.info(f"Querying LRCLIB (exact match) for: {title} - {artist} (duration: {int(duration)}s)")
        try:
            response = await client.get(url, params=params)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                logger.info("Exact match not found on LRCLIB. Trying search...")
            else:
                logger.warning(f"LRCLIB returned status {response.status_code}")
        except Exception as e:
            logger.error(f"Exact lookup error: {e}")

        # 2. Try Search API as fallback
        search_url = "https://lrclib.net/api/search"
        search_params = {
            "q": f"{title} {artist}"
        }
        try:
            response = await client.get(search_url, params=search_params)
            if response.status_code == 200:
                results = response.json()
                if results and len(results) > 0:
                    logger.info(f"Search found {len(results)} matches. Using first result.")
                    return results[0]
            logger.info("No search results found on LRCLIB.")
        except Exception as e:
            logger.error(f"Search lookup error: {e}")

        return None

    def _parse_lyrics_response(self, data: dict) -> dict:
        """Parses the LRCLIB response into structured format."""
        is_instrumental = data.get("instrumental", False)
        
        raw_synced = data.get("syncedLyrics", "")
        raw_static = data.get("plainLyrics", "")
        
        synced_parsed = None
        if raw_synced:
            synced_parsed = self._parse_lrc(raw_synced)
            
        static_parsed = None
        if raw_static:
            static_parsed = [line.strip() for line in raw_static.splitlines() if line.strip()]
        elif raw_synced and not synced_parsed:
            lines = []
            for line in raw_synced.splitlines():
                clean = re.sub(r'\[\d{2}:\d{2}\.\d{2,3}\]', '', line).strip()
                if clean:
                    lines.append(clean)
            if lines:
                static_parsed = lines

        return {
            "synced": synced_parsed,
            "static": static_parsed,
            "raw_synced": raw_synced,
            "raw_static": raw_static,
            "is_instrumental": is_instrumental
        }

    def _parse_lrc(self, lrc_text: str) -> list:
        """Parses LRC synced lyrics text."""
        if not lrc_text:
            return None
            
        parsed_lines = []
        pattern = re.compile(r'\[(\d{2}):(\d{2})\.(\d{2,3})\]')
        
        for line in lrc_text.splitlines():
            line = line.strip()
            if not line:
                continue
                
            matches = list(pattern.finditer(line))
            if not matches:
                continue
                
            text = pattern.sub('', line).strip()
            
            for m in matches:
                minutes = m.group(1)
                seconds = m.group(2)
                ms_str = m.group(3)
                
                # Check for clean integer parsing
                try:
                    mins = int(minutes)
                    secs = int(seconds)
                    if len(ms_str) == 2:
                        ms = int(ms_str) * 10
                    else:
                        ms = int(ms_str)
                    
                    total_seconds = mins * 60 + secs + ms / 1000.0
                    parsed_lines.append({
                        "time": total_seconds,
                        "text": text
                    })
                except ValueError:
                    continue
                
        parsed_lines.sort(key=lambda x: x["time"])
        return parsed_lines if parsed_lines else None

    async def translate_lyrics(self, parsed: dict) -> dict:
        """
        Translates both synced and static lyrics in the parsed response
        and stores them under 'translation' and 'static_translation' keys.
        """
        synced = parsed.get("synced")
        static = parsed.get("static")
        
        # 1. Translate Synced Lyrics
        if synced:
            try:
                # Extract non-empty lines to translate
                texts = [line["text"] for line in synced]
                translated_texts = await self._batch_translate(texts)
                
                if translated_texts and len(translated_texts) == len(synced):
                    for i, line in enumerate(synced):
                        trans = translated_texts[i].strip()
                        # If translation is case-insensitively identical to the original line,
                        # we keep translation empty to avoid displaying duplicate lines on screen.
                        if trans.lower() == line["text"].strip().lower():
                            line["translation"] = ""
                        else:
                            line["translation"] = trans
                else:
                    # Mismatch or error: set empty translation for safety
                    for line in synced:
                        line["translation"] = ""
            except Exception as e:
                logger.error(f"Error translating synced lyrics: {e}")
                for line in synced:
                    line["translation"] = ""
        
        # 2. Translate Static Lyrics Fallback
        if static:
            try:
                translated_static = await self._batch_translate(static)
                if translated_static and len(translated_static) == len(static):
                    parsed["static_translation"] = [
                        ("" if trans.lower() == orig.lower() else trans)
                        for orig, trans in zip(static, translated_static)
                    ]
                else:
                    parsed["static_translation"] = [""] * len(static)
            except Exception as e:
                logger.error(f"Error translating static lyrics: {e}")
                parsed["static_translation"] = [""] * len(static)
                
        return parsed

    async def _batch_translate(self, texts: list) -> list:
        """Translates a list of strings to English in a single batch request using the free Google Translate API."""
        if not texts:
            return []
            
        try:
            # Join texts with newlines. We use standard newlines which Google Translate respects.
            full_text = "\n".join(texts)
            
            url = "https://translate.googleapis.com/translate_a/single"
            params = {
                "client": "gtx",
                "sl": "auto",
                "tl": "en",
                "dt": "t",
                "q": full_text
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    translated_segments = data[0]
                    
                    # Google Translate response structure:
                    # [[["trans_1", "orig_1", ...], ["trans_2", "orig_2", ...]]]
                    translated_lines = []
                    for segment in translated_segments:
                        if segment and len(segment) > 0 and segment[0]:
                            translated_lines.append(segment[0])
                            
                    # Sometimes the response segments can be split/joined slightly differently if Google Translate consolidates.
                    # In case of mismatch, we attempt to split by newline from the consolidated string.
                    if len(translated_lines) != len(texts):
                        consolidated = "".join([s[0] for s in translated_segments if s and s[0]])
                        split_lines = consolidated.split("\n")
                        if len(split_lines) == len(texts):
                            return split_lines
                        else:
                            logger.warning(f"Batch translation count mismatch: got {len(translated_lines)} (or split {len(split_lines)}), expected {len(texts)}")
                            return []
                    return [line.strip() for line in translated_lines]
        except Exception as e:
            logger.error(f"Batch translation network error: {e}")
        return []

    def _empty_response(self) -> dict:
        return {
            "synced": None,
            "static": None,
            "raw_synced": None,
            "raw_static": None,
            "is_instrumental": False
        }

    async def close(self):
        # Kept for backward compatibility, no persistent client to close
        pass
