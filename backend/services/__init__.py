from __future__ import annotations

from pathlib import Path
from pkgutil import extend_path

__path__ = extend_path(__path__, __name__)

_PROJECT_SERVICES_ROOT = Path(__file__).resolve().parents[2] / "services"
if _PROJECT_SERVICES_ROOT.is_dir():
    resolved = str(_PROJECT_SERVICES_ROOT)
    if resolved not in __path__:
        __path__.append(resolved)

