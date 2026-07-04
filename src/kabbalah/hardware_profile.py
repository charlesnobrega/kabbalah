"""Local hardware profiling for model fit decisions."""

from __future__ import annotations

import ctypes
import hashlib
import json
import os
import platform
import shutil
import sqlite3
import subprocess
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Optional, Protocol, Sequence

from kabbalah.llm_gateway import ModelProfile

try:
    import psutil
except ImportError:
    psutil = None


class CapabilityRegistryProtocol(Protocol):
    """Registry interface consumed by the hardware profiler."""

    def list_profiles(self) -> list[ModelProfile]:
        """Return model profiles available for classification."""


@dataclass(frozen=True)
class GPUInfo:
    """Detected GPU metadata relevant to model placement."""

    model: str
    vendor: str
    vram_total_mb: int
    backend: str


@dataclass(frozen=True)
class CPUInfo:
    """Detected CPU/RAM metadata relevant to local fallback."""

    model: str
    cores: int
    ram_total_mb: int
    flags: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class HardwareProfile:
    """Persisted hardware snapshot and model fit classification."""

    fingerprint: str
    backend: str
    gpus: list[GPUInfo]
    cpu: CPUInfo
    ram_total_mb: int
    model_fits: dict[str, str]
    model_tiers: dict[str, str]
    created_at: float


GPUProbe = Callable[[], Sequence[GPUInfo]]
CPUProbe = Callable[[], CPUInfo]


class HardwareProfiler:
    """Detect host hardware and persist append-only hardware snapshots."""

    def __init__(
        self,
        db_path: str | Path | None = None,
        *,
        gpu_probe: Optional[GPUProbe] = None,
        cpu_probe: Optional[CPUProbe] = None,
    ):
        state_db_path = (
            db_path
            or os.getenv("KABBALAH_HARDWARE_PROFILE_DB")
            or os.getenv("KABBALAH_BRIDGE_STATE_DB")
            or ".kabbalah_bridge_state.sqlite3"
        )
        self.db_path = Path(state_db_path).expanduser()
        if not self.db_path.is_absolute():
            self.db_path = self.db_path.resolve()
        self._gpu_probe = gpu_probe or self._default_probe_gpus
        self._cpu_probe = cpu_probe or self._default_probe_cpu
        self._lock = threading.RLock()
        self._ensure_schema()

    def profile(self, registry: CapabilityRegistryProtocol) -> HardwareProfile:
        """Return the current profile, appending only when hardware changes."""
        gpus = list(self._gpu_probe())
        cpu = self._cpu_probe()
        fingerprint = self._fingerprint(gpus=gpus, cpu=cpu)

        with self._lock:
            latest = self._latest_profile()
            if latest and latest.fingerprint == fingerprint:
                return latest

            profile = HardwareProfile(
                fingerprint=fingerprint,
                backend=self._select_backend(gpus),
                gpus=gpus,
                cpu=cpu,
                ram_total_mb=cpu.ram_total_mb,
                model_fits=self._classify_model_fits(registry.list_profiles(), gpus),
                model_tiers=self._classify_model_tiers(registry.list_profiles(), gpus),
                created_at=time.time(),
            )
            self._insert_profile(profile)
            return profile

    def list_profiles(self) -> list[HardwareProfile]:
        """Return persisted hardware snapshots in insertion order."""
        with self._lock:
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT profile_json FROM hardware_profiles ORDER BY seq ASC"
                ).fetchall()
        return [self._deserialize_profile(row[0]) for row in rows]

    def _ensure_schema(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS hardware_profiles (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    fingerprint TEXT NOT NULL,
                    profile_json TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def _latest_profile(self) -> Optional[HardwareProfile]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT profile_json FROM hardware_profiles ORDER BY seq DESC LIMIT 1"
            ).fetchone()
        if row is None:
            return None
        return self._deserialize_profile(row[0])

    def _insert_profile(self, profile: HardwareProfile) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO hardware_profiles (fingerprint, profile_json, created_at)
                VALUES (?, ?, ?)
                """,
                (
                    profile.fingerprint,
                    self._serialize_profile(profile),
                    profile.created_at,
                ),
            )

    @staticmethod
    def _select_backend(gpus: Sequence[GPUInfo]) -> str:
        if not gpus:
            return "cpu"
        return gpus[0].backend or "gpu"

    @staticmethod
    def _classify_model_fits(
        profiles: Iterable[ModelProfile],
        gpus: Sequence[GPUInfo],
    ) -> dict[str, str]:
        max_vram = max((gpu.vram_total_mb for gpu in gpus), default=0)
        model_fits: dict[str, str] = {}

        for profile in profiles:
            if profile.location != "local":
                continue

            if profile.min_vram_full is None and profile.min_vram_offload is None:
                model_fits[profile.name] = "cpu"
            elif profile.min_vram_full is not None and max_vram >= profile.min_vram_full:
                model_fits[profile.name] = "full"
            elif (
                profile.min_vram_offload is not None
                and max_vram >= profile.min_vram_offload
            ):
                model_fits[profile.name] = "offload"
            else:
                model_fits[profile.name] = "unavailable"

        # TODO(onda-7): enforce live VRAM pressure before dispatching a local model.
        return model_fits

    @classmethod
    def _classify_model_tiers(
        cls,
        profiles: Iterable[ModelProfile],
        gpus: Sequence[GPUInfo],
    ) -> dict[str, str]:
        model_fits = cls._classify_model_fits(profiles, gpus)
        model_tiers: dict[str, str] = {}

        for profile in profiles:
            if profile.location != "local":
                continue

            fit = model_fits.get(profile.name, "unavailable")
            if fit == "unavailable" or profile.tokens_s_medido is None:
                model_tiers[profile.name] = "indisponivel"
            elif profile.tokens_s_medido >= 12.0:
                model_tiers[profile.name] = "interativo"
            elif profile.tokens_s_medido > 0:
                model_tiers[profile.name] = "batch"
            else:
                model_tiers[profile.name] = "indisponivel"

        return model_tiers

    @staticmethod
    def _fingerprint(*, gpus: Sequence[GPUInfo], cpu: CPUInfo) -> str:
        payload = {
            "cpu": asdict(cpu),
            "gpus": [asdict(gpu) for gpu in sorted(gpus, key=lambda item: item.model)],
            "ram_total_mb": cpu.ram_total_mb,
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _serialize_profile(profile: HardwareProfile) -> str:
        return json.dumps(asdict(profile), sort_keys=True, separators=(",", ":"))

    @staticmethod
    def _deserialize_profile(payload: str) -> HardwareProfile:
        data = json.loads(payload)
        return HardwareProfile(
            fingerprint=data["fingerprint"],
            backend=data["backend"],
            gpus=[GPUInfo(**gpu) for gpu in data["gpus"]],
            cpu=CPUInfo(
                model=data["cpu"]["model"],
                cores=data["cpu"]["cores"],
                ram_total_mb=data["cpu"]["ram_total_mb"],
                flags=tuple(data["cpu"].get("flags", ())),
            ),
            ram_total_mb=data["ram_total_mb"],
            model_fits=dict(data["model_fits"]),
            model_tiers=dict(data.get("model_tiers", {})),
            created_at=data["created_at"],
        )

    @staticmethod
    def _default_probe_cpu() -> CPUInfo:
        model = platform.processor() or platform.machine() or "unknown-cpu"
        return CPUInfo(
            model=model,
            cores=_detect_cpu_cores(),
            ram_total_mb=_detect_total_ram_mb(),
            flags=_detect_cpu_flags(),
        )

    @staticmethod
    def _default_probe_gpus() -> list[GPUInfo]:
        gpus = _probe_vendor_gpus()
        if gpus:
            return gpus
        gpus = _probe_nvidia_smi()
        if gpus:
            return gpus
        return _probe_windows_video_controllers()


def _detect_cpu_cores() -> int:
    if psutil is not None:
        cores = psutil.cpu_count(logical=True)
        if cores:
            return int(cores)
    return os.cpu_count() or 1


def _detect_total_ram_mb() -> int:
    if psutil is not None:
        try:
            return int(psutil.virtual_memory().total // (1024 * 1024))
        except Exception:
            pass

    if platform.system().lower() == "windows":
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        status = MEMORYSTATUSEX()
        status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return int(status.ullTotalPhys // (1024 * 1024))

    if hasattr(os, "sysconf"):
        try:
            pages = os.sysconf("SC_PHYS_PAGES")
            page_size = os.sysconf("SC_PAGE_SIZE")
            return int((pages * page_size) // (1024 * 1024))
        except (OSError, ValueError):
            pass
    return 0


def _detect_cpu_flags() -> tuple[str, ...]:
    flags: set[str] = set()
    cpuinfo_path = Path("/proc/cpuinfo")
    if cpuinfo_path.exists():
        try:
            text = cpuinfo_path.read_text(encoding="utf-8", errors="ignore").lower()
            for flag in ("avx", "avx2", "avx512", "fma", "sse4_2"):
                if flag in text:
                    flags.add(flag)
        except OSError:
            pass

    processor = (platform.processor() or "").lower()
    for flag in ("avx", "avx2", "avx512", "fma", "sse4_2"):
        if flag in processor:
            flags.add(flag)
    return tuple(sorted(flags))


def _probe_vendor_gpus() -> list[GPUInfo]:
    """Probe vendor-specific APIs first; callers must tolerate empty results."""
    gpus: list[GPUInfo] = []
    gpus.extend(_probe_nvml())
    gpus.extend(_probe_amdsmi())
    gpus.extend(_probe_level_zero())
    return gpus


def _probe_nvml() -> list[GPUInfo]:
    try:
        import pynvml
    except ImportError:
        return []

    try:
        pynvml.nvmlInit()
        count = pynvml.nvmlDeviceGetCount()
        gpus: list[GPUInfo] = []
        for index in range(count):
            handle = pynvml.nvmlDeviceGetHandleByIndex(index)
            raw_name = pynvml.nvmlDeviceGetName(handle)
            model = raw_name.decode("utf-8") if isinstance(raw_name, bytes) else str(raw_name)
            memory = pynvml.nvmlDeviceGetMemoryInfo(handle)
            gpus.append(
                GPUInfo(
                    model=model,
                    vendor="nvidia",
                    vram_total_mb=int(memory.total // (1024 * 1024)),
                    backend="cuda",
                )
            )
        return gpus
    except Exception:
        return []
    finally:
        try:
            pynvml.nvmlShutdown()
        except Exception:
            pass


def _probe_amdsmi() -> list[GPUInfo]:
    try:
        import amdsmi
    except ImportError:
        return []

    try:
        amdsmi.amdsmi_init()
        handles = amdsmi.amdsmi_get_processor_handles()
        gpus: list[GPUInfo] = []
        for handle in handles:
            model = _amdsmi_model(handle, amdsmi)
            vram_total_mb = _amdsmi_vram_total_mb(handle, amdsmi)
            if model and vram_total_mb > 0:
                gpus.append(
                    GPUInfo(
                        model=model,
                        vendor="amd",
                        vram_total_mb=vram_total_mb,
                        backend="rocm",
                    )
                )
        return gpus
    except Exception:
        return []
    finally:
        try:
            amdsmi.amdsmi_shut_down()
        except Exception:
            pass


def _amdsmi_model(handle: object, amdsmi_module: object) -> str:
    for method_name in ("amdsmi_get_gpu_asic_info", "amdsmi_get_gpu_board_info"):
        method = getattr(amdsmi_module, method_name, None)
        if method is None:
            continue
        try:
            info = method(handle)
        except Exception:
            continue
        if isinstance(info, dict):
            for key in ("market_name", "product_name", "name", "model"):
                value = info.get(key)
                if value:
                    return str(value)
    return "AMD GPU"


def _amdsmi_vram_total_mb(handle: object, amdsmi_module: object) -> int:
    memory_type = getattr(getattr(amdsmi_module, "AmdSmiMemoryType", object), "VRAM", None)
    method = getattr(amdsmi_module, "amdsmi_get_gpu_memory_total", None)
    if method is None:
        return 0
    try:
        if memory_type is None:
            total_bytes = method(handle)
        else:
            total_bytes = method(handle, memory_type)
        return int(total_bytes // (1024 * 1024))
    except Exception:
        return 0


def _probe_level_zero() -> list[GPUInfo]:
    executable = shutil.which("zeinfo")
    if executable is None:
        return []

    try:
        result = subprocess.run(
            [executable],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []

    if result.returncode != 0:
        return []

    gpus: list[GPUInfo] = []
    current_model: Optional[str] = None
    current_vram_mb = 0
    for raw_line in result.stdout.splitlines():
        line = raw_line.strip()
        lower = line.lower()
        if "device name" in lower:
            if current_model and current_vram_mb > 0:
                gpus.append(
                    GPUInfo(
                        model=current_model,
                        vendor=_infer_vendor(current_model),
                        vram_total_mb=current_vram_mb,
                        backend="level-zero",
                    )
                )
            current_model = line.split(":", 1)[-1].strip() or "Level Zero GPU"
            current_vram_mb = 0
        elif "global memory size" in lower or "total memory" in lower:
            current_vram_mb = _parse_memory_mb(line)

    if current_model and current_vram_mb > 0:
        gpus.append(
            GPUInfo(
                model=current_model,
                vendor=_infer_vendor(current_model),
                vram_total_mb=current_vram_mb,
                backend="level-zero",
            )
        )
    return gpus


def _parse_memory_mb(line: str) -> int:
    digits = "".join(character for character in line if character.isdigit())
    if not digits:
        return 0
    value = int(digits)
    lowered = line.lower()
    if "gib" in lowered or "gb" in lowered:
        return value * 1024
    if "kib" in lowered or "kb" in lowered:
        return value // 1024
    if "mib" in lowered or "mb" in lowered:
        return value
    return value // (1024 * 1024)


def _probe_nvidia_smi() -> list[GPUInfo]:
    executable = shutil.which("nvidia-smi")
    if executable is None:
        return []
    try:
        result = subprocess.run(
            [
                executable,
                "--query-gpu=name,memory.total",
                "--format=csv,noheader,nounits",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []

    if result.returncode != 0:
        return []

    gpus: list[GPUInfo] = []
    for line in result.stdout.splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) != 2:
            continue
        try:
            vram_total_mb = int(parts[1])
        except ValueError:
            continue
        gpus.append(
            GPUInfo(
                model=parts[0],
                vendor="nvidia",
                vram_total_mb=vram_total_mb,
                backend="cuda",
            )
        )
    return gpus


def _probe_windows_video_controllers() -> list[GPUInfo]:
    if platform.system().lower() != "windows":
        return []

    powershell = shutil.which("powershell") or shutil.which("pwsh")
    if powershell is None:
        return []

    try:
        result = subprocess.run(
            [
                powershell,
                "-NoProfile",
                "-Command",
                (
                    "Get-CimInstance Win32_VideoController | "
                    "Select-Object Name,AdapterRAM | ConvertTo-Json -Compress"
                ),
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []

    if result.returncode != 0 or not result.stdout.strip():
        return []

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []

    controllers = payload if isinstance(payload, list) else [payload]
    gpus: list[GPUInfo] = []
    for controller in controllers:
        if not isinstance(controller, dict):
            continue
        name = str(controller.get("Name") or "").strip()
        if not name:
            continue
        raw_ram = controller.get("AdapterRAM") or 0
        try:
            vram_total_mb = int(raw_ram) // (1024 * 1024)
        except (TypeError, ValueError):
            vram_total_mb = 0
        if vram_total_mb <= 0:
            continue
        vendor = _infer_vendor(name)
        gpus.append(
            GPUInfo(
                model=name,
                vendor=vendor,
                vram_total_mb=vram_total_mb,
                backend=_infer_backend(vendor),
            )
        )
    return gpus


def _infer_vendor(name: str) -> str:
    lowered = name.lower()
    if "nvidia" in lowered or "geforce" in lowered or "quadro" in lowered:
        return "nvidia"
    if "amd" in lowered or "radeon" in lowered:
        return "amd"
    if "intel" in lowered:
        return "intel"
    return "unknown"


def _infer_backend(vendor: str) -> str:
    if vendor == "nvidia":
        return "cuda"
    if vendor == "amd":
        return "rocm"
    if vendor == "intel":
        return "openvino"
    return "gpu"
