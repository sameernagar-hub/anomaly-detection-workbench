from __future__ import annotations

import json
import os
import secrets
import threading
import time
import uuid
from collections import Counter
from datetime import datetime
from functools import wraps
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple

from flask import Flask, Response, abort, flash, jsonify, redirect, render_template, request, send_file, url_for
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from auth import auth_bp, current_profile, current_user, login_required
from db import connect_db, get_db_path, init_db, load_json
from emailer import Mailer
from report_renderers import render_pdf, renderer_statuses
from reports import build_analysis_report, build_evaluation_report, build_live_report, empty_report, report_catalog
from workbench import DEFAULT_UPLOAD_TEXT, AnomalyWorkbench, LiveMonitor, load_records_from_file, load_records_from_text


app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.getenv("WORKBENCH_SECRET_KEY") or secrets.token_urlsafe(32),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.getenv("WORKBENCH_SECURE_COOKIE", "0") == "1",
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,
)

RUNTIME_DIR = BASE_DIR / "runtime"
RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
DEMO_RUNTIME_DIR = BASE_DIR / "demo_runtime"
DEMO_RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
SAMPLE_DIR = BASE_DIR / "sample_data"

database = connect_db(get_db_path(BASE_DIR))
init_db(database)
app.config["DB"] = database
app.config["MAILER"] = Mailer(RUNTIME_DIR)
app.config["RUNTIME_DIR"] = RUNTIME_DIR
app.register_blueprint(auth_bp)

MODEL_NAMES = {
    "baseline": {"label": "Baseline Sentinel", "subtitle": "Baseline sequence model"},
    "improved": {"label": "Apex Insight", "subtitle": "Improved argument-aware model"},
}
THEME_OPTIONS = {"campus", "midnight", "signal"}
FEEDBACK_CATEGORIES = {
    "question": "Platform question",
    "idea": "Improvement idea",
    "bug": "Bug report",
    "general": "General feedback",
}

SAMPLE_SCENARIOS = [
    {
        "id": "executive-brief",
        "filename": "executive_brief.log",
        "title": "Executive Brief",
        "eyebrow": "Balanced sample",
        "description": "A walkthrough trace with a clean opening, a reconnaissance burst, and enough volume to populate the main charts clearly.",
        "tags": ["balanced", "demo-ready", "compare"],
    },
    {
        "id": "recon-surge",
        "filename": "recon_surge.log",
        "title": "Recon Surge",
        "eyebrow": "Attack-heavy sample",
        "description": "A louder stream with repeated reconnaissance-style spikes that makes the improved model story easy to visualize.",
        "tags": ["attack", "high-signal", "live-demo"],
    },
    {
        "id": "night-shift",
        "filename": "night_shift.log",
        "title": "Night Shift Drift",
        "eyebrow": "Drift scenario",
        "description": "Starts quiet, shifts protocol mix, and ends with enough variance to show drift and adaptive-threshold behavior.",
        "tags": ["drift", "adaptive", "timeline"],
    },
    {
        "id": "disagreement-lab",
        "filename": "disagreement_lab.log",
        "title": "Disagreement Lab",
        "eyebrow": "Model comparison",
        "description": "A curated sequence that highlights disagreement windows, mixed labels, and metric deltas between the two models.",
        "tags": ["disagreement", "benchmark", "comparison"],
    },
]

workbench = AnomalyWorkbench(BASE_DIR)
BOOTSTRAP_STATUS: Dict[str, Any] = {"state": "starting", "message": "Preparing anomaly detection services...", "details": {}}
EVALUATION_CACHE: Dict[str, Any] = {"state": "idle", "message": "Evaluation snapshot has not run yet.", "updated_at": None, "benchmark": None}
BOOTSTRAP_LOCK = threading.Lock()
BOOTSTRAP_THREAD: Optional[threading.Thread] = None
EVALUATION_THREAD: Optional[threading.Thread] = None
USER_STATE_LOCK = threading.Lock()
USER_LIVE_MONITORS: Dict[int, LiveMonitor] = {}
USER_REPLAYS: Dict[int, "DemoReplay"] = {}
USER_LIVE_CONTEXT: Dict[int, Dict[str, Any]] = {}
RUN_LIMIT = 80
BUFFER_ROTATION_MESSAGES = [
    "Preparing your workbench services...",
    "Personalizing your environment...",
    "Loading anomaly detection models...",
    "Tuning your secure workspace session...",
]


def _scenario_path(sample_id: str) -> Path:
    for scenario in SAMPLE_SCENARIOS:
        if scenario["id"] == sample_id:
            return SAMPLE_DIR / scenario["filename"]
    raise KeyError(f"Unknown scenario '{sample_id}'")


def _scenario_meta(sample_id: str) -> Dict[str, Any]:
    for scenario in SAMPLE_SCENARIOS:
        if scenario["id"] == sample_id:
            path = SAMPLE_DIR / scenario["filename"]
            line_count = len(path.read_text(encoding="utf-8", errors="ignore").splitlines()) if path.exists() else 0
            return {**scenario, "path": str(path.resolve()), "line_count": line_count}
    raise KeyError(f"Unknown scenario '{sample_id}'")


def _scenario_title_by_filename(filename: str) -> Optional[str]:
    for scenario in SAMPLE_SCENARIOS:
        if scenario["filename"] == filename:
            return str(scenario["title"])
    return None


def demo_catalog() -> List[Dict[str, Any]]:
    return [_scenario_meta(scenario["id"]) for scenario in SAMPLE_SCENARIOS]


def _timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _empty_result() -> Dict[str, Any]:
    return {"summary": {}, "items": [], "charts": {}}


def _summary_for(result: Dict[str, Any]) -> Dict[str, Any]:
    return dict((result or {}).get("summary") or {})


def _db():
    return app.config["DB"]


def _user_upload_dir(user_id: int) -> Path:
    path = UPLOAD_DIR / f"user_{user_id}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _row_to_feedback(row: Any) -> Dict[str, Any]:
    record = dict(row)
    return {
        "id": record["feedback_key"],
        "category": record["category"],
        "category_label": FEEDBACK_CATEGORIES.get(record["category"], "Feedback"),
        "overall_rating": record["overall_rating"],
        "usability_rating": record["usability_rating"],
        "visual_rating": record["visual_rating"],
        "clarity_rating": record["clarity_rating"],
        "title": record["title"],
        "message": record["message"],
        "question": record["question"],
        "created_at": record["created_at"],
    }


def _row_to_run(row: Any) -> Dict[str, Any]:
    run = dict(row)
    return {
        "id": run["run_key"],
        "source": run["source"],
        "filename": run["filename"],
        "created_at": run["created_at"],
        "mode": run["mode"],
        "summary": load_json(run["summary_json"], {}),
        "result": load_json(run["result_json"], _empty_result()),
        "metadata": load_json(run["metadata_json"], {}),
    }


def _display_run_name(run: Optional[Dict[str, Any]]) -> str:
    if not run:
        return "No report yet"
    filename = str(run.get("filename") or "").strip()
    if not filename:
        return "No report yet"
    if run.get("source") == "scenario":
        metadata = run.get("metadata") or {}
        sample_id = str(metadata.get("sample_id") or "").strip()
        if sample_id:
            try:
                return str(_scenario_meta(sample_id)["title"])
            except KeyError:
                pass
        scenario_title = _scenario_title_by_filename(filename)
        if scenario_title:
            return scenario_title
        return Path(filename).stem.replace("_", " ").strip().title() or filename
    return filename


def _run_summary(run: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": run["id"],
        "source": run["source"],
        "filename": run["filename"],
        "display_name": _display_run_name(run),
        "created_at": run["created_at"],
        "mode": run["mode"],
        "summary": run.get("summary", {}),
        "metadata": run.get("metadata", {}),
        "detail_url": url_for("run_detail", run_id=run["id"]),
    }


def _pct_text(value: Any) -> str:
    try:
        return f"{round(float(value) * 100)}%"
    except (TypeError, ValueError):
        return "-"


def _score_text(value: Any, digits: int = 3) -> str:
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return "-"


def _ranked_counts(items: List[Dict[str, Any]], key: str, *, limit: int = 3, anomaly_only: bool = False) -> List[Tuple[str, int]]:
    counter: Counter[str] = Counter()
    for item in items:
        if anomaly_only and not (int(item.get("deeplog_prediction") or 0) == 1 or int(item.get("report_prediction") or 0) == 1):
            continue
        value = str(item.get(key) or "unknown").strip() or "unknown"
        counter[value] += 1
    return counter.most_common(limit)


def _build_run_recommendations(run: Dict[str, Any]) -> Dict[str, Any]:
    summary = dict(run.get("summary") or {})
    result = dict(run.get("result") or {})
    metadata = dict(run.get("metadata") or {})
    items = list(result.get("items") or [])
    window_count = int(summary.get("window_count") or 0)
    report_anomalies = int(summary.get("report_anomalies") or 0)
    baseline_anomalies = int(summary.get("deeplog_anomalies") or 0)
    agreement_rate = float(summary.get("agreement_rate") or 0.0)
    disagreement_rate = max(0.0, 1.0 - agreement_rate)
    anomaly_rate = (report_anomalies / window_count) if window_count else 0.0
    drift = dict(summary.get("drift") or {})
    drift_status = str(drift.get("status") or "n/a")
    report_accuracy = summary.get("report_vs_label_accuracy")
    baseline_accuracy = summary.get("deep_vs_label_accuracy")
    labeled_windows = int(summary.get("labeled_windows") or 0)

    anomaly_hosts = _ranked_counts(items, "host_group", anomaly_only=True)
    anomaly_events = _ranked_counts(items, "event", anomaly_only=True)
    attack_categories = _ranked_counts(items, "attack_cat", anomaly_only=True)

    top_host, top_host_count = anomaly_hosts[0] if anomaly_hosts else ("none", 0)
    top_event, top_event_count = anomaly_events[0] if anomaly_events else ("none", 0)
    host_share = (top_host_count / report_anomalies) if report_anomalies else 0.0
    event_share = (top_event_count / report_anomalies) if report_anomalies else 0.0

    display_name = str(run.get("display_name") or run.get("filename") or "this run")
    source = str(run.get("source") or "run")

    priorities: List[Dict[str, Any]] = []
    immediate_actions: List[str] = []
    prevention_actions: List[str] = []
    watch_items: List[str] = []
    meaning_points: List[str] = []

    if report_anomalies == 0 and baseline_anomalies == 0:
        meaning_points.append(
            f"{display_name} looks operationally calm: neither model is surfacing a meaningful anomaly cluster in the saved window set."
        )
        immediate_actions.append("Keep this run as a clean baseline reference and compare future suspicious uploads or live sessions against it.")
        prevention_actions.append("Preserve the same source formatting and collection path so future drift checks have a stable comparison point.")
        watch_items.append("If later runs show anomalies on the same source, compare host groups and event tokens first to isolate what changed.")
    else:
        meaning_points.append(
            f"{display_name} contains {report_anomalies} Apex Insight anomaly calls across {window_count} windows, which is {_pct_text(anomaly_rate)} of the saved timeline."
        )

    if anomaly_rate >= 0.35 or report_anomalies >= 12:
        priorities.append(
            {
                "priority": "High",
                "title": "Anomaly volume is elevated",
                "summary": "This run is showing a broad anomaly footprint rather than an isolated outlier.",
                "meaning": f"Apex Insight is flagging {_pct_text(anomaly_rate)} of the run. That usually means either a sustained suspicious pattern, a changed environment, or a noisy ingestion source.",
                "actions": [
                    "Filter the evidence table to `Any anomaly` and inspect the first concentrated burst rather than reading the run top to bottom.",
                    "Check whether the flagged windows cluster around one host group, one event token, or one short time span.",
                    "If this source is expected to be stable, treat this as an operational incident until proven otherwise.",
                ],
                "signals": [
                    f"Apex anomalies: {report_anomalies}",
                    f"Baseline anomalies: {baseline_anomalies}",
                    f"Anomaly share: {_pct_text(anomaly_rate)}",
                ],
            }
        )
        immediate_actions.append("Treat the run as a cluster problem, not a single-row problem: start with concentrated hosts/events, then validate whether the pattern is expected.")
        watch_items.append("Monitor whether the anomaly share keeps rising in later runs or live monitoring sessions.")

    if drift_status in {"watch", "drifting"}:
        priorities.append(
            {
                "priority": "High" if drift_status == "drifting" else "Medium",
                "title": "Behavior shifted during the run",
                "summary": "The run is not just anomalous; its recent behavior moved away from the earlier portion of the same stream.",
                "meaning": f"Drift posture is `{drift_status}` with score shift {_score_text(drift.get('score_shift'))}, anomaly-rate shift {_score_text(drift.get('anomaly_rate_shift'))}, and protocol shift {_score_text(drift.get('protocol_shift'))}.",
                "actions": [
                    "Compare the earlier and later halves of the timeline to find the exact point where score behavior changed.",
                    "Check whether protocol mix, service mix, or log source conditions changed around that point.",
                    "If the environment was intentionally changed, capture that as context so future runs do not look unexplained.",
                ],
                "signals": [
                    f"Drift posture: {drift_status}",
                    f"Score shift: {_score_text(drift.get('score_shift'))}",
                    f"Protocol shift: {_score_text(drift.get('protocol_shift'))}",
                ],
            }
        )
        meaning_points.append("The analytics suggest the run changed character midstream, so the important question is what changed and when, not only how many anomalies were produced.")
        immediate_actions.append("Use the saved timeline to locate the transition point where scores begin to lift, then inspect nearby evidence rows for the first repeated changed pattern.")
        prevention_actions.append("Record deployment changes, traffic shifts, or parser changes near the drift point so future anomaly runs can be interpreted faster.")

    if disagreement_rate >= 0.22:
        priorities.append(
            {
                "priority": "Medium",
                "title": "The two models disagree often",
                "summary": "This run needs analyst review because the baseline and improved model are not telling the same story.",
                "meaning": f"Agreement is only {_pct_text(agreement_rate)}, so disagreement windows are likely where the strongest analyst signal lives.",
                "actions": [
                    "Filter the evidence table to `Disagreements only` and review which event types are being split between the models.",
                    "Use disagreement windows to identify whether the baseline is missing structured context or the improved model is being more sensitive than expected.",
                    "If one model consistently flags a host/event family the other ignores, treat that pattern as a review lane of its own.",
                ],
                "signals": [
                    f"Agreement: {_pct_text(agreement_rate)}",
                    f"Disagreement share: {_pct_text(disagreement_rate)}",
                ],
            }
        )
        meaning_points.append("Model disagreement usually means the run contains borderline or context-sensitive behavior, which is exactly where human review adds the most value.")
        watch_items.append("Watch whether future runs show the same disagreement family. Repeated disagreement on the same token/host usually means the source deserves targeted tuning.")

    if host_share >= 0.45 and top_host != "none":
        priorities.append(
            {
                "priority": "High",
                "title": "Anomalies are concentrated in one host group",
                "summary": "The issue may be localized rather than system-wide.",
                "meaning": f"The leading host group `{top_host}` accounts for {_pct_text(host_share)} of anomaly windows, which strongly suggests a focused source of instability or suspicious behavior.",
                "actions": [
                    f"Filter the evidence table to host group `{top_host}` first.",
                    "Compare whether the same host is also driving disagreement, drift, or repeated event patterns.",
                    "If this host group maps to one device, service, or environment, validate configuration changes and traffic expectations there before widening the investigation.",
                ],
                "signals": [
                    f"Top host group: {top_host}",
                    f"Host share of anomalies: {_pct_text(host_share)}",
                ],
            }
        )
        immediate_actions.append(f"Start with host group `{top_host}`. The analytics suggest that is the fastest path to root cause.")
        prevention_actions.append(f"If `{top_host}` is a known environment, improve source-specific baselining or collection hygiene there first.")

    if event_share >= 0.35 and top_event != "none":
        priorities.append(
            {
                "priority": "Medium",
                "title": "A repeated event pattern is driving the run",
                "summary": "One event signature is doing a large share of the anomaly work.",
                "meaning": f"The event pattern `{top_event}` appears in {_pct_text(event_share)} of anomaly windows, which often points to one recurring workflow, parser edge case, or attack sequence.",
                "actions": [
                    f"Search the evidence rows for `{top_event}` and review whether the surrounding raw lines have the same operational story.",
                    "Decide whether the pattern is malicious, misconfigured, or simply a valid workflow that the baseline does not yet understand.",
                    "If valid, consider normalizing or baselining this pattern rather than repeatedly re-investigating it.",
                ],
                "signals": [
                    f"Top event signature: {top_event}",
                    f"Event share of anomalies: {_pct_text(event_share)}",
                ],
            }
        )
        prevention_actions.append(f"If `{top_event}` is legitimate traffic, normalize that event family or adjust baselining so it stops generating repetitive investigation cost.")

    if labeled_windows and report_accuracy is not None and baseline_accuracy is not None and float(report_accuracy) > float(baseline_accuracy):
        priorities.append(
            {
                "priority": "Medium",
                "title": "The improved model is adding useful signal",
                "summary": "This run suggests the argument-aware model is the more trustworthy guide.",
                "meaning": f"Apex Insight accuracy is {_score_text(report_accuracy)} versus {_score_text(baseline_accuracy)} for the baseline on labeled windows.",
                "actions": [
                    "When reviewing this run, give extra attention to windows that only the improved model flags.",
                    "Use the improved-model evidence as the primary explanation path in your report or export summary.",
                    "If the baseline underperforms repeatedly on similar runs, treat that as a reason to rely less on single-sequence-only interpretation.",
                ],
                "signals": [
                    f"Apex accuracy: {_score_text(report_accuracy)}",
                    f"Baseline accuracy: {_score_text(baseline_accuracy)}",
                    f"Labeled windows: {labeled_windows}",
                ],
            }
        )
        meaning_points.append("On this run, the argument-aware model appears to be extracting more reliable context than the baseline alone.")

    if attack_categories:
        attack_name, attack_count = attack_categories[0]
        watch_items.append(f"The strongest saved attack category signal is `{attack_name}` across {attack_count} anomaly windows. Use that as a working hypothesis, not a final verdict.")

    if source in {"upload", "text"}:
        prevention_actions.append("If the source came from manual upload or pasted text, standardize formatting and token consistency before the next run to reduce parser-driven noise.")
    if "saved_path" in metadata:
        watch_items.append("Because this run came from a saved file path, compare later runs from the same path to see whether the anomaly family is persistent or one-off.")

    if not priorities:
        priorities.append(
            {
                "priority": "Medium",
                "title": "Use this run as a review baseline",
                "summary": "There is enough information here to guide follow-up, but no single dominant risk pattern is overwhelming the run.",
                "meaning": "The strongest value is comparative: use host, event, and disagreement filters to establish what is normal for this source and what meaningfully deviates later.",
                "actions": [
                    "Review the highest-score windows first.",
                    "Check whether anomalies cluster by host or event family.",
                    "Save a PDF report for comparison against future runs from the same source.",
                ],
                "signals": [
                    f"Windows analyzed: {window_count}",
                    f"Agreement: {_pct_text(agreement_rate)}",
                    f"Drift posture: {drift_status}",
                ],
            }
        )

    priority_weight = {"High": 0, "Medium": 1, "Low": 2}
    priorities = sorted(priorities, key=lambda entry: priority_weight.get(entry["priority"], 3))[:4]

    overview = " ".join(meaning_points[:3]).strip() or "This archived run is ready for guided review."
    return {
        "headline": priorities[0]["title"] if priorities else "Guided review available",
        "overview": overview,
        "priorities": priorities,
        "tabs": [
            {
                "id": "meaning",
                "label": "Meaning",
                "intro": "What the analytics are telling you about this run.",
                "items": meaning_points or ["Use the anomaly counts, agreement, and drift posture together rather than in isolation."],
            },
            {
                "id": "immediate",
                "label": "Immediate Actions",
                "intro": "Practical next steps to move from detection into investigation.",
                "items": immediate_actions[:5] or ["Start with anomaly-heavy windows and narrow by host group or disagreement first."],
            },
            {
                "id": "prevention",
                "label": "Prevention",
                "intro": "What could reduce repeat anomalies or shorten future investigations.",
                "items": prevention_actions[:5] or ["Capture source context and normalize recurring benign patterns so future runs are easier to interpret."],
            },
            {
                "id": "watch",
                "label": "Watch Next",
                "intro": "Signals worth monitoring in the next run or live session.",
                "items": watch_items[:5] or ["Watch whether the same host group, event token, or disagreement pattern returns in future runs."],
            },
        ],
    }


def _list_runs(user_id: int) -> List[Dict[str, Any]]:
    rows = _db().execute(
        "SELECT * FROM user_runs WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
        (user_id, RUN_LIMIT),
    ).fetchall()
    return [_run_summary(_row_to_run(row)) for row in rows]


def _list_feedback(user_id: int, limit: int = 30) -> List[Dict[str, Any]]:
    rows = _db().execute(
        "SELECT * FROM feedback_records WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()
    return [_row_to_feedback(row) for row in rows]


def _store_feedback(user_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    feedback_key = f"FDBK-{uuid.uuid4().hex[:8].upper()}"
    created_at = _timestamp()
    _db().execute(
        """
        INSERT INTO feedback_records (
            user_id, feedback_key, category, overall_rating, usability_rating, visual_rating, clarity_rating,
            title, message, question, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            feedback_key,
            payload["category"],
            payload["overall_rating"],
            payload["usability_rating"],
            payload["visual_rating"],
            payload["clarity_rating"],
            payload["title"],
            payload["message"],
            payload.get("question", ""),
            created_at,
        ),
    )
    _db().commit()
    row = _db().execute(
        "SELECT * FROM feedback_records WHERE user_id = ? AND feedback_key = ?",
        (user_id, feedback_key),
    ).fetchone()
    return _row_to_feedback(row)


def _current_run(user_id: int) -> Optional[Dict[str, Any]]:
    row = _db().execute(
        "SELECT * FROM user_runs WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
        (user_id,),
    ).fetchone()
    return _row_to_run(row) if row else None


def _store_run(user_id: int, source: str, filename: str, mode: str, result: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    run_key = uuid.uuid4().hex[:10]
    payload = {
        "summary_json": json.dumps(_summary_for(result)),
        "result_json": json.dumps(result),
        "metadata_json": json.dumps(metadata or {}),
    }
    _db().execute(
        """
        INSERT INTO user_runs (user_id, run_key, source, filename, created_at, mode, summary_json, result_json, metadata_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (user_id, run_key, source, filename, _timestamp(), mode, payload["summary_json"], payload["result_json"], payload["metadata_json"]),
    )
    _db().commit()
    return _run_by_id(user_id, run_key)


def _run_by_id(user_id: int, run_id: str) -> Dict[str, Any]:
    row = _db().execute(
        "SELECT * FROM user_runs WHERE user_id = ? AND run_key = ?",
        (user_id, run_id),
    ).fetchone()
    if row is None:
        abort(404, description=f"Run '{run_id}' was not found.")
    return _row_to_run(row)


def _selected_run(user_id: int, run_id: Optional[str]) -> Dict[str, Any]:
    if run_id:
        return _run_by_id(user_id, run_id)
    run = _current_run(user_id)
    if run:
        return run
    return {
        "id": None,
        "source": "none",
        "filename": "No report yet",
        "created_at": None,
        "mode": "compare",
        "summary": {},
        "result": _empty_result(),
        "metadata": {},
    }


def _run_filename(run: Dict[str, Any], extension: str) -> str:
    stem = Path(run.get("filename") or "anomaly_report").stem
    mode = run.get("mode", "compare")
    return f"{stem}_{mode}.{extension}"


def _persist_analysis(user_id: int, source: str, filename: str, mode: str, result: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    user = current_user() or {}
    profile = current_profile() or {}
    enriched = dict(metadata or {})
    enriched.setdefault("public_user_id", user.get("public_user_id"))
    enriched.setdefault("display_name", profile.get("display_name"))
    return _store_run(user_id, source, filename, mode, result, enriched)


def _user_bootstrap(page: str, extras: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    featured = _scenario_meta("executive-brief")
    user = current_user()
    profile = current_profile()
    current_run = _current_run(int(user["id"])) if user else None
    payload = {
        "page": page,
        "sample_text": Path(featured["path"]).read_text(encoding="utf-8", errors="ignore"),
        "sample_catalog": demo_catalog(),
        "model_names": MODEL_NAMES,
        "featured_sample": featured,
        "default_upload_text": DEFAULT_UPLOAD_TEXT,
        "current_run_id": current_run["id"] if current_run else None,
        "current_user": {
            "email": user["email"],
            "display_name": (profile or {}).get("display_name"),
            "full_name": (profile or {}).get("full_name"),
            "public_user_id": user.get("public_user_id"),
        } if user else None,
        "preferences": {
            "theme": (profile or {}).get("preferred_theme", "campus"),
            "analysis_mode": (profile or {}).get("preferred_analysis_mode", "compare"),
            "live_trace_os": (profile or {}).get("live_trace_os_preference", "Windows"),
        },
        "theme_options": sorted(THEME_OPTIONS),
        "feedback_categories": FEEDBACK_CATEGORIES,
    }
    if extras:
        payload.update(extras)
    return payload


def _build_benchmark_payload() -> Dict[str, Any]:
    train_normal, test_normal, test_attack = workbench._training_records()
    evaluation_records = test_normal + test_attack
    result = workbench.predict_records(evaluation_records)
    cross_host = workbench.evaluate_cross_host_proxy()

    summary = result["summary"]
    baseline_metrics = summary.get("deeplog_metrics", {})
    improved_metrics = summary.get("report_metrics", {})
    metric_names = ("accuracy", "precision", "recall", "f1", "false_positive_rate")
    metric_rows = []
    improved_wins = 0
    for metric_name in metric_names:
        baseline_value = baseline_metrics.get(metric_name)
        improved_value = improved_metrics.get(metric_name)
        delta = None
        if baseline_value is not None and improved_value is not None:
            delta = round(float(improved_value) - float(baseline_value), 3)
            if metric_name == "false_positive_rate":
                if improved_value < baseline_value:
                    improved_wins += 1
            elif improved_value > baseline_value:
                improved_wins += 1
        metric_rows.append({"metric": metric_name, "baseline": baseline_value, "improved": improved_value, "delta": delta})

    folds = cross_host.get("folds", [])
    baseline_cross = [fold.get("deeplog_accuracy") for fold in folds if fold.get("deeplog_accuracy") is not None]
    improved_cross = [fold.get("report_accuracy") for fold in folds if fold.get("report_accuracy") is not None]
    cross_summary = {
        "fold_count": len(folds),
        "baseline_avg_accuracy": round(sum(baseline_cross) / len(baseline_cross), 3) if baseline_cross else None,
        "improved_avg_accuracy": round(sum(improved_cross) / len(improved_cross), 3) if improved_cross else None,
    }
    cross_summary["delta"] = (
        round(cross_summary["improved_avg_accuracy"] - cross_summary["baseline_avg_accuracy"], 3)
        if cross_summary["baseline_avg_accuracy"] is not None and cross_summary["improved_avg_accuracy"] is not None
        else None
    )

    headline = {
        "window_count": summary.get("window_count", 0),
        "labeled_windows": summary.get("labeled_windows", 0),
        "improved_wins": improved_wins,
        "metric_count": len(metric_rows),
        "agreement_rate": summary.get("agreement_rate", 0.0),
        "baseline_anomalies": summary.get("deeplog_anomalies", 0),
        "improved_anomalies": summary.get("report_anomalies", 0),
        "baseline_accuracy": summary.get("deep_vs_label_accuracy"),
        "improved_accuracy": summary.get("report_vs_label_accuracy"),
    }

    return {
        "standard": {"summary": summary, "metric_rows": metric_rows},
        "cross_host": {"note": cross_host.get("note"), "summary": cross_summary, "folds": folds},
        "headline": headline,
    }


def _report_renderer_statuses() -> Dict[str, Dict[str, Any]]:
    return renderer_statuses()


def _report_preview_context(user_id: int) -> Dict[str, Any]:
    live_monitor, _ = _user_services(user_id)
    return {
        "runs": _list_runs(user_id),
        "evaluation_cache": dict(EVALUATION_CACHE),
        "live_status": live_monitor.status(),
        "live_context": dict(USER_LIVE_CONTEXT.get(user_id, {})),
        "renderers": _report_renderer_statuses(),
    }


def _resolve_report_payload(user_id: int, report_type: str, source_id: Optional[str], theme: str, renderer: str) -> Dict[str, Any]:
    preview_context = _report_preview_context(user_id)
    if report_type == "analysis":
        run_id = source_id or (_current_run(user_id) or {}).get("id")
        if not run_id:
            return empty_report("analysis", "Analysis Report", "No saved run is available yet. Analyze text, upload a file, or save a live session first.", theme=theme, renderer=renderer)
        run = _run_by_id(user_id, str(run_id))
        return build_analysis_report(run, MODEL_NAMES, theme=theme, renderer=renderer)
    if report_type == "evaluation":
        ensure_evaluation_started()
        if EVALUATION_CACHE.get("state") != "ready" or not EVALUATION_CACHE.get("benchmark"):
            return empty_report("evaluation", "Evaluation Report", EVALUATION_CACHE.get("message", "Evaluation snapshot is still warming up."), theme=theme, renderer=renderer)
        return build_evaluation_report(dict(EVALUATION_CACHE), MODEL_NAMES, theme=theme, renderer=renderer)
    if report_type == "live":
        live_status = preview_context["live_status"]
        if not live_status.get("result"):
            return empty_report("live", "Live Monitor Report", "The live monitor does not have a result yet. Start a replay or follow a file to generate a live snapshot.", theme=theme, renderer=renderer)
        return build_live_report(live_status, preview_context["live_context"], MODEL_NAMES, theme=theme, renderer=renderer)
    raise ValueError(f"Unsupported report type '{report_type}'.")


def _refresh_evaluation_cache() -> None:
    global EVALUATION_THREAD
    try:
        EVALUATION_CACHE["state"] = "running"
        EVALUATION_CACHE["message"] = "Computing benchmark metrics and cross-host proxy results..."
        EVALUATION_CACHE["benchmark"] = _build_benchmark_payload()
        EVALUATION_CACHE["state"] = "ready"
        EVALUATION_CACHE["message"] = "Benchmark snapshot ready."
        EVALUATION_CACHE["updated_at"] = _timestamp()
    except Exception as exc:
        EVALUATION_CACHE["state"] = "error"
        EVALUATION_CACHE["message"] = str(exc)
    finally:
        EVALUATION_THREAD = None


def ensure_evaluation_started() -> None:
    global EVALUATION_THREAD
    if EVALUATION_CACHE["state"] in {"running", "ready"}:
        return
    if EVALUATION_THREAD is not None and EVALUATION_THREAD.is_alive():
        return
    EVALUATION_THREAD = threading.Thread(target=_refresh_evaluation_cache, daemon=True)
    EVALUATION_THREAD.start()


def bootstrap_models() -> None:
    try:
        details = workbench.ensure_ready()
        BOOTSTRAP_STATUS["state"] = "ready"
        BOOTSTRAP_STATUS["message"] = "Models are warm and the workbench is ready."
        BOOTSTRAP_STATUS["details"] = details
        ensure_evaluation_started()
    except Exception as exc:
        BOOTSTRAP_STATUS["state"] = "error"
        BOOTSTRAP_STATUS["message"] = str(exc)


def ensure_bootstrap_started() -> None:
    global BOOTSTRAP_THREAD
    with BOOTSTRAP_LOCK:
        if BOOTSTRAP_THREAD is not None and BOOTSTRAP_THREAD.is_alive():
            return
        if BOOTSTRAP_STATUS["state"] == "ready":
            return
        BOOTSTRAP_STATUS["state"] = "starting"
        BOOTSTRAP_STATUS["message"] = "Preparing your workbench and loading detection services..."
        BOOTSTRAP_THREAD = threading.Thread(target=bootstrap_models, daemon=True)
        BOOTSTRAP_THREAD.start()


def _normalized_next_path(candidate: Optional[str]) -> str:
    value = str(candidate or "").strip()
    if not value or not value.startswith("/") or value.startswith("//"):
        return url_for("overview")
    if value.startswith("/auth/") or value.startswith("/workspace-buffer"):
        return url_for("overview")
    return value


def _request_wants_json() -> bool:
    accept = request.headers.get("Accept", "")
    return request.path.startswith("/api/") or "application/json" in accept


def workbench_ready_required(view):
    @wraps(view)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        if BOOTSTRAP_STATUS.get("state") == "ready":
            return view(*args, **kwargs)
        next_path = _normalized_next_path(request.full_path if request.query_string else request.path)
        if _request_wants_json():
            return jsonify({
                "error": "The workbench is still preparing your environment.",
                "bootstrap": BOOTSTRAP_STATUS,
                "redirect": url_for("buffer_page", next=next_path),
            }), 503
        return redirect(url_for("buffer_page", next=next_path))

    return wrapped


def apply_mode_filter(result: Dict[str, Any], mode: str) -> Dict[str, Any]:
    if mode == "compare":
        result["summary"]["active_model"] = "Dual Command View"
        return result
    filtered_items = []
    for item in result["items"]:
        current = dict(item)
        if mode == "deeplog":
            current["report_prediction"] = None
            current["report_score"] = None
            current["agreement"] = None
        elif mode == "report":
            current["deeplog_prediction"] = None
            current["deeplog_score"] = None
            current["deeplog_top_matches"] = []
            current["agreement"] = None
        filtered_items.append(current)
    filtered_summary = dict(result["summary"])
    filtered_summary["active_model"] = MODEL_NAMES["baseline"]["label"] if mode == "deeplog" else MODEL_NAMES["improved"]["label"] if mode == "report" else "Dual Command View"
    return {"summary": filtered_summary, "items": filtered_items, "charts": result["charts"]}


class DemoReplay:
    def __init__(self, live_monitor_: LiveMonitor, runtime_suffix: str) -> None:
        self.live_monitor = live_monitor_
        self.runtime_suffix = runtime_suffix
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._status: Dict[str, Any] = {
            "state": "idle",
            "sample_id": None,
            "target_path": None,
            "appended_lines": 0,
            "total_lines": 0,
            "updated_at": None,
            "message": "Replay idle.",
        }

    def start(self, sample_id: str, interval: float = 0.45) -> Dict[str, Any]:
        source_path = _scenario_path(sample_id)
        target_path = DEMO_RUNTIME_DIR / f"{sample_id}_{self.runtime_suffix}_live.log"
        self.stop(stop_live=False)
        target_path.write_text("", encoding="utf-8")
        self._stop.clear()
        self._status = {
            "state": "starting",
            "sample_id": sample_id,
            "target_path": str(target_path.resolve()),
            "appended_lines": 0,
            "total_lines": 0,
            "updated_at": _timestamp(),
            "message": f"Preparing replay from {source_path.name}.",
        }
        self.live_monitor.start(str(target_path))
        self._thread = threading.Thread(target=self._run, args=(sample_id, source_path, target_path, interval), daemon=True)
        self._thread.start()
        return self.status()

    def stop(self, stop_live: bool = True) -> Dict[str, Any]:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._thread = None
        if stop_live:
            self.live_monitor.stop()
        if self._status["state"] not in {"complete", "idle"}:
            self._status["state"] = "stopped"
            self._status["message"] = "Replay stopped."
            self._status["updated_at"] = _timestamp()
        return self.status()

    def status(self) -> Dict[str, Any]:
        return dict(self._status)

    def _run(self, sample_id: str, source_path: Path, target_path: Path, interval: float) -> None:
        lines = source_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        self._status["state"] = "running"
        self._status["total_lines"] = len(lines)
        self._status["message"] = f"Streaming {source_path.name} into live monitor."
        for index, line in enumerate(lines, start=1):
            if self._stop.is_set():
                return
            with target_path.open("a", encoding="utf-8") as outfile:
                outfile.write(f"{line}\n")
            self._status["sample_id"] = sample_id
            self._status["appended_lines"] = index
            self._status["updated_at"] = _timestamp()
            self._status["message"] = f"Streaming live demo line {index} of {len(lines)}."
            time.sleep(interval)
        self._status["state"] = "complete"
        self._status["updated_at"] = _timestamp()
        self._status["message"] = "Replay complete. Live monitor will keep the final stream loaded."


def _user_services(user_id: int) -> Tuple[LiveMonitor, DemoReplay]:
    with USER_STATE_LOCK:
        live_monitor = USER_LIVE_MONITORS.get(user_id)
        replay = USER_REPLAYS.get(user_id)
        if live_monitor is None:
            live_monitor = LiveMonitor(workbench)
            USER_LIVE_MONITORS[user_id] = live_monitor
        if replay is None:
            replay = DemoReplay(live_monitor, runtime_suffix=f"user_{user_id}")
            USER_REPLAYS[user_id] = replay
        return live_monitor, replay


def project_status(user_id: int) -> Dict[str, Any]:
    current_run = _current_run(user_id)
    live_monitor, replay = _user_services(user_id)
    live_context = USER_LIVE_CONTEXT.get(user_id, {})
    return {
        "bootstrap": BOOTSTRAP_STATUS,
        "artifacts": {
            "baseline_model": str(workbench.baseline_artifact_path),
            "report_model": str(workbench.report_model_path),
        },
        "adaptive": workbench.get_adaptive_status(),
        "live": live_monitor.status(),
        "replay": replay.status(),
        "recent_runs": _list_runs(user_id),
        "recent_feedback": _list_feedback(user_id, limit=6),
        "current_run": _run_summary(current_run) if current_run else None,
        "current_result": current_run["result"] if current_run else None,
        "model_names": MODEL_NAMES,
        "evaluation": {"state": EVALUATION_CACHE["state"], "message": EVALUATION_CACHE["message"], "updated_at": EVALUATION_CACHE["updated_at"]},
        "user": {
            "email": current_user()["email"] if current_user() else None,
            "display_name": (current_profile() or {}).get("display_name"),
            "preferred_theme": (current_profile() or {}).get("preferred_theme"),
            "public_user_id": current_user().get("public_user_id") if current_user() else None,
        },
        "live_context": live_context,
    }


@app.route("/")
def home() -> Response:
    if not current_user():
        return redirect(url_for("auth.login"))
    if BOOTSTRAP_STATUS.get("state") != "ready":
        return redirect(url_for("buffer_page"))
    return redirect(url_for("overview"))


@app.route("/workspace-buffer")
@login_required
def buffer_page() -> str | Response:
    next_path = _normalized_next_path(request.args.get("next"))
    if BOOTSTRAP_STATUS.get("state") == "ready":
        return redirect(next_path)
    ensure_bootstrap_started()
    return render_template(
        "buffer.html",
        active_page="buffer",
        bootstrap_data=_user_bootstrap("buffer", {"buffer": {"next_path": next_path, "messages": BUFFER_ROTATION_MESSAGES}}),
        next_path=next_path,
        buffer_messages=BUFFER_ROTATION_MESSAGES,
        bootstrap_state=BOOTSTRAP_STATUS,
    )


@app.route("/overview")
@login_required
@workbench_ready_required
def overview() -> str:
    return render_template("overview.html", active_page="overview", bootstrap_data=_user_bootstrap("overview"))


@app.route("/analyze")
@login_required
@workbench_ready_required
def analyze_page() -> str:
    return render_template("analyze.html", active_page="analyze", bootstrap_data=_user_bootstrap("analyze"))


@app.route("/live")
@login_required
@workbench_ready_required
def live_page() -> str:
    return render_template("live.html", active_page="live", bootstrap_data=_user_bootstrap("live"))


@app.route("/evaluation")
@login_required
@workbench_ready_required
def evaluation_page() -> str:
    return render_template("evaluation.html", active_page="evaluation", bootstrap_data=_user_bootstrap("evaluation"))


@app.route("/reports")
@login_required
@workbench_ready_required
def reports_page() -> str:
    user = current_user()
    report_type = str(request.args.get("report_type", "analysis")).strip() or "analysis"
    source_id = str(request.args.get("source_id") or request.args.get("run_id") or "").strip()
    renderer = str(request.args.get("renderer", "weasyprint")).strip() or "weasyprint"
    return render_template(
        "reports.html",
        active_page="reports",
        bootstrap_data=_user_bootstrap(
            "reports",
            {
                "report_defaults": {"report_type": report_type, "source_id": source_id, "renderer": renderer},
                "report_renderers": _report_renderer_statuses(),
                "report_catalog": report_catalog(**_report_preview_context(int(user["id"]))),
            },
        ),
    )


@app.route("/reports/preview")
@login_required
@workbench_ready_required
def reports_preview() -> Response:
    user = current_user()
    report_type = str(request.args.get("report_type", "analysis")).strip() or "analysis"
    source_id = str(request.args.get("source_id") or request.args.get("run_id") or "").strip() or None
    renderer = str(request.args.get("renderer", "weasyprint")).strip() or "weasyprint"
    theme = str(request.args.get("theme", (current_profile() or {}).get("preferred_theme", "campus"))).strip() or "campus"
    renderers = _report_renderer_statuses()
    if renderer not in renderers:
        return jsonify({"error": f"Unsupported renderer '{renderer}'."}), 400
    if not renderers[renderer].get("available"):
        return jsonify({"error": renderers[renderer].get("detail", "Requested renderer is unavailable.")}), 503
    try:
        payload = _resolve_report_payload(int(user["id"]), report_type, source_id, theme, renderer)
    except Exception as exc:
        payload = empty_report(report_type, "Report Preview", str(exc), theme=theme, renderer=renderer)
    html = render_template("report_preview.html", report=payload)
    pdf_bytes = render_pdf(payload, renderer=renderer, html=html, base_url=str(BASE_DIR))
    filename = f"{payload.get('filename_stem', 'report')}_{renderer}_preview.pdf"
    return Response(pdf_bytes, mimetype="application/pdf", headers={"Content-Disposition": f"inline; filename={filename}"})


@app.route("/docs")
@login_required
@workbench_ready_required
def docs_page() -> str:
    return render_template("docs.html", active_page="docs", bootstrap_data=_user_bootstrap("docs"))


@app.route("/history")
@login_required
@workbench_ready_required
def history_page() -> str:
    return render_template("history.html", active_page="history", bootstrap_data=_user_bootstrap("history"))


@app.route("/feedback", methods=["GET", "POST"])
@login_required
@workbench_ready_required
def feedback_page() -> str | Response:
    user = current_user()
    form_data = {
        "category": "question",
        "overall_rating": "5",
        "usability_rating": "5",
        "visual_rating": "5",
        "clarity_rating": "5",
        "title": "",
        "message": "",
        "question": "",
    }
    errors: Dict[str, str] = {}
    if request.method == "POST" and user:
        form_data.update({
            "category": str(request.form.get("category", "question")).strip(),
            "overall_rating": str(request.form.get("overall_rating", "5")).strip(),
            "usability_rating": str(request.form.get("usability_rating", "5")).strip(),
            "visual_rating": str(request.form.get("visual_rating", "5")).strip(),
            "clarity_rating": str(request.form.get("clarity_rating", "5")).strip(),
            "title": str(request.form.get("title", "")).strip(),
            "message": str(request.form.get("message", "")).strip(),
            "question": str(request.form.get("question", "")).strip(),
        })
        if form_data["category"] not in FEEDBACK_CATEGORIES:
            errors["category"] = "Choose a valid feedback category."
        for field in ("overall_rating", "usability_rating", "visual_rating", "clarity_rating"):
            if form_data[field] not in {"1", "2", "3", "4", "5"}:
                errors[field] = "Ratings must stay between 1 and 5."
        if len(form_data["title"]) < 4:
            errors["title"] = "Add a short title so you can recognize this feedback later."
        if len(form_data["message"]) < 12:
            errors["message"] = "Share a little more detail so the feedback is useful."
        if not errors:
            _store_feedback(
                int(user["id"]),
                {
                    "category": form_data["category"],
                    "overall_rating": int(form_data["overall_rating"]),
                    "usability_rating": int(form_data["usability_rating"]),
                    "visual_rating": int(form_data["visual_rating"]),
                    "clarity_rating": int(form_data["clarity_rating"]),
                    "title": form_data["title"],
                    "message": form_data["message"],
                    "question": form_data["question"],
                },
            )
            flash("Feedback saved. Thanks for helping tighten the workbench.", "success")
            return redirect(url_for("feedback_page"))
    return render_template(
        "feedback.html",
        active_page="feedback",
        bootstrap_data=_user_bootstrap("feedback"),
        form_data=form_data,
        form_errors=errors,
        feedback_records=_list_feedback(int(user["id"])) if user else [],
        feedback_categories=FEEDBACK_CATEGORIES,
    )


@app.route("/runs/<run_id>")
@login_required
@workbench_ready_required
def run_detail(run_id: str) -> str:
    user = current_user()
    _run_by_id(int(user["id"]), run_id)
    return render_template("run_detail.html", active_page="history", bootstrap_data=_user_bootstrap("run_detail", {"run_id": run_id}))


@app.route("/api/status")
@login_required
def api_status():
    user = current_user()
    return jsonify(project_status(int(user["id"])))


@app.route("/api/profile/theme", methods=["POST"])
@login_required
def api_profile_theme():
    user = current_user()
    payload = request.get_json(force=True)
    theme = str(payload.get("theme", "")).strip()
    if theme not in THEME_OPTIONS:
        return jsonify({"error": "Unsupported theme."}), 400
    _db().execute(
        "UPDATE user_profiles SET preferred_theme = ?, updated_at = ? WHERE user_id = ?",
        (theme, datetime.now().astimezone().isoformat(), int(user["id"])),
    )
    _db().commit()
    return jsonify({"theme": theme})


@app.route("/api/evaluation")
@login_required
@workbench_ready_required
def api_evaluation():
    ensure_evaluation_started()
    return jsonify(EVALUATION_CACHE)


@app.route("/api/reports/catalog")
@login_required
@workbench_ready_required
def api_reports_catalog():
    user = current_user()
    return jsonify(report_catalog(**_report_preview_context(int(user["id"]))))


@app.route("/api/reports/download.pdf")
@login_required
@workbench_ready_required
def api_reports_download_pdf():
    user = current_user()
    report_type = str(request.args.get("report_type", "analysis")).strip() or "analysis"
    source_id = str(request.args.get("source_id") or request.args.get("run_id") or "").strip() or None
    renderer = str(request.args.get("renderer", "weasyprint")).strip() or "weasyprint"
    theme = str(request.args.get("theme", (current_profile() or {}).get("preferred_theme", "campus"))).strip() or "campus"
    renderers = _report_renderer_statuses()
    if renderer not in renderers:
        return jsonify({"error": f"Unsupported renderer '{renderer}'."}), 400
    if not renderers[renderer].get("available"):
        return jsonify({"error": renderers[renderer].get("detail", "Requested renderer is unavailable.")}), 503
    payload = _resolve_report_payload(int(user["id"]), report_type, source_id, theme, renderer)
    html = render_template("report_preview.html", report=payload)
    pdf_bytes = render_pdf(payload, renderer=renderer, html=html, base_url=str(BASE_DIR))
    filename = f"{payload.get('filename_stem', 'report')}_{renderer}.pdf"
    return Response(pdf_bytes, mimetype="application/pdf", headers={"Content-Disposition": f"attachment; filename={filename}"})


@app.route("/api/bootstrap/retry", methods=["POST"])
@login_required
def api_bootstrap_retry():
    ensure_bootstrap_started()
    return jsonify({"bootstrap": BOOTSTRAP_STATUS})


@app.route("/api/demo/catalog")
@login_required
@workbench_ready_required
def api_demo_catalog():
    return jsonify({"samples": demo_catalog()})


@app.route("/api/demo/sample/<sample_id>/text")
@login_required
@workbench_ready_required
def api_demo_sample_text(sample_id: str):
    path = _scenario_path(sample_id)
    return jsonify({"sample": _scenario_meta(sample_id), "text": path.read_text(encoding="utf-8", errors="ignore")})


@app.route("/api/demo/sample/<sample_id>/analyze", methods=["POST"])
@login_required
@workbench_ready_required
def api_demo_sample_analyze(sample_id: str):
    user = current_user()
    payload = request.get_json(silent=True) or {}
    mode = payload.get("mode", (current_profile() or {}).get("preferred_analysis_mode", "compare"))
    meta = _scenario_meta(sample_id)
    records = load_records_from_file(Path(meta["path"]))
    result = apply_mode_filter(workbench.predict_records(records), mode)
    run = _persist_analysis(int(user["id"]), "scenario", meta["filename"], mode, result, {"sample_id": sample_id})
    return jsonify({"sample": meta, "run": _run_summary(run), "result": result})


@app.route("/api/demo/sample/<sample_id>/download")
@login_required
@workbench_ready_required
def api_demo_sample_download(sample_id: str):
    meta = _scenario_meta(sample_id)
    return send_file(meta["path"], as_attachment=True, download_name=meta["filename"], mimetype="text/plain")


@app.route("/api/demo/replay/start", methods=["POST"])
@login_required
@workbench_ready_required
def api_demo_replay_start():
    user = current_user()
    payload = request.get_json(force=True)
    sample_id = payload.get("sample_id", "executive-brief")
    interval = float(payload.get("interval", 0.45))
    system = str(payload.get("system", (current_profile() or {}).get("live_trace_os_preference", "Windows"))).strip() or "Windows"
    _, replay = _user_services(int(user["id"]))
    USER_LIVE_CONTEXT[int(user["id"])] = {"system": system, "sample_id": sample_id, "public_user_id": user.get("public_user_id")}
    return jsonify(replay.start(sample_id, interval=interval))


@app.route("/api/demo/replay/stop", methods=["POST"])
@login_required
@workbench_ready_required
def api_demo_replay_stop():
    user = current_user()
    _, replay = _user_services(int(user["id"]))
    return jsonify(replay.stop())


@app.route("/api/analyze/text", methods=["POST"])
@login_required
@workbench_ready_required
def api_analyze_text():
    user = current_user()
    payload = request.get_json(force=True)
    text = payload.get("text", "")
    mode = payload.get("mode", (current_profile() or {}).get("preferred_analysis_mode", "compare"))
    records = load_records_from_text(text)
    result = apply_mode_filter(workbench.predict_records(records), mode)
    run = _persist_analysis(int(user["id"]), "text", "pasted_text.log", mode, result, {"source_type": "text"})
    return jsonify({"run": _run_summary(run), "result": result})


@app.route("/api/analyze/upload", methods=["POST"])
@login_required
@workbench_ready_required
def api_analyze_upload():
    user = current_user()
    uploaded_file = request.files.get("file")
    mode = request.form.get("mode", (current_profile() or {}).get("preferred_analysis_mode", "compare"))
    if uploaded_file is None or uploaded_file.filename == "":
        return jsonify({"error": "No file uploaded."}), 400

    filename = secure_filename(uploaded_file.filename)
    saved_path = _user_upload_dir(int(user["id"])) / filename
    uploaded_file.save(saved_path)
    _db().execute(
        "INSERT INTO user_uploads (user_id, original_filename, stored_path, created_at) VALUES (?, ?, ?, ?)",
        (int(user["id"]), filename, str(saved_path.resolve()), _timestamp()),
    )
    _db().commit()

    records = load_records_from_file(saved_path)
    result = apply_mode_filter(workbench.predict_records(records), mode)
    run = _persist_analysis(int(user["id"]), "upload", filename, mode, result, {"saved_path": str(saved_path.resolve())})
    return jsonify({"filename": filename, "saved_path": str(saved_path.resolve()), "run": _run_summary(run), "result": result})


@app.route("/api/runs")
@login_required
@workbench_ready_required
def api_runs():
    user = current_user()
    current_run = _current_run(int(user["id"]))
    return jsonify({"runs": _list_runs(int(user["id"])), "current_run_id": current_run["id"] if current_run else None})


@app.route("/api/feedback")
@login_required
@workbench_ready_required
def api_feedback():
    user = current_user()
    return jsonify({"feedback": _list_feedback(int(user["id"]))})


@app.route("/api/runs/<run_id>")
@login_required
@workbench_ready_required
def api_run_detail(run_id: str):
    user = current_user()
    run = _run_by_id(int(user["id"]), run_id)
    return jsonify({"run": {**_run_summary(run), "result": run["result"], "recommendations": _build_run_recommendations(run)}})


@app.route("/api/live/start", methods=["POST"])
@login_required
@workbench_ready_required
def api_live_start():
    user = current_user()
    payload = request.get_json(force=True)
    path = str(payload.get("path", "")).strip()
    system = str(payload.get("system", (current_profile() or {}).get("live_trace_os_preference", "Windows"))).strip() or "Windows"
    if not path:
        return jsonify({"error": "Path is required."}), 400
    live_monitor, replay = _user_services(int(user["id"]))
    replay.stop(stop_live=False)
    USER_LIVE_CONTEXT[int(user["id"])] = {"system": system, "path": path, "public_user_id": user.get("public_user_id")}
    return jsonify(live_monitor.start(path))


@app.route("/api/live/stop", methods=["POST"])
@login_required
@workbench_ready_required
def api_live_stop():
    user = current_user()
    live_monitor, replay = _user_services(int(user["id"]))
    replay.stop(stop_live=False)
    return jsonify(live_monitor.stop())


@app.route("/api/live/status")
@login_required
@workbench_ready_required
def api_live_status():
    user = current_user()
    live_monitor, replay = _user_services(int(user["id"]))
    return jsonify({"status": live_monitor.status(), "replay": replay.status(), "context": USER_LIVE_CONTEXT.get(int(user["id"]), {})})


@app.route("/api/live/save", methods=["POST"])
@login_required
@workbench_ready_required
def api_live_save():
    user = current_user()
    payload = request.get_json(silent=True) or {}
    live_monitor, _ = _user_services(int(user["id"]))
    status = live_monitor.status()
    result = status.get("result")
    if not result:
        return jsonify({"error": "No live result is available yet."}), 400
    path = status.get("path") or "live_monitor.log"
    filename = Path(path).name
    mode = payload.get("mode", (current_profile() or {}).get("preferred_analysis_mode", "compare"))
    live_context = dict(USER_LIVE_CONTEXT.get(int(user["id"]), {}))
    live_context.update({"path": path, "saved_from_live": True})
    run = _persist_analysis(int(user["id"]), "live", filename, mode, result, live_context)
    return jsonify({"run": _run_summary(run), "result": result})


@app.route("/api/adaptive/status")
@login_required
@workbench_ready_required
def api_adaptive_status():
    return jsonify(workbench.get_adaptive_status())


@app.route("/api/adaptive/toggle", methods=["POST"])
@login_required
@workbench_ready_required
def api_adaptive_toggle():
    enabled = not workbench.get_adaptive_status().get("enabled", True)
    return jsonify(workbench.set_adaptive_thresholding(enabled))


@app.route("/api/report/export.json")
@login_required
@workbench_ready_required
def api_report_export_json():
    user = current_user()
    run = _selected_run(int(user["id"]), request.args.get("run_id"))
    payload = json.dumps(run, indent=2)
    return Response(payload, mimetype="application/json", headers={"Content-Disposition": f"attachment; filename={_run_filename(run, 'json')}"})


@app.route("/api/report/export.csv")
@login_required
@workbench_ready_required
def api_report_export_csv():
    user = current_user()
    run = _selected_run(int(user["id"]), request.args.get("run_id"))
    payload = workbench.export_report_csv(run.get("result") or _empty_result())
    return Response(payload, mimetype="text/csv", headers={"Content-Disposition": f"attachment; filename={_run_filename(run, 'csv')}"})


@app.route("/api/report/export.html")
@login_required
@workbench_ready_required
def api_report_export_html():
    user = current_user()
    run = _selected_run(int(user["id"]), request.args.get("run_id"))
    theme = (current_profile() or {}).get("preferred_theme", "campus")
    payload = build_analysis_report(run, MODEL_NAMES, theme=theme, renderer="weasyprint")
    html = render_template("report_preview.html", report=payload)
    return Response(html, mimetype="text/html", headers={"Content-Disposition": f"attachment; filename={_run_filename(run, 'html')}"})


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=int(os.getenv("PORT", "5000")),
        debug=os.getenv("FLASK_DEBUG", "0") == "1",
    )
