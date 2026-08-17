"""Plugin manager — a marketplace hub for community extensions."""

import importlib
from pathlib import Path
from typing import Any


class PluginManager:
    """Discovers, loads, and manages plugins from the plugins/ directory."""

    def __init__(self, plugin_dir: str = None):
        base = Path(plugin_dir or (Path(__file__).resolve().parent.parent / "plugins"))
        self._base = base
        self._base.mkdir(parents=True, exist_ok=True)
        self._loaded: dict[str, Any] = {}

    @property
    def base(self) -> Path:
        return self._base

    @base.setter
    def base(self, value: Path):
        self._base = value

    def discover(self) -> list[str]:
        """List available plugin modules (single-file plugins)."""
        names = []
        for py in sorted(self.base.glob("*.py")):
            if py.name == "__init__.py":
                continue
            names.append(py.stem)
        return names

    def load(self, name: str) -> Any:
        if name in self._loaded:
            return self._loaded[name]
        spec_path = self.base / f"{name}.py"
        if not spec_path.exists():
            raise FileNotFoundError(f"plugin '{name}' not found in {self.base}")
        spec = importlib.util.spec_from_file_location(f"plugins.{name}", spec_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self._loaded[name] = module
        return module

    def load_all(self) -> dict[str, Any]:
        for name in self.discover():
            try:
                self.load(name)
            except Exception:  # noqa: BLE001
                continue
        return self._loaded

    def installed(self) -> list[str]:
        return sorted(self._loaded.keys())
