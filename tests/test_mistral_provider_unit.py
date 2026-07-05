"""Unit tests for Mistral provider parsing that do not call the live API."""

from kabbalah.providers.mistral_provider import MistralProvider


class _FakeMistralMessage:
    def __init__(self, content):
        self.content = content


class _FakeMistralChoice:
    def __init__(self, content):
        self.message = _FakeMistralMessage(content)


class _FakeMistralUsage:
    prompt_tokens = 5
    completion_tokens = 7


class _FakeMistralResponse:
    usage = _FakeMistralUsage()

    def __init__(self, content):
        self.choices = [_FakeMistralChoice(content)]


class _FakeMistralChat:
    def __init__(self, content):
        self._content = content

    def complete(self, **kwargs):
        return _FakeMistralResponse(self._content)


class _FakeMistralClient:
    def __init__(self, content):
        self.chat = _FakeMistralChat(content)


class _TextChunk:
    def __init__(self, text):
        self.text = text


def test_execute_request_extracts_list_content_from_current_mistral_shape():
    provider = MistralProvider(api_key="test-key")
    provider.client = _FakeMistralClient([_TextChunk("hello "), {"text": "world"}])

    response = provider.execute_request(
        {
            "model": "mistral-small",
            "messages": [{"role": "user", "content": "Say hello"}],
        }
    )

    assert response.error is None
    assert response.content == "hello world"
    assert response.tokens_used == 12
