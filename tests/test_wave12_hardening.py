import os
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

from kabbalah.budget_manager import _entries_today
from kabbalah.contrato_store import ContratoStore, sanitize_key
from kabbalah.memory_subsystem import Knowledge, SQLiteVectorBackend
from kabbalah.qlipot import Qlipot
from kabbalah.tools.execution_engine import ToolExecutionEngine, ToolRequest, ToolType


def test_docker_sandbox_wrapping():
    engine = ToolExecutionEngine()
    os.environ["KABBALAH_USE_DOCKER_SANDBOX"] = "1"
    os.environ["KABBALAH_DOCKER_SANDBOX_IMAGE"] = "alpine:latest"

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="hello", stderr="")
        req = ToolRequest(tool_type=ToolType.BASH, command="echo 'hello'")
        engine.execute(req)

        # Verify it was wrapped into docker run
        args, kwargs = mock_run.call_args_list[1] # first call is docker --version
        cmd_list = args[0]
        assert "docker" in cmd_list
        assert "run" in cmd_list
        assert "alpine:latest" in cmd_list
        assert "echo 'hello'" in cmd_list
    os.environ["KABBALAH_USE_DOCKER_SANDBOX"] = "0"


def test_sqlite_vector_memory():
    import gc
    with tempfile.TemporaryDirectory() as tmpdir:
        backend = SQLiteVectorBackend(tmpdir)
        k1 = Knowledge(knowledge_id="k1", content="Python rules", category="dev")
        k2 = Knowledge(knowledge_id="k2", content="Golang is fast", category="dev")

        backend.store(k1)
        backend.store(k2)

        # Test query substring fallback
        results = backend.query("Python")
        assert len(results) == 1
        assert results[0].knowledge_id == "k1"

        del backend
        gc.collect()


def test_qlipot_persistence():
    import gc
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "state.db"
        store = ContratoStore(db_path)
        qlipot = Qlipot(store=store)

        # Apply a correction
        qlipot.aplicar_correcao("action_sig_123", 0.15, origem="sync_hub")

        # Instantiate a new Qlipot with same store to simulate restart
        qlipot2 = Qlipot(store=store)
        assert qlipot2._correcoes.get("action_sig_123") == 0.15

        del qlipot
        del qlipot2
        del store
        gc.collect()


def test_sanitize_key():
    assert sanitize_key("agente_id\nwith\rnewline") == "agente_id with newline"
    assert sanitize_key("agente_id\u200bwithzero") == "agente_idwithzero"


def test_utc_timezone_budget():
    # Verify that entries today uses UTC (gmtime)
    entry_today = {
        "cost": 1.0,
        "timestamp": time.time()
    }
    res = _entries_today([entry_today])
    assert len(res) == 1
