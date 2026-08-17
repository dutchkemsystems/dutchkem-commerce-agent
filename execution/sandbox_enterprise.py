"""Enterprise sandbox — safe execution of generated code in a subprocess or container.

Security model:
  * Docker is preferred whenever available (isolated, resource-capped, no
    network, no host env, no capabilities, read-only filesystem).
  * The raw-subprocess fallback scrubs the inherited environment so generated
    (untrusted) code never sees API keys/secrets, runs in an isolated cwd, and
    on POSIX applies RLIMIT_AS / RLIMIT_CPU / RLIMIT_NOFILE jail limits.
"""

import os
import shutil
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

# Env vars a sandboxed process is allowed to see. Anything else (API keys,
# tokens, internal paths) is stripped from the child environment.
SAFE_ENV_ALLOWLIST = {
    "PATH", "HOME", "LANG", "LC_ALL", "LANGUAGE",
    "SYSTEMROOT", "SystemRoot", "WINDIR", "TEMP", "TMP",
    "USERNAME", "USER", "USERPROFILE", "LOGNAME",
    "COMSPEC", "PATHEXT",
    "PROCESSOR_ARCHITECTURE", "NUMBER_OF_PROCESSORS",
    "PYTHONIOENCODING",
}


class EnterpriseSandbox:
    """Runs untrusted code in an isolated subprocess or Docker container."""

    docker_image = "python:3.11-slim"

    def __init__(self, timeout: int = 60, allow_network: bool = False,
                 max_memory_mb: int = 256, max_cpu_seconds: int = 30):
        self.timeout = timeout
        self.allow_network = allow_network
        self.max_memory_mb = max_memory_mb
        self.max_cpu_seconds = max_cpu_seconds

    def execute_python(self, code: str, timeout: int = None) -> dict:
        """Execute Python code and return stdout/stderr/returncode."""
        if not timeout:
            timeout = self.timeout
        if shutil.which("docker"):
            return self._run_docker(code, timeout)
        return self._run_subprocess(code, timeout)

    # ---------- Docker ------------------------------------------------

    def _run_docker(self, code: str, timeout: int) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "script.py"
            script.write_text(code, encoding="utf-8")
            cmd = [
                "docker", "run", "--rm",
                "--network", "none" if not self.allow_network else "default",
                "--memory", f"{self.max_memory_mb}m",
                "--cpus", "1",
                "--pids-limit", "128",
                "--read-only",
                "--tmpfs", "/tmp:rw,noexec,nosuid,size=16m",
                "--cap-drop", "ALL",
                "--security-opt", "no-new-privileges",
                "-v", f"{tmp}:/work:ro",
                "-w", "/work",
                self.docker_image,
                "python", "script.py",
            ]
            # Floating mount paths are auto-created by tmpfs; no host env, no
            # secrets are passed into the container.
            return self._run(cmd, timeout, method="docker")

    # ---------- Subprocess fallback ----------------------------------

    def _run_subprocess(self, code: str, timeout: int) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "script.py"
            script.write_text(code, encoding="utf-8")
            kwargs = dict(
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=tmp,
                env=self._sanitized_env(),
                start_new_session=True,
            )
            if sys.platform != "win32":
                kwargs["preexec_fn"] = self._make_limits()
            try:
                proc = subprocess.run(["python", str(script)], **kwargs)
                return {
                    "ok": proc.returncode == 0,
                    "returncode": proc.returncode,
                    "stdout": proc.stdout,
                    "stderr": proc.stderr,
                    "method": "subprocess",
                }
            except subprocess.TimeoutExpired:  # subprocess.run already killed the child
                return {
                    "ok": False,
                    "returncode": -1,
                    "stdout": "",
                    "stderr": f"Timed out after {timeout}s",
                    "method": "subprocess",
                }

    def _sanitized_env(self) -> dict:
        """A child env containing only SAFE_ENV_ALLOWLIST entries."""
        env = {}
        for key in SAFE_ENV_ALLOWLIST:
            value = os.environ.get(key)
            if value is not None:
                env[key] = value
        if not self.allow_network:
            for key in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy", "NO_PROXY", "no_proxy"):
                env.pop(key, None)
        return env

    def _make_limits(self):
        """Return a preexec_fn that jails the child with RLIMIT rlimits."""
        max_as = self.max_memory_mb * 1024 * 1024
        cpu = max(1, self.max_cpu_seconds)

        def _apply():
            import resource
            resource.setrlimit(resource.RLIMIT_AS, (max_as, max_as))
            resource.setrlimit(resource.RLIMIT_DATA, (max_as, max_as))
            resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu + 1))
            resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
            signal.signal(signal.SIGXCPU, signal.SIG_TERM)
            signal.signal(signal.SIGXFSZ, signal.SIG_IGN)
        return _apply

    @staticmethod
    def _run(cmd, timeout: int, method: str) -> dict:
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return {
                "ok": proc.returncode == 0,
                "returncode": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "method": method,
            }
        except subprocess.TimeoutExpired:
            return {
                "ok": False,
                "returncode": -1,
                "stdout": "",
                "stderr": f"Timed out after {timeout}s",
                "method": method,
            }
