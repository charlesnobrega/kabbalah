"""Run Kabbalah containment benchmarks.

The harness measures the pre-execution security pipeline only:
Qlipot intent scoring -> FirewallMCP authorization -> HITL pending/denial.
Allowed scenarios are executed against the guarded test-only MockProvider so
the benchmark never invokes real tools, shell, network, or live providers.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from kabbalah.firewall_mcp import FirewallMCP, MCPRequest, permitir_tudo
from kabbalah.hitl import HITL
from kabbalah.providers.mock_provider import MockProvider
from kabbalah.qlipot import RISK_ASSESSOR_VERSION, Qlipot

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCENARIOS_DIR = ROOT / "benchmarks" / "scenarios"
DEFAULT_RESULTS_DIR = ROOT / "benchmarks" / "results"


@dataclass(frozen=True)
class BenchmarkScenario:
    """Declarative containment scenario."""

    id: str
    name: str
    category: str
    expected_blocked: bool
    tool: str
    request: str
    arguments: dict[str, Any]
    agent_id: str = "bench-agent"


def load_scenarios(path: Path) -> list[BenchmarkScenario]:
    """Load all JSON/YAML scenarios from a directory or one file."""

    files = (
        [path]
        if path.is_file()
        else sorted(path.glob("*.json")) + sorted(path.glob("*.yaml")) + sorted(path.glob("*.yml"))
    )
    scenarios: list[BenchmarkScenario] = []
    for file_path in files:
        data = _load_structured_file(file_path)
        raw_items = data.get("scenarios", data if isinstance(data, list) else [])
        for item in raw_items:
            scenarios.append(
                BenchmarkScenario(
                    id=str(item["id"]),
                    name=str(item.get("name", item["id"])),
                    category=str(item.get("category", "attack")),
                    expected_blocked=bool(item["expected_blocked"]),
                    tool=str(item["tool"]),
                    request=str(item["request"]),
                    arguments=dict(item.get("arguments", {})),
                    agent_id=str(item.get("agent_id", "bench-agent")),
                )
            )
    _validate_scenarios(scenarios)
    return scenarios


def load_corrections(path: Path | None) -> list[dict[str, Any]]:
    """Load optional Qlipot corrections for before/after benchmarks."""

    if path is None:
        return []
    data = _load_structured_file(path)
    return list(data.get("corrections", data if isinstance(data, list) else []))


class BenchmarkRunner:
    """Run scenarios through Kabbalah's security decision path."""

    def __init__(self, *, corrections: list[dict[str, Any]] | None = None) -> None:
        self.qlipot = Qlipot()
        self.hitl = HITL()
        self.firewall = FirewallMCP(
            rbac_checker=permitir_tudo,
            contract_checker=permitir_tudo,
            hitl=self.hitl,
        )
        self.corrections = corrections or []

    def run(self, scenarios: list[BenchmarkScenario]) -> dict[str, Any]:
        """Run scenarios and return a JSON-serializable report."""

        self._apply_corrections(scenarios)
        results = [self._run_one(scenario) for scenario in scenarios]
        expected_attacks = [item for item in results if item["expected_blocked"]]
        benign = [item for item in results if not item["expected_blocked"]]
        latencies = [float(item["latency_ms"]) for item in results]
        return {
            "metadata": {
                "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
                "git_commit": _git_commit(),
                "python": platform.python_version(),
                "platform": platform.platform(),
                "risk_assessor_version": RISK_ASSESSOR_VERSION,
            },
            "summary": {
                "total": len(results),
                "correct": sum(1 for item in results if item["correct"]),
                "correct_block_rate": _ratio(
                    sum(1 for item in expected_attacks if item["blocked"]),
                    len(expected_attacks),
                ),
                "false_positive_rate": _ratio(
                    sum(1 for item in benign if item["blocked"]),
                    len(benign),
                ),
                "avg_latency_ms": statistics.fmean(latencies) if latencies else 0.0,
                "p95_latency_ms": _p95(latencies),
                "decision_overhead_ms": sum(latencies),
            },
            "scenarios": results,
        }

    def _apply_corrections(self, scenarios: list[BenchmarkScenario]) -> None:
        by_id = {scenario.id: scenario for scenario in scenarios}
        for correction in self.corrections:
            signature = correction.get("signature")
            target_id = correction.get("target_scenario_id")
            if target_id:
                scenario = by_id[str(target_id)]
                signature = self.qlipot.assinar_acao(
                    ferramenta=scenario.tool,
                    argumentos=scenario.arguments,
                    pedido=scenario.request,
                )
            self.qlipot.aplicar_correcao(
                str(signature),
                float(correction["delta"]),
                origem=str(correction.get("origem", "sync_hub")),
            )

    def _run_one(self, scenario: BenchmarkScenario) -> dict[str, Any]:
        start = time.perf_counter()
        intent = self.qlipot.avaliar_intencao(
            pedido=scenario.request,
            ferramenta=scenario.tool,
            argumentos=scenario.arguments,
            agente_id=scenario.agent_id,
        )
        stage = "qlipot"
        blocked = bool(intent.bloqueado)
        decision = None
        provider_error = None

        if not blocked:
            request = MCPRequest(
                agente_id=scenario.agent_id,
                ferramenta=scenario.tool,
                argumentos=scenario.arguments,
                contrato_id=f"bench:{scenario.id}",
                trace_id=f"bench:{scenario.id}",
                metadata={
                    "risco": intent.risco,
                    "score_confianca": intent.score_confianca,
                    "benchmark": True,
                },
            )
            decision = self.firewall.autorizar(request)
            blocked = not decision.autorizado
            stage = "hitl" if decision.hitl_required else "firewall"

        if not blocked:
            provider_error = self._execute_mock_provider(scenario)

        latency_ms = (time.perf_counter() - start) * 1000
        return {
            "id": scenario.id,
            "name": scenario.name,
            "category": scenario.category,
            "tool": scenario.tool,
            "expected_blocked": scenario.expected_blocked,
            "blocked": blocked,
            "correct": blocked == scenario.expected_blocked,
            "stage": stage,
            "risk": round(float(intent.risco), 4),
            "score_confianca": intent.score_confianca,
            "reason": decision.motivo if decision is not None else intent.motivo,
            "hitl_required": bool(decision and decision.hitl_required),
            "provider_error": provider_error,
            "latency_ms": round(latency_ms, 4),
        }

    @staticmethod
    def _execute_mock_provider(scenario: BenchmarkScenario) -> str | None:
        previous = os.environ.get("KABBALAH_ALLOW_TEST_FAKE_PROVIDER")
        os.environ["KABBALAH_ALLOW_TEST_FAKE_PROVIDER"] = "1"
        try:
            provider = MockProvider(response_content=f"bench-ok:{scenario.id}", latency_ms=0)
            response = provider.execute_request(
                {
                    "model": "mock-model-1",
                    "messages": [{"role": "user", "content": scenario.request}],
                    "max_tokens": 16,
                }
            )
            return response.error
        finally:
            if previous is None:
                os.environ.pop("KABBALAH_ALLOW_TEST_FAKE_PROVIDER", None)
            else:
                os.environ["KABBALAH_ALLOW_TEST_FAKE_PROVIDER"] = previous


def write_reports(report: dict[str, Any], results_dir: Path, timestamp: str | None = None) -> tuple[Path, Path]:
    """Write datestamped JSON and Markdown reports without overwriting."""

    results_dir.mkdir(parents=True, exist_ok=True)
    stamp = timestamp or datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    json_path = results_dir / f"{stamp}-kabbalah-bench.json"
    md_path = results_dir / f"{stamp}-kabbalah-bench.md"
    if json_path.exists() or md_path.exists():
        raise FileExistsError(f"Benchmark report already exists for timestamp {stamp}")
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    return json_path, md_path


def render_markdown(report: dict[str, Any]) -> str:
    """Render a compact Markdown benchmark report."""

    summary = report["summary"]
    lines = [
        "# Kabbalah-Bench Report",
        "",
        f"- Generated: {report['metadata']['generated_at']}",
        f"- Commit: `{report['metadata']['git_commit']}`",
        f"- Risk assessor: `{report['metadata']['risk_assessor_version']}`",
        f"- Correct: {summary['correct']}/{summary['total']}",
        f"- Correct block rate: {summary['correct_block_rate']:.2%}",
        f"- False-positive rate: {summary['false_positive_rate']:.2%}",
        f"- Average latency: {summary['avg_latency_ms']:.2f} ms",
        f"- p95 latency: {summary['p95_latency_ms']:.2f} ms",
        "",
        "| Scenario | Expected blocked | Blocked | Correct | Stage | Risk |",
        "|---|---:|---:|---:|---|---:|",
    ]
    for item in report["scenarios"]:
        lines.append(
            "| {id} | {expected} | {blocked} | {correct} | {stage} | {risk:.4f} |".format(
                id=item["id"],
                expected=str(item["expected_blocked"]).lower(),
                blocked=str(item["blocked"]).lower(),
                correct=str(item["correct"]).lower(),
                stage=item["stage"],
                risk=float(item["risk"]),
            )
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for ``python -m benchmarks.run``."""

    parser = argparse.ArgumentParser(description="Run Kabbalah containment benchmarks")
    parser.add_argument("--scenarios", type=Path, default=DEFAULT_SCENARIOS_DIR)
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS_DIR)
    parser.add_argument("--timestamp", help="Override report timestamp, useful for reproducible baselines")
    parser.add_argument("--corrections", type=Path, help="Optional JSON/YAML qlipot correction file")
    parser.add_argument("--no-write", action="store_true", help="Print JSON to stdout instead of writing reports")
    args = parser.parse_args(argv)

    report = BenchmarkRunner(corrections=load_corrections(args.corrections)).run(load_scenarios(args.scenarios))
    if args.no_write:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    json_path, md_path = write_reports(report, args.results_dir, args.timestamp)
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    return 0


def _load_structured_file(path: Path) -> Any:
    if path.suffix == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    if path.suffix in {".yaml", ".yml"}:
        import yaml

        return yaml.safe_load(path.read_text(encoding="utf-8"))
    raise ValueError(f"Unsupported scenario file: {path}")


def _validate_scenarios(scenarios: list[BenchmarkScenario]) -> None:
    if not scenarios:
        raise ValueError("No benchmark scenarios found")
    ids = [scenario.id for scenario in scenarios]
    duplicates = sorted({scenario_id for scenario_id in ids if ids.count(scenario_id) > 1})
    if duplicates:
        raise ValueError(f"Duplicate benchmark scenario ids: {duplicates}")


def _ratio(numerator: int, denominator: int) -> float:
    return float(numerator) / denominator if denominator else 0.0


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(round((len(ordered) - 1) * 0.95)))
    return ordered[index]


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return "unknown"


if __name__ == "__main__":
    raise SystemExit(main())
