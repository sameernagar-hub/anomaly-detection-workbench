from __future__ import annotations

import hashlib
import re
import secrets
from typing import Dict, List, Optional, Tuple

from werkzeug.security import check_password_hash, generate_password_hash

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

COMMON_PASSWORDS = {
    "password",
    "password123",
    "123456789",
    "qwerty123",
    "letmein",
    "welcome123",
    "admin123",
    "changeme",
}


def normalize_email(email: str) -> str:
    return email.strip().lower()


def is_valid_email(email: str) -> bool:
    return bool(EMAIL_RE.match(normalize_email(email)))


def password_policy_feedback(password: str, email: str = "", profile_values: Optional[List[str]] = None) -> Tuple[bool, List[str]]:
    issues: List[str] = []
    normalized_email = normalize_email(email)
    email_local = normalized_email.split("@")[0] if "@" in normalized_email else ""
    lowered = password.lower()

    if len(password) < 12:
        issues.append("Use at least 12 characters.")
    if not re.search(r"[A-Z]", password):
        issues.append("Include at least one uppercase letter.")
    if not re.search(r"[a-z]", password):
        issues.append("Include at least one lowercase letter.")
    if not re.search(r"\d", password):
        issues.append("Include at least one number.")
    if not re.search(r"[^A-Za-z0-9]", password):
        issues.append("Include at least one special character.")
    if lowered in COMMON_PASSWORDS:
        issues.append("Choose a less common password.")
    if email_local and email_local in lowered:
        issues.append("Do not include your email name in the password.")
    for value in profile_values or []:
        cleaned = re.sub(r"[^a-z0-9]", "", value.lower())
        if cleaned and len(cleaned) >= 4 and cleaned in re.sub(r"[^a-z0-9]", "", lowered):
            issues.append("Avoid using profile details in the password.")
            break
    return (not issues), issues


def hash_password(password: str) -> str:
    return generate_password_hash(password, method="pbkdf2:sha256", salt_length=16)


def verify_password(password_hash: str, password: str) -> bool:
    return check_password_hash(password_hash, password)


def generate_otp_code(length: int = 6) -> str:
    digits = "0123456789"
    return "".join(secrets.choice(digits) for _ in range(length))


def generate_token(length: int = 32) -> str:
    return secrets.token_urlsafe(length)


def digest_secret(secret_value: str) -> str:
    return hashlib.sha256(secret_value.encode("utf-8")).hexdigest()


def verify_secret(secret_hash: str, candidate: str) -> bool:
    return secrets.compare_digest(secret_hash, digest_secret(candidate))


def password_strength(password: str) -> Dict[str, object]:
    score = 0
    if len(password) >= 12:
        score += 1
    if re.search(r"[A-Z]", password):
        score += 1
    if re.search(r"[a-z]", password):
        score += 1
    if re.search(r"\d", password):
        score += 1
    if re.search(r"[^A-Za-z0-9]", password):
        score += 1
    if len(password) >= 16:
        score += 1

    if score <= 2:
        label = "Needs work"
    elif score <= 4:
        label = "Solid"
    else:
        label = "Strong"
    return {"score": score, "label": label}
