import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

GTEX_ROOT = Path(os.environ["GTEX_REPO_ROOT"])
for path in (GTEX_ROOT, GTEX_ROOT / "backend"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app.main import get_asgi_app  # noqa: E402

app = get_asgi_app()
