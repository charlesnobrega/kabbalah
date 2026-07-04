"""Tests for local hardware profiling and model fit classification."""

import kabbalah.hardware_profile as hardware_profile
from kabbalah.hardware_profile import CPUInfo, GPUInfo, HardwareProfiler
from kabbalah.llm_gateway import CapabilityRegistry, ModelProfile


def _local_profile(
    name: str,
    *,
    min_vram_full: int | None = None,
    min_vram_offload: int | None = None,
    tokens_s_medido: float | None = None,
) -> ModelProfile:
    return ModelProfile(
        name=name,
        provider_name="ollama_local",
        model=name,
        roles={"Leaf_Builder"},
        capabilities={"chat", "code"},
        context_window=8192,
        input_cost_per_1m_tokens=0.0,
        output_cost_per_1m_tokens=0.0,
        license_type="open",
        location="local",
        tier="local",
        min_vram_full=min_vram_full,
        min_vram_offload=min_vram_offload,
        tokens_s_medido=tokens_s_medido,
    )


def test_profiler_records_cpu_only_profile_and_cpu_model_fit(tmp_path):
    registry = CapabilityRegistry([_local_profile("cpu-friendly")])
    profiler = HardwareProfiler(
        tmp_path / "hardware.sqlite3",
        gpu_probe=lambda: [],
        cpu_probe=lambda: CPUInfo(model="ci-cpu", cores=4, ram_total_mb=16384),
    )

    profile = profiler.profile(registry)

    assert profile.backend == "cpu"
    assert profile.gpus == []
    assert profile.cpu.model == "ci-cpu"
    assert profile.ram_total_mb == 16384
    assert profile.fingerprint
    assert profile.model_fits == {"cpu-friendly": "cpu"}
    assert len(profiler.list_profiles()) == 1


def test_profiler_uses_bridge_state_db_by_default(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("KABBALAH_HARDWARE_PROFILE_DB", raising=False)
    monkeypatch.delenv("KABBALAH_BRIDGE_STATE_DB", raising=False)

    profiler = HardwareProfiler(
        gpu_probe=lambda: [],
        cpu_probe=lambda: CPUInfo(model="ci-cpu", cores=4, ram_total_mb=16384),
    )

    assert profiler.db_path == tmp_path / ".kabbalah_bridge_state.sqlite3"


def test_profiler_honors_bridge_state_db_env(monkeypatch, tmp_path):
    state_db = tmp_path / "state.sqlite3"
    monkeypatch.setenv("KABBALAH_BRIDGE_STATE_DB", str(state_db))
    monkeypatch.delenv("KABBALAH_HARDWARE_PROFILE_DB", raising=False)

    profiler = HardwareProfiler(
        gpu_probe=lambda: [],
        cpu_probe=lambda: CPUInfo(model="ci-cpu", cores=4, ram_total_mb=16384),
    )

    assert profiler.db_path == state_db


def test_profiler_reuses_cached_profile_when_fingerprint_is_unchanged(tmp_path):
    registry = CapabilityRegistry([_local_profile("cpu-friendly")])
    profiler = HardwareProfiler(
        tmp_path / "hardware.sqlite3",
        gpu_probe=lambda: [],
        cpu_probe=lambda: CPUInfo(model="ci-cpu", cores=4, ram_total_mb=16384),
    )

    first = profiler.profile(registry)
    second = profiler.profile(registry)

    assert second.fingerprint == first.fingerprint
    assert second.created_at == first.created_at
    assert len(profiler.list_profiles()) == 1


def test_profiler_appends_new_profile_when_hardware_changes(tmp_path):
    registry = CapabilityRegistry(
        [
            _local_profile("small-local", min_vram_full=4096),
            _local_profile("large-local", min_vram_full=8192, min_vram_offload=4096),
        ]
    )
    current_gpus = {
        "value": [GPUInfo(model="Small GPU", vendor="nvidia", vram_total_mb=4096, backend="cuda")]
    }
    profiler = HardwareProfiler(
        tmp_path / "hardware.sqlite3",
        gpu_probe=lambda: current_gpus["value"],
        cpu_probe=lambda: CPUInfo(model="ci-cpu", cores=8, ram_total_mb=32768),
    )

    first = profiler.profile(registry)
    current_gpus["value"] = [
        GPUInfo(model="Large GPU", vendor="nvidia", vram_total_mb=12288, backend="cuda")
    ]
    second = profiler.profile(registry)

    assert first.fingerprint != second.fingerprint
    assert first.backend == "cuda"
    assert first.model_fits == {"small-local": "full", "large-local": "offload"}
    assert second.model_fits == {"small-local": "full", "large-local": "full"}
    assert len(profiler.list_profiles()) == 2


def test_default_gpu_probe_prefers_vendor_api_before_fallbacks(monkeypatch):
    vendor_gpu = GPUInfo(
        model="Vendor GPU",
        vendor="nvidia",
        vram_total_mb=6144,
        backend="cuda",
    )
    calls = []

    monkeypatch.setattr(
        hardware_profile,
        "_probe_vendor_gpus",
        lambda: calls.append("vendor") or [vendor_gpu],
    )
    monkeypatch.setattr(
        hardware_profile,
        "_probe_nvidia_smi",
        lambda: calls.append("nvidia-smi") or [],
    )
    monkeypatch.setattr(
        hardware_profile,
        "_probe_windows_video_controllers",
        lambda: calls.append("wmi") or [],
    )

    assert HardwareProfiler._default_probe_gpus() == [vendor_gpu]
    assert calls == ["vendor"]


def test_vendor_gpu_probe_aggregates_nvml_amdsmi_and_level_zero(monkeypatch):
    nvml_gpu = GPUInfo(model="NVIDIA", vendor="nvidia", vram_total_mb=6144, backend="cuda")
    amd_gpu = GPUInfo(model="AMD", vendor="amd", vram_total_mb=4096, backend="rocm")
    intel_gpu = GPUInfo(model="Intel", vendor="intel", vram_total_mb=2048, backend="level-zero")

    monkeypatch.setattr(hardware_profile, "_probe_nvml", lambda: [nvml_gpu])
    monkeypatch.setattr(hardware_profile, "_probe_amdsmi", lambda: [amd_gpu])
    monkeypatch.setattr(hardware_profile, "_probe_level_zero", lambda: [intel_gpu])

    assert hardware_profile._probe_vendor_gpus() == [nvml_gpu, amd_gpu, intel_gpu]


def test_profiler_derives_runtime_tiers_from_measured_tokens_per_second(tmp_path):
    registry = CapabilityRegistry(
        [
            _local_profile("interactive-model", tokens_s_medido=16.0),
            _local_profile("batch-model", tokens_s_medido=4.0),
            _local_profile("unavailable-model", min_vram_full=4096, tokens_s_medido=20.0),
        ]
    )
    profiler = HardwareProfiler(
        tmp_path / "hardware.sqlite3",
        gpu_probe=lambda: [],
        cpu_probe=lambda: CPUInfo(model="ci-cpu", cores=4, ram_total_mb=16384),
    )

    profile = profiler.profile(registry)

    assert profile.model_tiers == {
        "interactive-model": "interativo",
        "batch-model": "batch",
        "unavailable-model": "indisponivel",
    }
