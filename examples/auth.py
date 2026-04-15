from __future__ import annotations

import os
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple
from urllib.parse import urljoin

from flask import Blueprint, Response, abort, current_app, flash, g, jsonify, redirect, render_template, request, send_file, session, url_for
from werkzeug.utils import secure_filename

from db import row_to_dict
from human_verification import make_human_challenge_bundle, validate_human_bundle
from security import digest_secret, generate_token, hash_password, is_valid_email, normalize_email, password_policy_feedback, password_strength, verify_password

REMEMBER_DAYS = 21
VERIFY_WINDOW_MINUTES = 5
MAX_VERIFY_ATTEMPTS = 5
RESET_EXPIRY_MINUTES = 30
ALLOWED_AVATAR_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
MAX_AVATAR_BYTES = 2 * 1024 * 1024

auth_bp = Blueprint("auth", __name__, template_folder="templates")


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def now_text() -> str:
    return now_utc().isoformat()


def _db() -> sqlite3.Connection:
    return current_app.config["DB"]


def _runtime_dir() -> Path:
    return Path(current_app.config["RUNTIME_DIR"])


def _avatar_dir() -> Path:
    path = _runtime_dir() / "avatars"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _safe_next_path(candidate: Any) -> str:
    value = str(candidate or "").strip()
    if not value or not value.startswith("/") or value.startswith("//"):
        return url_for("overview")
    if value.startswith("/auth/verify-human"):
        return url_for("overview")
    return value


def _make_public_user_id() -> str:
    return f"ADW-{uuid.uuid4().hex[:8].upper()}"


def fetch_user_by_id(user_id: Optional[int]) -> Optional[Dict[str, Any]]:
    if not user_id:
        return None
    row = _db().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return row_to_dict(row)


def fetch_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    row = _db().execute("SELECT * FROM users WHERE email = ?", (normalize_email(email),)).fetchone()
    return row_to_dict(row)


def fetch_profile(user_id: int) -> Optional[Dict[str, Any]]:
    row = _db().execute("SELECT * FROM user_profiles WHERE user_id = ?", (user_id,)).fetchone()
    return row_to_dict(row)


def current_user() -> Optional[Dict[str, Any]]:
    return getattr(g, "current_user", None)


def current_profile() -> Optional[Dict[str, Any]]:
    return getattr(g, "current_profile", None)


def build_profile_form(form: Dict[str, Any], profile: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    base = profile or {}
    first_name = str(form.get("first_name", base.get("first_name", ""))).strip()
    last_name = str(form.get("last_name", base.get("last_name", ""))).strip()
    full_name = f"{first_name} {last_name}".strip()
    display_name = str(form.get("display_name", base.get("display_name", ""))).strip() or first_name
    return {
        "first_name": first_name,
        "last_name": last_name,
        "full_name": full_name,
        "display_name": display_name,
        "role": str(form.get("role", base.get("role", ""))).strip(),
        "organization": str(form.get("organization", base.get("organization", ""))).strip(),
        "monitoring_focus": str(form.get("monitoring_focus", base.get("monitoring_focus", ""))).strip(),
        "primary_os": str(form.get("primary_os", base.get("primary_os", "Windows"))).strip() or "Windows",
        "host_environment": str(form.get("host_environment", base.get("host_environment", ""))).strip(),
        "log_source_preference": str(form.get("log_source_preference", base.get("log_source_preference", ""))).strip(),
        "live_trace_os_preference": str(form.get("live_trace_os_preference", base.get("live_trace_os_preference", "Windows"))).strip() or "Windows",
        "preferred_theme": str(form.get("preferred_theme", base.get("preferred_theme", "campus"))).strip() or "campus",
        "preferred_analysis_mode": str(form.get("preferred_analysis_mode", base.get("preferred_analysis_mode", "compare"))).strip() or "compare",
        "notification_preference": str(form.get("notification_preference", base.get("notification_preference", "important-only"))).strip() or "important-only",
        "greeting_style": str(form.get("greeting_style", base.get("greeting_style", "warm"))).strip() or "warm",
        "avatar_path": str(base.get("avatar_path", "")),
    }


def validate_signup_form(form: Dict[str, Any]) -> Tuple[Dict[str, str], Dict[str, str]]:
    profile = build_profile_form(form)
    errors: Dict[str, str] = {}
    email = normalize_email(str(form.get("email", "")))
    password = str(form.get("password", ""))
    confirm_password = str(form.get("confirm_password", ""))

    if not is_valid_email(email):
        errors["email"] = "Use a valid email address."
    if not profile["first_name"]:
        errors["first_name"] = "First name is required."
    if not profile["last_name"]:
        errors["last_name"] = "Last name is required."
    if not profile["display_name"]:
        errors["display_name"] = "Choose the name the app should greet you with."
    valid_password, feedback = password_policy_feedback(
        password,
        email=email,
        profile_values=[profile["first_name"], profile["last_name"], profile["display_name"], profile["organization"]],
    )
    if not valid_password:
        errors["password"] = " ".join(feedback)
    if password != confirm_password:
        errors["confirm_password"] = "Passwords need to match."
    if fetch_user_by_email(email):
        errors["email"] = "An account with that email already exists."
    profile["email"] = email
    return profile, errors


def create_user_and_profile(email: str, password: str, profile_data: Dict[str, str]) -> Dict[str, Any]:
    database = _db()
    created_at = now_text()
    public_user_id = _make_public_user_id()
    cursor = database.cursor()
    cursor.execute(
        """
        INSERT INTO users (email, public_user_id, password_hash, is_active, email_verified, created_at)
        VALUES (?, ?, ?, 1, 1, ?)
        """,
        (normalize_email(email), public_user_id, hash_password(password), created_at),
    )
    user_id = int(cursor.lastrowid)
    cursor.execute(
        """
        INSERT INTO user_profiles (
            user_id, first_name, last_name, full_name, display_name, role, organization, monitoring_focus,
            primary_os, host_environment, log_source_preference, live_trace_os_preference, avatar_path,
            preferred_theme, preferred_analysis_mode, notification_preference, greeting_style, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            profile_data["first_name"],
            profile_data["last_name"],
            profile_data["full_name"],
            profile_data["display_name"],
            profile_data.get("role", ""),
            profile_data.get("organization", ""),
            profile_data.get("monitoring_focus", ""),
            profile_data.get("primary_os", "Windows"),
            profile_data.get("host_environment", ""),
            profile_data.get("log_source_preference", ""),
            profile_data.get("live_trace_os_preference", "Windows"),
            profile_data.get("avatar_path", ""),
            profile_data.get("preferred_theme", "campus"),
            profile_data.get("preferred_analysis_mode", "compare"),
            profile_data.get("notification_preference", "important-only"),
            profile_data.get("greeting_style", "warm"),
            created_at,
            created_at,
        ),
    )
    database.commit()
    return {"user": fetch_user_by_id(user_id), "profile": fetch_profile(user_id)}


def update_profile(user_id: int, profile_data: Dict[str, str]) -> Dict[str, Any]:
    database = _db()
    updated_at = now_text()
    database.execute(
        """
        UPDATE user_profiles
        SET first_name = ?, last_name = ?, full_name = ?, display_name = ?, role = ?, organization = ?, monitoring_focus = ?,
            primary_os = ?, host_environment = ?, log_source_preference = ?, live_trace_os_preference = ?, avatar_path = ?,
            preferred_theme = ?, preferred_analysis_mode = ?, notification_preference = ?, greeting_style = ?, updated_at = ?
        WHERE user_id = ?
        """,
        (
            profile_data["first_name"],
            profile_data["last_name"],
            profile_data["full_name"],
            profile_data["display_name"],
            profile_data.get("role", ""),
            profile_data.get("organization", ""),
            profile_data.get("monitoring_focus", ""),
            profile_data.get("primary_os", "Windows"),
            profile_data.get("host_environment", ""),
            profile_data.get("log_source_preference", ""),
            profile_data.get("live_trace_os_preference", "Windows"),
            profile_data.get("avatar_path", ""),
            profile_data.get("preferred_theme", "campus"),
            profile_data.get("preferred_analysis_mode", "compare"),
            profile_data.get("notification_preference", "important-only"),
            profile_data.get("greeting_style", "warm"),
            updated_at,
            user_id,
        ),
    )
    database.commit()
    return fetch_profile(user_id) or {}


def _avatar_url(profile: Optional[Dict[str, Any]]) -> Optional[str]:
    if profile and profile.get("avatar_path"):
        return url_for("auth.avatar_file", filename=Path(str(profile["avatar_path"])).name)
    return None


def _save_avatar(file_storage: Any, user_id: int) -> str:
    filename = secure_filename(file_storage.filename or "")
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_AVATAR_EXTENSIONS:
        raise ValueError("Use an image file like PNG, JPG, WEBP, or GIF.")
    file_storage.stream.seek(0, os.SEEK_END)
    size = file_storage.stream.tell()
    file_storage.stream.seek(0)
    if size > MAX_AVATAR_BYTES:
        raise ValueError("Avatar images must be under 2 MB.")
    target_name = f"user_{user_id}_{uuid.uuid4().hex[:8]}{suffix}"
    target_path = _avatar_dir() / target_name
    file_storage.save(target_path)
    return str(target_path.resolve())


def _set_pending_verification(user_id: int, remember_me: bool) -> None:
    bundle = make_human_challenge_bundle()
    session["pending_user_id"] = user_id
    session["pending_human_payload"] = bundle["payload"]
    session["pending_human_answers"] = bundle["answers"]
    session["pending_human_attempts"] = 0
    session["pending_human_expires_at"] = (now_utc() + timedelta(minutes=VERIFY_WINDOW_MINUTES)).isoformat()
    session["pending_remember_me"] = remember_me


def _clear_pending_verification() -> None:
    for key in (
        "pending_user_id",
        "pending_human_payload",
        "pending_human_answers",
        "pending_human_attempts",
        "pending_human_expires_at",
        "pending_next",
        "pending_remember_me",
    ):
        session.pop(key, None)


def _pending_verification_valid() -> bool:
    expires_at = session.get("pending_human_expires_at")
    if not expires_at:
        return False
    try:
        return now_utc() <= datetime.fromisoformat(str(expires_at))
    except ValueError:
        return False


def _refresh_human_challenge() -> None:
    bundle = make_human_challenge_bundle()
    session["pending_human_payload"] = bundle["payload"]
    session["pending_human_answers"] = bundle["answers"]
    session["pending_human_attempts"] = 0
    session["pending_human_expires_at"] = (now_utc() + timedelta(minutes=VERIFY_WINDOW_MINUTES)).isoformat()


def create_password_reset(user: Dict[str, Any]) -> Dict[str, Any]:
    database = _db()
    token = generate_token(24)
    created_at = now_utc()
    expires_at = created_at + timedelta(minutes=RESET_EXPIRY_MINUTES)
    database.execute(
        "UPDATE password_reset_tokens SET consumed_at = ? WHERE user_id = ? AND consumed_at IS NULL",
        (created_at.isoformat(), int(user["id"])),
    )
    database.execute(
        """
        INSERT INTO password_reset_tokens (user_id, token_hash, expires_at, consumed_at, created_at)
        VALUES (?, ?, ?, NULL, ?)
        """,
        (int(user["id"]), digest_secret(token), expires_at.isoformat(), created_at.isoformat()),
    )
    database.commit()
    reset_link = urljoin(request.url_root, url_for("auth.reset_password", token=token))
    profile = fetch_profile(int(user["id"])) or {}
    current_app.config["MAILER"].send_reset_link(
        recipient=str(user["email"]),
        reset_link=reset_link,
        display_name=profile.get("display_name") or profile.get("full_name"),
    )
    return {"token": token, "expires_at": expires_at.isoformat()}


def get_valid_reset_token(token: str) -> Optional[Dict[str, Any]]:
    row = _db().execute(
        "SELECT * FROM password_reset_tokens WHERE token_hash = ? ORDER BY created_at DESC LIMIT 1",
        (digest_secret(token),),
    ).fetchone()
    payload = row_to_dict(row)
    if not payload or payload.get("consumed_at"):
        return None
    if now_utc() > datetime.fromisoformat(str(payload["expires_at"])):
        return None
    return payload


def complete_password_reset(token_row: Dict[str, Any], new_password: str) -> None:
    database = _db()
    database.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hash_password(new_password), int(token_row["user_id"])))
    database.execute(
        "UPDATE password_reset_tokens SET consumed_at = ? WHERE user_id = ? AND consumed_at IS NULL",
        (now_text(), int(token_row["user_id"])),
    )
    database.commit()


def login_user(user: Dict[str, Any], remember_me: bool = False) -> None:
    session["user_id"] = int(user["id"])
    session.permanent = bool(remember_me)
    if remember_me:
        current_app.permanent_session_lifetime = timedelta(days=REMEMBER_DAYS)
    _clear_pending_verification()
    _db().execute(
        "UPDATE users SET last_login_at = ?, last_otp_verified_at = ? WHERE id = ?",
        (now_text(), now_text(), int(user["id"])),
    )
    _db().commit()


def logout_user() -> None:
    session.clear()


def wants_json() -> bool:
    accept = request.headers.get("Accept", "")
    return request.path.startswith("/api/") or "application/json" in accept


def login_required(view: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(view)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        user = current_user()
        if user and int(user.get("is_active", 0)) == 1:
            return view(*args, **kwargs)
        if wants_json():
            return jsonify({"error": "Authentication required."}), 401
        next_path = request.full_path if request.query_string else request.path
        return redirect(url_for("auth.login", next=next_path))

    return wrapped


@auth_bp.before_app_request
def load_logged_in_user() -> None:
    user = fetch_user_by_id(session.get("user_id"))
    g.current_user = user
    g.current_profile = fetch_profile(int(user["id"])) if user else None


@auth_bp.app_context_processor
def inject_auth_context() -> Dict[str, Any]:
    user = current_user()
    profile = current_profile()
    greeting_name = profile.get("display_name") if profile else None
    avatar_url = _avatar_url(profile)
    return {
        "auth_user": user,
        "auth_profile": profile,
        "greeting_name": greeting_name,
        "auth_avatar_url": avatar_url,
    }


@auth_bp.route("/avatars/<filename>")
def avatar_file(filename: str):
    path = _avatar_dir() / secure_filename(filename)
    if not path.exists():
        return abort(404)
    return send_file(path)


@auth_bp.route("/auth/login", methods=["GET", "POST"])
def login() -> str | Response:
    if current_user():
        return redirect(url_for("overview"))

    form_data = {
        "email": normalize_email(str(request.form.get("email", ""))),
        "remember_me": _truthy(request.form.get("remember_me")),
    }
    next_path = _safe_next_path(request.args.get("next") or request.form.get("next") or session.get("pending_next"))
    if request.method == "POST":
        email = form_data["email"]
        password = str(request.form.get("password", ""))
        user = fetch_user_by_email(email)
        if not user or not verify_password(str(user["password_hash"]), password):
            flash("The email or password does not match our records. Verify both fields and try again, or reset your password if you need to recover access.", "error")
        elif int(user.get("is_active", 0)) != 1:
            flash("This account is inactive.", "error")
        else:
            session["pending_next"] = _safe_next_path(next_path)
            _set_pending_verification(int(user["id"]), form_data["remember_me"])
            flash("One quick human check and you're in.", "success")
            return redirect(url_for("auth.verify_human"))

    return render_template(
        "auth_login.html",
        active_page="auth",
        bootstrap_data={"page": "auth-login"},
        form_data=form_data,
        next_path=next_path,
    )


@auth_bp.route("/auth/signup", methods=["GET", "POST"])
def signup() -> str | Response:
    if current_user():
        return redirect(url_for("overview"))

    form_data = build_profile_form(request.form or {})
    form_data["email"] = normalize_email(str(request.form.get("email", "")))
    errors: Dict[str, str] = {}
    if request.method == "POST":
        profile, errors = validate_signup_form(request.form)
        form_data.update(profile)
        if not errors:
            create_user_and_profile(form_data["email"], str(request.form.get("password", "")), profile)
            flash("Your account is ready. Sign in and complete the human check to enter.", "success")
            return redirect(url_for("auth.login", next=url_for("overview")))

    return render_template(
        "auth_signup.html",
        active_page="auth",
        bootstrap_data={"page": "auth-signup"},
        form_data=form_data,
        form_errors=errors,
        password_strength=password_strength(str(request.form.get("password", ""))),
    )


@auth_bp.route("/auth/verify-human", methods=["GET", "POST"])
def verify_human() -> str | Response:
    pending_user = fetch_user_by_id(session.get("pending_user_id"))
    if not pending_user or not _pending_verification_valid():
        _clear_pending_verification()
        flash("Start with your email and password first.", "error")
        return redirect(url_for("auth.login"))

    profile = fetch_profile(int(pending_user["id"])) or {}
    if request.method == "POST":
        if request.form.get("action") == "refresh":
            _refresh_human_challenge()
            flash("Fresh challenge loaded.", "success")
            return redirect(url_for("auth.verify_human"))

        attempts = int(session.get("pending_human_attempts", 0)) + 1
        session["pending_human_attempts"] = attempts
        ok, message = validate_human_bundle(
            session.get("pending_human_answers", {}),
            str(request.form.get("scribble_code", "")),
            str(request.form.get("emoji_choice", "")),
        )
        if ok:
            redirect_target = session.get("pending_next") or url_for("overview")
            login_user(pending_user, remember_me=_truthy(session.get("pending_remember_me")))
            flash("Identity verified. We're preparing your workspace now.", "success")
            return redirect(url_for("buffer_page", next=redirect_target))
        if attempts >= MAX_VERIFY_ATTEMPTS:
            _refresh_human_challenge()
            flash("Too many misses. We refreshed the challenge for you.", "error")
        else:
            flash(message, "error")

    expires_at = session.get("pending_human_expires_at")
    seconds_left = max(0, int((datetime.fromisoformat(expires_at) - now_utc()).total_seconds())) if expires_at else 0
    return render_template(
        "auth_verify_human.html",
        active_page="auth",
        bootstrap_data={
            "page": "auth-verify-human",
            "human_payload": session.get("pending_human_payload", {}),
            "seconds_left": seconds_left,
        },
        pending_user=pending_user,
        pending_profile=profile,
        human_payload=session.get("pending_human_payload", {}),
        seconds_left=seconds_left,
        remember_me=_truthy(session.get("pending_remember_me")),
    )


@auth_bp.route("/auth/forgot-password", methods=["GET", "POST"])
def forgot_password() -> str | Response:
    form_data = {"email": normalize_email(str(request.form.get("email", "")))}
    if request.method == "POST":
        user = fetch_user_by_email(form_data["email"])
        if user:
            create_password_reset(user)
        flash("If that email exists, a reset link has been sent.", "success")
        return redirect(url_for("auth.login"))
    return render_template("auth_forgot_password.html", active_page="auth", bootstrap_data={"page": "auth-forgot-password"}, form_data=form_data)


@auth_bp.route("/auth/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token: str) -> str | Response:
    token_row = get_valid_reset_token(token)
    if not token_row:
        flash("That reset link is no longer valid.", "error")
        return redirect(url_for("auth.forgot_password"))
    user = fetch_user_by_id(int(token_row["user_id"]))
    profile = fetch_profile(int(token_row["user_id"])) or {}
    errors: Dict[str, str] = {}
    if request.method == "POST":
        password = str(request.form.get("password", ""))
        confirm_password = str(request.form.get("confirm_password", ""))
        valid_password, feedback = password_policy_feedback(
            password,
            email=str(user["email"]) if user else "",
            profile_values=[profile.get("first_name", ""), profile.get("last_name", ""), profile.get("display_name", ""), profile.get("organization", "")],
        )
        if not valid_password:
            errors["password"] = " ".join(feedback)
        if password != confirm_password:
            errors["confirm_password"] = "Passwords need to match."
        if not errors and user:
            complete_password_reset(token_row, password)
            flash("Password updated. Sign in to continue.", "success")
            return redirect(url_for("auth.login"))
    return render_template(
        "auth_reset_password.html",
        active_page="auth",
        bootstrap_data={"page": "auth-reset-password"},
        user=user,
        profile=profile,
        form_errors=errors,
        password_strength=password_strength(str(request.form.get("password", ""))),
    )


@auth_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile_page() -> str | Response:
    user = current_user()
    existing_profile = current_profile() or {}
    form_data = build_profile_form(request.form or {}, profile=existing_profile)
    form_data["email"] = user["email"] if user else ""
    form_data["public_user_id"] = user.get("public_user_id", "") if user else ""
    errors: Dict[str, str] = {}

    if request.method == "POST" and user:
        updated = build_profile_form(request.form, profile=existing_profile)
        form_data.update(updated)
        if not updated["first_name"]:
            errors["first_name"] = "First name is required."
        if not updated["last_name"]:
            errors["last_name"] = "Last name is required."
        if not updated["display_name"]:
            errors["display_name"] = "Add the name we should greet you with."
        avatar = request.files.get("avatar")
        if avatar and avatar.filename:
            try:
                updated["avatar_path"] = _save_avatar(avatar, int(user["id"]))
                form_data["avatar_path"] = updated["avatar_path"]
            except ValueError as exc:
                errors["avatar"] = str(exc)
        elif _truthy(request.form.get("remove_avatar")):
            updated["avatar_path"] = ""
            form_data["avatar_path"] = ""
        else:
            updated["avatar_path"] = existing_profile.get("avatar_path", "")
        if not errors:
            update_profile(int(user["id"]), updated)
            g.current_profile = fetch_profile(int(user["id"]))
            flash("Profile updated.", "success")
            return redirect(url_for("auth.profile_page"))

    return render_template(
        "profile.html",
        active_page="profile",
        bootstrap_data={"page": "profile"},
        form_data=form_data,
        form_errors=errors,
        avatar_url=_avatar_url(existing_profile),
    )


@auth_bp.route("/auth/logout", methods=["POST"])
def logout() -> Response:
    logout_user()
    flash("You've been signed out.", "success")
    return redirect(url_for("auth.login"))
