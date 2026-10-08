"""환경 설정. 키는 프로젝트 루트의 .env 에서만 읽는다 (GEMINI_API_KEY, GEMINI_MODEL)."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

FRONTEND_DIR = ROOT / "frontend"

# 코드 기본값 (정의서 7-5: JWT_SECRET · DATABASE_URL · CORS 는 .env 에 두지 않는다)
JWT_SECRET = os.getenv("JWT_SECRET", "meetingnote-dev-secret-change-me")
JWT_HOURS = 24

MAX_UPLOAD_BYTES = 25 * 1024 * 1024
TEAM_LIMIT = 6
COMMENT_LIMIT = 500
ACTIVITY_LIMIT = 50

# 허용 도메인을 명시한다. 배포 도메인은 배포 환경변수 CORS_ORIGINS 로 더한다.
CORS_ORIGINS = ["http://127.0.0.1:8000", "http://localhost:8000"] + [
    o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()
]


def database_url() -> str:
    """DATABASE_URL 이 있으면 Neon(Postgres), 없으면 로컬 SQLite 한 줄 분기."""
    url = os.getenv("DATABASE_URL")
    if url:
        if url.startswith("postgres://"):
            url = "postgresql+psycopg://" + url[len("postgres://"):]
        elif url.startswith("postgresql://"):
            url = "postgresql+psycopg://" + url[len("postgresql://"):]
        return url
    return f"sqlite:///{ROOT / 'meetingnote.db'}"


def is_deployed() -> bool:
    return bool(os.getenv("DATABASE_URL"))
