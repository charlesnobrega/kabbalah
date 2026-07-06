import json
from pathlib import Path

import pytest

from benchmarks.run import BenchmarkRunner, load_scenarios, write_reports

ROOT = Path(__file__).resolve().parents[1]


def test_default_benchmark_scenarios_are_unique_and_include_controls():
    scenarios = load_scenarios(ROOT / "benchmarks" / "scenarios")

    assert len({scenario.id for scenario in scenarios}) == len(scenarios)
    assert any(scenario.expected_blocked for scenario in scenarios)
    assert any(not scenario.expected_blocked for scenario in scenarios)


def test_benchmark_runner_measures_containment_without_false_positives():
    scenarios = load_scenarios(ROOT / "benchmarks" / "scenarios")

    report = BenchmarkRunner().run(scenarios)

    assert report["summary"]["total"] == len(scenarios)
    assert report["summary"]["correct_block_rate"] == 1.0
    assert report["summary"]["false_positive_rate"] == 0.0
    assert all(item["correct"] for item in report["scenarios"])


def test_benchmark_reports_are_datestamped_and_never_overwritten(tmp_path):
    report = BenchmarkRunner().run(load_scenarios(ROOT / "benchmarks" / "scenarios"))

    json_path, md_path = write_reports(report, tmp_path, "20260706T000000Z")

    assert json.loads(json_path.read_text(encoding="utf-8"))["summary"]["total"] == report["summary"]["total"]
    assert "Kabbalah-Bench Report" in md_path.read_text(encoding="utf-8")
    with pytest.raises(FileExistsError):
        write_reports(report, tmp_path, "20260706T000000Z")

