"""
Disk-backed cache for deterministic LLM generation results (issue #20).

Profile and simulation-config generation re-issue the same expensive LLM calls
whenever a campaign is re-run on the same entities. Keying a small on-disk cache
by a hash of the request (model + system + prompt) lets identical requests skip
the model entirely.

One JSON file per entry under ``<cache_dir>/<namespace>/<sha>.json`` so
concurrent generation never rewrites a single shared store. Reads and writes are
best-effort: any failure degrades to a cache miss rather than raising.
"""

import hashlib
import json
import os
import time
from typing import Any, Optional

from ..config import Config
from .logger import get_logger

logger = get_logger('mirofish.llm_cache')


def hash_key(material: Any) -> str:
    """Stable SHA-256 over the canonical JSON of the request material."""
    canonical = json.dumps(material, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


class LLMResponseCache:
    """Namespaced, content-addressed cache for LLM responses."""

    def __init__(
        self,
        namespace: str,
        *,
        enabled: Optional[bool] = None,
        cache_dir: Optional[str] = None,
        ttl: Optional[int] = None,
    ):
        self.namespace = namespace
        self.enabled = Config.LLM_CACHE_ENABLED if enabled is None else enabled
        base_dir = cache_dir if cache_dir is not None else Config.LLM_CACHE_DIR
        self.dir = os.path.join(base_dir, namespace)
        self.ttl = Config.LLM_CACHE_TTL if ttl is None else ttl

    def _path(self, key: str) -> str:
        return os.path.join(self.dir, f"{key}.json")

    def get(self, material: Any) -> Optional[Any]:
        """Return the cached value for ``material``, or None on miss/expiry/error."""
        if not self.enabled:
            return None
        path = self._path(hash_key(material))
        if not os.path.exists(path):
            return None
        try:
            with open(path, 'r', encoding='utf-8') as handle:
                entry = json.load(handle)
        except (OSError, json.JSONDecodeError):
            return None
        if self.ttl and self.ttl > 0:
            if time.time() - entry.get('stored_at', 0) > self.ttl:
                return None
        return entry.get('value')

    def set(self, material: Any, value: Any) -> None:
        """Store ``value`` for ``material``. Best-effort; never raises."""
        if not self.enabled:
            return
        path = self._path(hash_key(material))
        try:
            os.makedirs(self.dir, exist_ok=True)
            tmp_path = f"{path}.tmp"
            with open(tmp_path, 'w', encoding='utf-8') as handle:
                json.dump({'stored_at': time.time(), 'value': value}, handle, ensure_ascii=False)
            os.replace(tmp_path, path)  # atomic publish
        except OSError as exc:
            logger.warning("Failed to write LLM cache entry (%s): %s", self.namespace, exc)
