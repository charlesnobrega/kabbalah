"""Bitwarden-backed secret access wrapper.

This module never stores secrets and never reads repository `.env` files. It
expects an authenticated Bitwarden CLI session through the `BW_SESSION`
environment variable and returns only the requested field value to callers.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass
from typing import Callable, Dict, Mapping, Optional, Sequence, Tuple


CACHE_TTL = 300


class CofreError(Exception):
    """Base error for vault access failures."""


class CofreSecretNotFound(CofreError):
    """Raised when the requested item or field cannot be found."""


Runner = Callable[[Sequence[str]], subprocess.CompletedProcess]


@dataclass(frozen=True)
class Segredo:
    """Secret value returned from Bitwarden.

    The value is intentionally hidden from repr to avoid accidental log leaks.
    """

    item_name: str
    field_name: str
    value: str
    created_at: float = 0.0

    def __repr__(self) -> str:
        return (
            "Segredo("
            f"item_name={self.item_name!r}, "
            f"field_name={self.field_name!r}, "
            "value='***'"
            ")"
        )


class CofreBitwarden:
    """Small Bitwarden CLI adapter for retrieving named secret fields."""

    def __init__(
        self,
        *,
        runner: Optional[Callable[..., subprocess.CompletedProcess]] = None,
        timeout: float = 15.0,
        env: Optional[Mapping[str, str]] = None,
        use_cache: bool = False,
        cache_ttl: int = CACHE_TTL,
    ):
        self._runner = runner or subprocess.run
        self._timeout = timeout
        self._env = dict(env) if env is not None else None
        self._use_cache = use_cache
        self._cache_ttl = cache_ttl
        self._cache: Dict[Tuple[str, str], Segredo] = {}

    def testar_conexao(self) -> bool:
        """Return whether the Bitwarden CLI session is usable."""

        session = self._session()
        if not session:
            return False

        result = self._run(["bw", "status"])
        return result.returncode == 0

    def get_chave(self, item_name: str, *, field_name: str = "api_key") -> str:
        """Retrieve a field value from a Bitwarden item.

        Args:
            item_name: Bitwarden item name or ID.
            field_name: Custom field name to retrieve.
        """

        if not item_name:
            raise CofreError("item_name must be a non-empty string")
        if not field_name:
            raise CofreError("field_name must be a non-empty string")
        if not self._session():
            raise CofreError("BW_SESSION is required for Bitwarden CLI access")

        cache_key = (item_name, field_name)
        cached = self._cache.get(cache_key) if self._use_cache else None
        if cached and time.time() - cached.created_at <= self._cache_ttl:
            return cached.value

        result = self._run(["bw", "get", "item", item_name])
        if result.returncode != 0:
            raise CofreSecretNotFound(f"Bitwarden item not found or inaccessible: {item_name}")

        try:
            item = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise CofreError("Bitwarden returned invalid JSON") from exc

        for field in item.get("fields", []) or []:
            if field.get("name") == field_name and field.get("value"):
                return self._store_cache(cache_key, item_name, field_name, field["value"])

        if field_name in item and item[field_name]:
            return self._store_cache(cache_key, item_name, field_name, item[field_name])

        raise CofreSecretNotFound(
            f"Field '{field_name}' not found in Bitwarden item '{item_name}'"
        )

    def _session(self) -> Optional[str]:
        env = self._effective_env()
        return env.get("BW_SESSION")

    def _effective_env(self) -> dict[str, str]:
        env = dict(os.environ)
        if self._env:
            env.update(self._env)
        return env

    def _run(self, args: Sequence[str]):
        return self._runner(
            list(args),
            timeout=self._timeout,
            env=self._effective_env(),
        )

    def _store_cache(
        self,
        cache_key: Tuple[str, str],
        item_name: str,
        field_name: str,
        value: str,
    ) -> str:
        if self._use_cache:
            self._cache[cache_key] = Segredo(
                item_name=item_name,
                field_name=field_name,
                value=value,
                created_at=time.time(),
            )
        return value
