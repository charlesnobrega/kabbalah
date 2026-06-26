"""Bitwarden-backed secret access wrapper.

This module never stores secrets and never reads repository `.env` files. It
expects an authenticated Bitwarden CLI session through the `BW_SESSION`
environment variable and returns only the requested field value to callers.
"""

from __future__ import annotations

import json
import os
import subprocess
from typing import Callable, Mapping, Optional, Sequence


class CofreError(Exception):
    """Base error for vault access failures."""


class CofreSecretNotFound(CofreError):
    """Raised when the requested item or field cannot be found."""


Runner = Callable[[Sequence[str]], subprocess.CompletedProcess]


class CofreBitwarden:
    """Small Bitwarden CLI adapter for retrieving named secret fields."""

    def __init__(
        self,
        *,
        runner: Optional[Callable[..., subprocess.CompletedProcess]] = None,
        timeout: float = 15.0,
        env: Optional[Mapping[str, str]] = None,
    ):
        self._runner = runner or subprocess.run
        self._timeout = timeout
        self._env = dict(env) if env is not None else None

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

        result = self._run(["bw", "get", "item", item_name])
        if result.returncode != 0:
            raise CofreSecretNotFound(f"Bitwarden item not found or inaccessible: {item_name}")

        try:
            item = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise CofreError("Bitwarden returned invalid JSON") from exc

        for field in item.get("fields", []) or []:
            if field.get("name") == field_name and field.get("value"):
                return field["value"]

        if field_name in item and item[field_name]:
            return item[field_name]

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
