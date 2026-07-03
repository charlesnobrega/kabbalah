import pytest

from src.kabbalah.tools.execution_engine import (
    ToolExecutionEngine,
    ToolRequest,
    ToolType,
)


def test_path_allowed_rejects_prefix_bypass(tmp_path):
    allowed = tmp_path / "allowed"
    evil = tmp_path / "allowed-evil"
    allowed.mkdir()
    evil.mkdir()
    engine = ToolExecutionEngine(allowed_paths=[str(allowed)])

    assert engine._is_path_allowed(str(evil / "file.txt")) is False


def test_path_allowed_rejects_symlink_escape(tmp_path):
    allowed = tmp_path / "allowed"
    outside = tmp_path / "outside"
    allowed.mkdir()
    outside.mkdir()
    target = outside / "secret.txt"
    target.write_text("secret", encoding="utf-8")
    link = allowed / "link.txt"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("symlinks unavailable on this platform")

    engine = ToolExecutionEngine(allowed_paths=[str(allowed)])

    assert engine._is_path_allowed(str(link)) is False


def test_domain_allowed_rejects_suffix_confusion(monkeypatch):
    monkeypatch.setattr(
        "src.kabbalah.tools.execution_engine.socket.getaddrinfo",
        lambda *args, **kwargs: [(None, None, None, None, ("93.184.216.34", 443))],
    )
    engine = ToolExecutionEngine(allowed_domains=["example.com"])

    assert engine._is_domain_allowed("https://evilexample.com") is False
    assert engine._is_domain_allowed("https://sub.example.com") is True


def test_domain_allowed_blocks_loopback_even_with_wildcard():
    engine = ToolExecutionEngine(allowed_domains=["*"])

    assert engine._is_domain_allowed("http://127.0.0.1:8080") is False
    assert engine._is_domain_allowed("ftp://example.com") is False


def test_grep_pattern_does_not_execute_shell_injection(tmp_path):
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    (allowed / "file.txt").write_text("hello\n", encoding="utf-8")
    canary = tmp_path / "pwned.txt"
    engine = ToolExecutionEngine(allowed_paths=[str(allowed)])

    response = engine.execute(
        ToolRequest(
            tool_type=ToolType.GREP,
            command="grep",
            args={"pattern": f"hello'; echo pwned > {canary}; echo '", "path": str(allowed)},
        )
    )

    assert response.success is True
    assert not canary.exists()


def test_bash_kill_switch_denies_execute_and_stream():
    engine = ToolExecutionEngine(enable_bash=False)
    request = ToolRequest(tool_type=ToolType.BASH, command="echo blocked")

    response = engine.execute(request)
    streamed = list(engine.stream(request))

    assert response.success is False
    assert "disabled" in response.error.lower()
    assert streamed[0].success is False
    assert "disabled" in streamed[0].error.lower()
