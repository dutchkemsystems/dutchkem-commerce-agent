"""Enterprise sandbox — safe execution of generated code in a subprocess."""

import os
import subprocess
import tempfile
import shutil
from pathlib import Path


class EnterpriseSandbox:
    """Runs untrusted code in an isolated subprocess with resource limits.

    On platforms with Docker available, code can be executed in a container;
    otherwise a time-boxed subprocess with cwd isolation is used.
    """

    def __init__(self, timeout: int = 60, allow_network: bool = False):
        self.timeout = timeout
        self.allow_network = allow_network

    def execute_python(self, code: str, timeout: int = None) -> dict:
        """Execute Python code and return stdout/stderr/returncode."""
        if not timeout:
            timeout = self.timeout
        if shutil.which("docker"):
            return self._run_docker(code, timeout)
        return self._run_subprocess(code, timeout)

    def _run_subprocess(self, code: str, timeout: int) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "script.py"
            script.write_text(code, encoding="utf-8")
            env = dict(os.environ)
            if not self.allow_network:
                env.pop("HTTP_PROXY", None)
                env.pop("HTTPS_PROXY", None)
                env.pop("http_proxy", None)
                env.pop("https_proxy", None)
            try:
                proc = subprocess.run(
                    ["python", str(script)],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=tmp,
                    env=env,
                )
                return {
                    "ok": proc.returncode == 0,
                    "returncode": proc.returncode,
                    "stdout": proc.stdout,
                    "stderr": proc.stderr,
                    "method": "subprocess",
                }
            except subprocess.TimeoutExpired:
                return {
                    "ok": False,
                    "returncode": -1,
                    "stdout": "",
                    "stderr": f"Timed out after {timeout}s",
                    "method": "subprocess",
                }

    def _run_docker(self, code: str, timeout: int) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "script.py"
            script.write_text(code, encoding="utf-8")
            cmd = [
                "docker", "run", "--rm",
                "--memory", "256m",
                "--cpus", "1",
                "-v", f"{tmp}:/work:ro",
                "-w", "/work",
                "python:3.11-slim",
                "python", "script.py",
            ]
            if not self.allow_network:
                cmd.insert(4, "--network")
                cmd.insert(5, "none")
            try:
                proc = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=timeout
                )
                return {
                    "ok": proc.returncode == 0,
                    "returncode": proc.returncode,
                    "stdout": proc.stdout,
                    "stderr": proc.stderr,
                    "method": "docker",
                }
            except subprocess.TimeoutExpired:
                return {
                    "ok": False,
                    "returncode": -1,
                    "stdout": "",
                    "stderr": f"Timed out after {timeout}s",
                    "method": "docker",
                }
