"""Interactive setup and provider key validation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable

from .configuration_manager import ConfigurationManager
from .providers.factory import ProviderFactory


@dataclass(frozen=True)
class ProviderValidationResult:
    """Result of validating one provider credential."""

    provider: str
    valid: bool
    message: str


class ProviderKeyValidator:
    """Validate provider credentials with a minimal live request."""

    def __init__(self, *, factory: ProviderFactory | None = None, timeout: float = 20.0):
        self.factory = factory or ProviderFactory()
        self.timeout = timeout

    def validate(self, provider: str, api_key: str) -> ProviderValidationResult:
        """Validate a provider key by executing a tiny chat request."""
        try:
            provider_instance = self.factory.create_provider(provider, api_key=api_key)
            response = provider_instance.execute_request(
                {
                    "messages": [{"role": "user", "content": "Reply with OK."}],
                    "max_tokens": 4,
                    "temperature": 0,
                },
                timeout=self.timeout,
            )
        except Exception as exc:
            return ProviderValidationResult(provider=provider, valid=False, message=str(exc))
        if response.error:
            return ProviderValidationResult(provider=provider, valid=False, message=response.error)
        return ProviderValidationResult(provider=provider, valid=True, message="validated")


def run_setup_wizard(
    *,
    config_manager: ConfigurationManager,
    validator: Any,
    provider_names: Iterable[str],
    input_func: Callable[[str], str],
    secret_input_func: Callable[[str], str],
    output_func: Callable[[str], None],
) -> dict[str, Any]:
    """Run the interactive provider setup wizard.

    Secrets are accepted only through ``secret_input_func`` and never echoed.
    Keys are stored only after validation succeeds.
    """
    providers = list(provider_names)
    output_func("Kabbalah setup")
    output_func("Available providers:")
    for provider in providers:
        output_func(f"- {provider}")

    selected_text = input_func("Providers to activate (comma separated, or 'all'): ").strip()
    selected = providers if selected_text.lower() == "all" else _parse_selected_providers(selected_text)
    results: list[dict[str, Any]] = []

    for provider in selected:
        if provider not in providers:
            results.append(
                {
                    "provider": provider,
                    "valid": False,
                    "stored": False,
                    "message": "unknown provider",
                }
            )
            output_func(f"[ERROR] {provider}: unknown provider")
            continue

        api_key = secret_input_func(f"{provider} API key: ")
        validation = validator.validate(provider, api_key)
        if validation.valid:
            config_manager.set_provider_api_key(provider, api_key, storage="keyring")
            status = config_manager.get_provider_key_status(provider)
            results.append(
                {
                    "provider": provider,
                    "valid": True,
                    "stored": True,
                    "source": status["source"],
                    "last4": status["last4"],
                    "message": validation.message,
                }
            )
            output_func(f"[OK] {provider}: key validated and stored (last4={status['last4']})")
        else:
            results.append(
                {
                    "provider": provider,
                    "valid": False,
                    "stored": False,
                    "message": validation.message,
                }
            )
            output_func(f"[ERROR] {provider}: validation failed — {validation.message}")

    return {
        "ok": all(result["valid"] and result["stored"] for result in results) if results else False,
        "providers": results,
    }


def _parse_selected_providers(selected_text: str) -> list[str]:
    return [item.strip() for item in selected_text.split(",") if item.strip()]
