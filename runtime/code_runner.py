"""
Safe local code execution for MAE agents.

The agent writes a script → Harness saves it to a temp file → runs it with
subprocess → returns stdout/stderr back into task_context so the LLM can
see the result and continue.

Safety constraints:
  - Runs in a dedicated temp directory (not repo root)
  - Hard timeout per execution (default 30s, configurable)
  - stdout + stderr both captured; process never interactive
  - No network restrictions (agent intentionally needs web access)
"""
from __future__ import annotations

import logging
import os
import subprocess
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path

from runtime.config import CODE_RUNNER_TIMEOUT

log = logging.getLogger(__name__)

# Temp dir for all agent-generated scripts
_WORK_DIR = Path(tempfile.gettempdir()) / "mae_agent_runs"
_WORK_DIR.mkdir(exist_ok=True)


@dataclass
class RunResult:
    script_path: str
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool

    def as_text(self) -> str:
        """Plain-text summary the LLM can read."""
        status = "TIMEOUT" if self.timed_out else ("OK" if self.exit_code == 0 else f"ERROR (exit {self.exit_code})")
        parts = [f"[code_runner] {status}"]
        if self.stdout.strip():
            parts.append(f"stdout:\n{self.stdout.strip()}")
        if self.stderr.strip():
            parts.append(f"stderr:\n{self.stderr.strip()}")
        if not self.stdout.strip() and not self.stderr.strip():
            parts.append("(no output)")
        return "\n".join(parts)


def run_python(script: str, timeout: int | None = None) -> RunResult:
    """
    Write `script` to a temp .py file and execute it with the current Python interpreter.
    Returns a RunResult the harness can append to task_context.
    """
    return _run(script, suffix=".py", cmd_prefix=["python3"], timeout=timeout)


def run_bash(script: str, timeout: int | None = None) -> RunResult:
    """
    Write `script` to a temp .sh file and execute it with bash.
    """
    return _run(script, suffix=".sh", cmd_prefix=["bash"], timeout=timeout)


def _run(script: str, suffix: str, cmd_prefix: list[str], timeout: int | None) -> RunResult:
    effective_timeout = timeout or CODE_RUNNER_TIMEOUT
    run_id = str(uuid.uuid4())[:8]
    script_path = _WORK_DIR / f"run_{run_id}{suffix}"
    script_path.write_text(script, encoding="utf-8")

    log.info("code_runner: executing %s (timeout=%ds)", script_path.name, effective_timeout)

    timed_out = False
    try:
        result = subprocess.run(
            cmd_prefix + [str(script_path)],
            capture_output=True,
            text=True,
            timeout=effective_timeout,
            cwd=str(_WORK_DIR),
            env={**os.environ},  # pass through existing env (includes API keys)
        )
        stdout = result.stdout[-4000:] if len(result.stdout) > 4000 else result.stdout
        stderr = result.stderr[-2000:] if len(result.stderr) > 2000 else result.stderr
        exit_code = result.returncode
    except subprocess.TimeoutExpired:
        timed_out = True
        stdout, stderr, exit_code = "", f"Script exceeded {effective_timeout}s timeout.", 1
        log.warning("code_runner: timeout on %s", script_path.name)
    except Exception as exc:
        stdout, stderr, exit_code = "", str(exc), 1
        log.error("code_runner: unexpected error — %s", exc)

    return RunResult(
        script_path=str(script_path),
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        timed_out=timed_out,
    )
