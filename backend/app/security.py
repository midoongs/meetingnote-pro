from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from . import config
from .errors import AppError


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode("utf-8")[:72], bcrypt.gensalt(rounds=11)).decode()


def check_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode("utf-8")[:72], hashed.encode())
    except ValueError:
        return False


def make_token(user_id: int) -> str:
    exp = datetime.now(timezone.utc) + timedelta(hours=config.JWT_HOURS)
    return jwt.encode({"sub": str(user_id), "exp": exp}, config.JWT_SECRET, algorithm="HS256")


def read_token(token: str) -> int:
    """만료와 위조는 모두 화면이 세션을 끝내도록 TOKEN_EXPIRED 로 돌려준다."""
    try:
        data = jwt.decode(token, config.JWT_SECRET, algorithms=["HS256"])
        return int(data["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise AppError(401, "TOKEN_EXPIRED", "세션이 만료됨")
