"""OpenAI-compatible model profiles persisted on disk (API keys never returned in full)."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from config import settings


def _path() -> Path:
    path = Path(settings.model_profiles_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _mask_key(key: str) -> tuple[bool, str]:
    if not key:
        return False, ""
    tail = key[-4:] if len(key) >= 4 else "****"
    return True, f"****{tail}"


def _normalize_api_base(url: str) -> str:
    u = (url or "").strip().rstrip("/")
    if not u:
        return u
    if not u.startswith(("http://", "https://")):
        u = "https://" + u
    return u


def _combine_base(api_base_norm: str, path_suffix: str | None) -> str:
    ps = (path_suffix or "").strip().rstrip("/")
    if ps and not ps.startswith("/"):
        ps = "/" + ps
    combined = api_base_norm.rstrip("/") + (ps if ps else "")
    if not ps and not combined.endswith("/v1"):
        combined = combined + "/v1"
    return combined


def effective_api_base(p: dict[str, Any]) -> str:
    c = str(p.get("combined_base") or "").strip().rstrip("/")
    if c:
        return c
    base = _normalize_api_base(str(p.get("api_base") or ""))
    ps = p.get("api_path")
    path_suffix = (str(ps) if ps is not None else "").strip().rstrip("/")
    if path_suffix and not path_suffix.startswith("/"):
        path_suffix = "/" + path_suffix
    return _combine_base(base, path_suffix if path_suffix else None)


def load_store() -> dict[str, Any]:
    path = _path()
    if not path.is_file():
        return {"profiles": [], "default_profile_id": None}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {"profiles": [], "default_profile_id": None}
        data.setdefault("profiles", [])
        data.setdefault("default_profile_id", None)
        return data
    except Exception:
        return {"profiles": [], "default_profile_id": None}


def save_store(data: dict[str, Any]) -> None:
    path = _path()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def to_public_dict(p: dict[str, Any]) -> dict[str, Any]:
    key = str(p.get("api_key") or "")
    has_key, hint = _mask_key(key)
    row = {k: v for k, v in p.items() if k != "api_key"}
    row["has_api_key"] = has_key
    row["api_key_hint"] = hint if has_key else ""
    row.setdefault("combined_base", effective_api_base(p))
    return row


def list_profiles_public() -> list[dict[str, Any]]:
    data = load_store()
    return [to_public_dict(p) for p in (data.get("profiles") or [])]


def get_profile_raw(profile_id: str) -> dict[str, Any] | None:
    for p in load_store().get("profiles") or []:
        if str(p.get("id")) == profile_id:
            return dict(p)
    return None


def upsert_profile(
    *,
    profile_id: str | None,
    name: str,
    vendor: str,
    api_base: str,
    api_path: str | None,
    default_model: str,
    api_key: str | None,
    extra_headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    data = load_store()
    profiles: list[dict[str, Any]] = list(data.get("profiles") or [])
    api_base_norm = _normalize_api_base(api_base)
    path_suffix = (api_path or "").strip().rstrip("/")
    if path_suffix and not path_suffix.startswith("/"):
        path_suffix = "/" + path_suffix
    combined_base = _combine_base(api_base_norm, path_suffix if path_suffix else None)

    if profile_id:
        found = False
        for i, p in enumerate(profiles):
            if str(p.get("id")) == profile_id:
                p2 = dict(p)
                p2.update(
                    {
                        "name": name,
                        "vendor": vendor,
                        "api_base": api_base_norm,
                        "api_path": path_suffix or None,
                        "combined_base": combined_base,
                        "default_model": default_model,
                        "extra_headers": extra_headers or {},
                    }
                )
                if api_key is not None and api_key.strip():
                    p2["api_key"] = api_key.strip()
                profiles[i] = p2
                found = True
                out = p2
                break
        if not found:
            raise KeyError(profile_id)
    else:
        pid = str(uuid.uuid4())
        out = {
            "id": pid,
            "name": name,
            "vendor": vendor,
            "api_base": api_base_norm,
            "api_path": path_suffix or None,
            "combined_base": combined_base,
            "default_model": default_model,
            "api_key": (api_key or "").strip(),
            "extra_headers": extra_headers or {},
        }
        profiles.append(out)

    data["profiles"] = profiles
    save_store(data)
    return out


def delete_profile(profile_id: str) -> bool:
    data = load_store()
    old = list(data.get("profiles") or [])
    profiles = [p for p in old if str(p.get("id")) != profile_id]
    if len(profiles) == len(old):
        return False
    data["profiles"] = profiles
    if str(data.get("default_profile_id") or "") == profile_id:
        data["default_profile_id"] = None
    save_store(data)
    return True


def set_default_profile(profile_id: str | None) -> None:
    data = load_store()
    if profile_id:
        ids = {str(p.get("id")) for p in (data.get("profiles") or [])}
        if profile_id not in ids:
            raise KeyError(profile_id)
    data["default_profile_id"] = profile_id
    save_store(data)


def get_default_profile_id() -> str | None:
    return load_store().get("default_profile_id")  # type: ignore[return-value]

