import re

_INJECTION_PATTERNS = (
    r"ignore\s+(all\s+)?(previous|prior)\s+instructions",
    r"system\s*:\s*",
    r"<\s*/?\s*script",
    r"```\s*system",
)


def scan_prompt_injection(text: str) -> tuple[bool, str | None]:
    t = text.lower()
    for pat in _INJECTION_PATTERNS:
        if re.search(pat, t, re.I):
            return False, f"命中可疑模式: {pat}"
    if len(text) > 12000:
        return False, "输入过长"
    return True, None
