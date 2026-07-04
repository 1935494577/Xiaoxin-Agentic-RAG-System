"""Auth HTTP routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from auth.middleware import get_auth_user
from auth.service import (
    admin_create_user,
    admin_list_users_public,
    admin_reset_password,
    change_password,
    login,
    logout,
    set_user_active,
)
from security.access_control import DEPARTMENTS
from security.department_features import FULL_ACCESS_DEPARTMENT

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1, max_length=128)
    remember: bool = True


class AuthUserPublic(BaseModel):
    id: str
    username: str
    department: str
    display_name: str


class LoginResponse(BaseModel):
    token: str
    user: AuthUserPublic


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=6, max_length=128)


class AdminCreateUserRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=64)
    password: str = Field(..., min_length=6, max_length=128)
    department: str = Field(..., max_length=64)
    display_name: str = Field(default="", max_length=64)


class AdminResetPasswordRequest(BaseModel):
    new_password: str = Field(..., min_length=6, max_length=128)


class AdminUserActiveRequest(BaseModel):
    is_active: bool


def _require_auth(request: Request) -> dict:
    user = get_auth_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="未登录")
    return user


def _require_tech(user: dict = Depends(_require_auth)) -> dict:
    if user.get("department") != FULL_ACCESS_DEPARTMENT:
        raise HTTPException(status_code=403, detail="仅技术部可管理账号")
    return user


def _token(request: Request) -> str:
    auth = (request.headers.get("authorization") or "").strip()
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return (request.headers.get("x-session-token") or "").strip()


@router.post("/login", response_model=LoginResponse)
def auth_login(body: LoginRequest):
    try:
        out = login(body.username, body.password, remember=body.remember)
    except ValueError as exc:
        if str(exc) == "invalid_credentials":
            raise HTTPException(status_code=401, detail="用户名或密码错误") from exc
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return LoginResponse(
        token=out["token"],
        user=AuthUserPublic.model_validate(out["user"]),
    )


@router.post("/logout")
def auth_logout(request: Request):
    logout(_token(request))
    return {"ok": True}


@router.get("/me", response_model=AuthUserPublic)
def auth_me(user: dict = Depends(_require_auth)):
    return AuthUserPublic(
        id=user["id"],
        username=user["username"],
        department=user["department"],
        display_name=user.get("display_name") or user["username"],
    )


@router.post("/change-password")
def auth_change_password(body: ChangePasswordRequest, user: dict = Depends(_require_auth)):
    try:
        change_password(user["id"], body.current_password, body.new_password)
    except ValueError as exc:
        code = str(exc)
        if code == "invalid_credentials":
            raise HTTPException(status_code=401, detail="当前密码不正确") from exc
        if code == "password_too_short":
            raise HTTPException(status_code=400, detail="新密码至少 6 位") from exc
        raise HTTPException(status_code=400, detail=code) from exc
    return {"ok": True}


@router.get("/departments")
def auth_departments():
    return {"departments": list(DEPARTMENTS)}


@router.get("/admin/users")
def auth_admin_list_users(_: dict = Depends(_require_tech)):
    return {"users": admin_list_users_public()}


@router.post("/admin/users", response_model=AuthUserPublic)
def auth_admin_create_user(body: AdminCreateUserRequest, _: dict = Depends(_require_tech)):
    try:
        row = admin_create_user(
            username=body.username,
            password=body.password,
            department=body.department,
            display_name=body.display_name,
        )
    except ValueError as exc:
        msg = str(exc)
        if msg == "username already exists":
            raise HTTPException(status_code=409, detail="用户名已存在") from exc
        if msg == "invalid_department":
            raise HTTPException(status_code=400, detail="无效部门") from exc
        raise HTTPException(status_code=400, detail=msg) from exc
    return AuthUserPublic(
        id=row["id"],
        username=row["username"],
        department=row["department"],
        display_name=row.get("display_name") or row["username"],
    )


@router.post("/admin/users/{user_id}/reset-password")
def auth_admin_reset_password(
    user_id: str,
    body: AdminResetPasswordRequest,
    _: dict = Depends(_require_tech),
):
    try:
        admin_reset_password(user_id, body.new_password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True}


@router.patch("/admin/users/{user_id}/active")
def auth_admin_set_active(
    user_id: str,
    body: AdminUserActiveRequest,
    _: dict = Depends(_require_tech),
):
    if not set_user_active(user_id, active=body.is_active):
        raise HTTPException(status_code=404, detail="用户不存在")
    return {"ok": True}
