"""Vercel 진입점. 코드는 backend/ 한 벌이며 로컬과 배포가 같다."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from app.main import app  # noqa: E402,F401
