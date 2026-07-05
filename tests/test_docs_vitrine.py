"""Documentation-vitrine checks for Onda 8.7."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_readme_documents_product_quickstart_and_demo_assets() -> None:
    """README should show the product boundary and executable quickstart."""

    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "zero-trust governance kernel" in readme
    assert "Five-minute quickstart" in readme
    assert "py -3.11 -m venv .venv" in readme
    assert 'pip install -e ".[mcp,observability]"' in readme
    assert "KABBALAH_BRIDGE_STATE_DB" in readme
    assert "kabbalah.exe status --json" in readme
    assert "kabbalah-setup-demo.cast" in readme
    assert "compare_models" in readme
    assert "```mermaid" in readme


def test_architecture_has_post_wave_5_diagrams() -> None:
    """Architecture doc should contain updated gateway and profiler diagrams."""

    architecture = (ROOT / "docs" / "ARCHITECTURE.md").read_text(encoding="utf-8")

    assert "Security pipeline diagram" in architecture
    assert "Gateway, registry, and budget flow" in architecture
    assert "Hardware profiler flow" in architecture
    assert "LLMGateway" in architecture
    assert "CapabilityRegistry" in architecture
    assert "HardwareProfiler" in architecture
    assert architecture.count("```mermaid") >= 3


def test_asciinema_cast_is_present() -> None:
    """The README demo asset should exist as an asciinema v2 cast file."""

    cast = (ROOT / "docs" / "assets" / "kabbalah-setup-demo.cast").read_text(encoding="utf-8")

    assert '"version":2' in cast
    assert "kabbalah.exe --version" in cast
    assert "Secret value was not printed" in cast
