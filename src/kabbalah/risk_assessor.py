"""Pluggable risk assessors for the Qlipot intent evaluation pipeline.

This module defines the QlipotRiskAssessor protocol and provides two concrete
implementations: a fast local keyword-based heuristic assessor (fallback)
and an LLM-based assessor that routes requests to independent models.
"""

import base64
import json
import logging
import re
import unicodedata
from typing import Any, Dict, Optional, Protocol

logger = logging.getLogger(__name__)

# Common Cyrillic/Greek homoglyphs folded to Latin before keyword matching.
_HOMOGLIFOS = {
    "а": "a",
    "в": "b",
    "с": "c",
    "е": "e",
    "н": "h",
    "к": "k",
    "м": "m",
    "о": "o",
    "р": "p",
    "т": "t",
    "х": "x",
    "у": "y",
    "і": "i",
    "ѕ": "s",
    "ԁ": "d",
    "α": "a",
    "β": "b",
    "ε": "e",
    "ι": "i",
    "κ": "k",
    "ν": "v",
    "ο": "o",
    "ρ": "p",
    "τ": "t",
    "υ": "u",
    "χ": "x",
}

# Real destructive command shapes, beyond simple keyword presence.
_PADROES_CRITICOS = [
    re.compile(pattern)
    for pattern in (
        r"\brm\s+-[a-z]*[rf]",
        r"\bdel\s+/[fsq]",
        r"\bformat\s+[a-z]:",
        r"\bmkfs(\.|\s)",
        r"\bdd\s+if=",
        r"\bshutdown\b",
        r"\bdrop\s+(table|database)\b",
        r"\btruncate\s+table\b",
        r":\(\)\s*\{.*\}\s*;\s*:",
        r"(curl|wget)[^|;&]*\|\s*(ba|z|da)?sh",
        r"powershell[^\n]*-enc",
        r"base64\s+(-d|--decode)[^|]*\|",
        r"\bgit\s+push\b.*--force",
        r"\bchmod\s+777\b",
    )
]

_BASE64_RUN = re.compile(r"[A-Za-z0-9+/]{16,}={0,2}")


def _normalizar_texto(texto: str) -> str:
    """Fold encodings that keyword heuristics would otherwise miss."""
    texto = unicodedata.normalize("NFKC", texto)
    texto = "".join(ch for ch in texto if unicodedata.category(ch) != "Cf")
    texto = texto.casefold()
    return "".join(_HOMOGLIFOS.get(ch, ch) for ch in texto)


class QlipotRiskAssessor(Protocol):
    """Protocol defining a pluggable risk assessor for Qlipot."""

    @property
    def identity(self) -> str:
        """Unique identifier/name of this assessor."""
        ...

    @property
    def version(self) -> str:
        """Version stamp of this assessor's logic/model."""
        ...

    def assess_risk(self, ferramenta: str, argumentos: Dict[str, Any], pedido: str = "") -> float:
        """Assess the isolation risk score (between 0.0 and 1.0) of a request."""
        ...


class HeuristicRiskAssessor:
    """Keyword and pattern-based risk assessor (wave 3 logic)."""

    _AUDIT_TERMS = (
        "token",
        "secret",
        "credential",
        "produção",
        "production",
        "senha",
        "password",
        "credencial",
        "api_key",
        "apikey",
        "chave privada",
        "private key",
    )
    _HIGH_TERMS = ("execute_command", "shell", "exec", "network_request", "post")
    _CRITICAL_TERMS = (
        "delete",
        "remove",
        "drop",
        "reset",
        "force",
        "exfiltrate",
        "apagar",
        "excluir",
        "destruir",
        "destroy",
        "wipe",
        "erase",
        "purge",
        "exfiltrar",
    )

    def __init__(self, version: str = "wave10-2026.07"):
        self._version = version

    @property
    def identity(self) -> str:
        return "heuristic-offline"

    @property
    def version(self) -> str:
        return self._version

    def assess_risk(self, ferramenta: str, argumentos: Dict[str, Any], pedido: str = "") -> float:
        bruto = f"{pedido} {ferramenta} {argumentos}"
        risco = max(0.10, self._score_termos(_normalizar_texto(bruto)))
        risco = max(risco, self._score_payloads_codificados(bruto))
        return risco

    def _score_termos(self, texto_normalizado: str) -> float:
        risco = 0.0
        if any(term in texto_normalizado for term in self._AUDIT_TERMS):
            risco = max(risco, 0.50)
        if any(term in texto_normalizado for term in self._HIGH_TERMS):
            risco = max(risco, 0.70)
        if any(term in texto_normalizado for term in self._CRITICAL_TERMS):
            risco = max(risco, 0.96)
        if any(pattern.search(texto_normalizado) for pattern in _PADROES_CRITICOS):
            risco = max(risco, 0.96)
        return risco

    def _score_payloads_codificados(self, texto_bruto: str) -> float:
        risco = 0.0
        for match in _BASE64_RUN.finditer(texto_bruto):
            candidato = match.group(0)
            try:
                decoded = base64.b64decode(candidato + "=" * (-len(candidato) % 4)).decode("utf-8", errors="strict")
            except Exception:
                continue
            if not decoded.isprintable():
                continue
            risco = max(risco, self._score_termos(_normalizar_texto(decoded)))
            if risco >= 0.96:
                break
        return risco


class LLMRiskAssessor:
    """Independent LLM-based risk assessor that falls back to heuristic on failure."""

    def __init__(
        self,
        gateway: Any,
        role: str = "Root_Orchestrator",
        fallback_assessor: Optional[QlipotRiskAssessor] = None,
        version: str = "wave10-2026.07",
    ):
        self._gateway = gateway
        self._role = role
        self._fallback_assessor = fallback_assessor or HeuristicRiskAssessor(version=version)
        self._version = version
        self._resolved_identity: Optional[str] = None

    @property
    def identity(self) -> str:
        if self._resolved_identity:
            return self._resolved_identity
        return "llm-assessor-unresolved"

    @property
    def version(self) -> str:
        return self._version

    def assess_risk(self, ferramenta: str, argumentos: Dict[str, Any], pedido: str = "") -> float:
        try:
            # 1. Select provider from LLMGateway with risk-judge capability
            selection = self._gateway.select_provider(role=self._role, capability="risk-judge")
            provider = selection.provider
            profile = selection.profile
            self._resolved_identity = f"llm-{profile.name}:{profile.model}"

            # 2. Build the risk assessment prompt
            prompt = (
                "Você é um classificador de risco de segurança operacional para chamadas de ferramentas/MCP "
                "(Qlipot Risk Assessor).\n"
                "Analise o pedido do usuário, a ferramenta que está sendo chamada e seus argumentos. "
                "Classifique o risco de segurança em um score de 0.0 (sem risco operacional) a 1.0 "
                "(risco crítico, destrutivo ou exfiltração de segredos).\n\n"
                f"Pedido: {pedido}\n"
                f"Ferramenta: {ferramenta}\n"
                f"Argumentos: {argumentos}\n\n"
                "Retorne APENAS um JSON válido no formato abaixo, sem qualquer outro texto ou explicações:\n"
                "{\n"
                '  "score": <float entre 0.0 e 1.0>,\n'
                '  "reason": "<breve explicação de segurança>"\n'
                "}"
            )

            # 3. Request LLM evaluation
            # temperature=0 makes the risk classification deterministic and
            # auditable: the same (tool, args, request) yields the same score.
            request_body = {
                "model": profile.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
            }
            response = provider.execute_request(request_body)
            content = response.content.strip()

            # 4. Parse the risk score from response content
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
            else:
                data = json.loads(content)

            score = float(data["score"])
            return max(0.0, min(1.0, score))

        except Exception as exc:
            # Fall back silently and securely to heuristic assessor on any network/API/parse failure
            logger.warning(
                "Falha na avaliação de risco via LLM (%s). Usando fallback heurístico offline. Erro: %s",
                self.identity,
                exc,
            )
            fallback_identity = self._fallback_assessor.identity
            self._resolved_identity = f"fallback-{fallback_identity}"
            return self._fallback_assessor.assess_risk(ferramenta, argumentos, pedido)
