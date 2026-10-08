import re

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .. import models
from ..deps import current_user, get_db, membership_of
from ..errors import AppError, bad, validation
from ..security import check_password, hash_password, make_token

router = APIRouter(prefix="/auth", tags=["auth"])

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class SignupIn(BaseModel):
    email: str
    password: str
    name: str
    invite_code: str | None = None  # 합류는 화면이 가입 직후 /teams/join 으로 부른다


class LoginIn(BaseModel):
    email: str
    password: str


class MeIn(BaseModel):
    name: str | None = None
    current_password: str | None = None
    new_password: str | None = None


def me_view(db: Session, user: models.User) -> dict:
    m = membership_of(db, user.id)
    team = db.get(models.Team, m.team_id) if m else None
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "team_id": team.id if team else None,
        "team_name": team.name if team else None,
        "role": m.role if m else None,
    }


def check_new_password(pw: str) -> None:
    if len(pw) < 8:
        raise bad("PASSWORD_TOO_WEAK", "비밀번호는 8자 이상")


@router.post("/signup", status_code=201)
def signup(body: SignupIn, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    if not EMAIL_RE.match(email):
        raise bad("EMAIL_INVALID", "이메일 형식이 올바르지 않음")
    check_new_password(body.password)
    if not body.name.strip():
        raise validation("이름을 입력해야 함")
    if db.query(models.User).filter_by(email=email).first():
        raise bad("EMAIL_DUPLICATED", "이미 가입된 이메일", 409)
    user = models.User(email=email, password_hash=hash_password(body.password), name=body.name.strip())
    db.add(user)
    db.commit()
    return {"token": make_token(user.id), "user": me_view(db, user), "team_id": None}


@router.post("/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.query(models.User).filter_by(email=body.email.strip().lower()).first()
    # 이메일 존재 여부를 드러내지 않도록 같은 응답을 쓴다
    if user is None or not check_password(body.password, user.password_hash):
        raise AppError(401, "INVALID_CREDENTIALS", "이메일 또는 비밀번호가 올바르지 않음")
    view = me_view(db, user)
    return {"token": make_token(user.id), "user": view, "team_id": view["team_id"]}


@router.get("/me")
def me(user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    return me_view(db, user)


@router.put("/me")
def update_me(body: MeIn, user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    if body.new_password:
        # 비밀번호를 바꿀 때만 현재 비밀번호를 요구한다
        if not body.current_password or not check_password(body.current_password, user.password_hash):
            raise AppError(401, "UNAUTHORIZED", "현재 비밀번호가 틀림")
        check_new_password(body.new_password)
        user.password_hash = hash_password(body.new_password)
    if body.name is not None:
        if not body.name.strip():
            raise validation("이름을 입력해야 함")
        user.name = body.name.strip()
    db.commit()
    return me_view(db, user)


@router.post("/logout")
def logout(_: models.User = Depends(current_user)):
    # JWT 는 무상태: 서버는 블랙리스트를 두지 않고 200 만 돌려준다
    return {"ok": True}
