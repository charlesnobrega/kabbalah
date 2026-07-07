"""Tests for OpenAI-compatible provider adapters."""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from kabbalah.providers.factory import ProviderFactory
from kabbalah.providers.openai_compatible_provider import OpenAICompatibleProvider


class _FakeOpenAIHandler(BaseHTTPRequestHandler):
    captured_headers = {}
    captured_payload = {}

    def do_POST(self):
        length = int(self.headers["Content-Length"])
        self.__class__.captured_headers = dict(self.headers)
        self.__class__.captured_payload = json.loads(self.rfile.read(length))

        body = {
            "model": self.__class__.captured_payload["model"],
            "choices": [
                {
                    "message": {
                        "content": "adapter response",
                    }
                }
            ],
            "usage": {
                "prompt_tokens": 11,
                "completion_tokens": 7,
                "total_tokens": 18,
            },
        }
        encoded = json.dumps(body).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format, *args):
        return


def _start_fake_server():
    server = HTTPServer(("127.0.0.1", 0), _FakeOpenAIHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f"http://127.0.0.1:{server.server_port}/v1"


def test_openai_compatible_provider_posts_chat_completion(monkeypatch):
    server, base_url = _start_fake_server()
    monkeypatch.setenv("FAKE_OPENAI_KEY", "test-key")
    try:
        provider = OpenAICompatibleProvider(
            base_url=base_url,
            api_key_env="FAKE_OPENAI_KEY",
            model="fake-model",
            input_cost_per_1m_tokens=1.0,
            output_cost_per_1m_tokens=2.0,
        )

        response = provider.execute_request(
            {
                "messages": [{"role": "user", "content": "hello"}],
                "temperature": 0.2,
                "max_tokens": 32,
            }
        )

        assert response.content == "adapter response"
        assert response.model == "fake-model"
        assert response.tokens_used == 18
        assert response.cost == 0.000025
        assert _FakeOpenAIHandler.captured_payload["model"] == "fake-model"
        assert _FakeOpenAIHandler.captured_headers["Authorization"] == "Bearer test-key"
    finally:
        server.shutdown()


def test_openai_compatible_provider_allows_keyless_local_endpoint():
    provider = OpenAICompatibleProvider(
        base_url="http://localhost:11434/v1",
        api_key_env=None,
        model="local-model",
    )

    assert provider.api_key is None
    assert provider.base_url == "http://localhost:11434/v1"


def test_provider_factory_registers_openai_compatible_entries(monkeypatch):
    factory = ProviderFactory()
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter")

    assert "ollama_local" in factory.get_available_providers()
    assert "openrouter" in factory.get_available_providers()
    assert "cerebras" in factory.get_available_providers()
    assert "sambanova" in factory.get_available_providers()

    openrouter = factory.create_provider("openrouter")
    ollama = factory.create_provider("ollama_local")

    assert isinstance(openrouter, OpenAICompatibleProvider)
    assert openrouter.api_key == "test-openrouter"
    assert openrouter.base_url == "https://openrouter.ai/api/v1"
    assert isinstance(ollama, OpenAICompatibleProvider)
    assert ollama.api_key is None
    assert ollama.base_url == "http://localhost:11434/v1"


def test_provider_factory_uses_current_openai_compatible_defaults():
    defaults = ProviderFactory.PROVIDER_DEFAULTS

    assert defaults["cerebras"]["base_url"] == "https://api.cerebras.ai/v1"
    assert defaults["cerebras"]["model"] == "gpt-oss-120b"
    assert defaults["sambanova"]["base_url"] == "https://api.sambanova.ai/v1"
    assert defaults["sambanova"]["model"] == "Meta-Llama-3.3-70B-Instruct"
