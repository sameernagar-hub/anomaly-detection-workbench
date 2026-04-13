from __future__ import annotations

import json
import threading
import time
import uuid
from collections import deque
from datetime import datetime
from pathlib import Path
import sys
from typing import Any, Deque, Dict, List, Optional

from flask import Flask, Response, abort, jsonify, redirect, render_template, request, send_file, url_for
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from workbench import DEFAULT_UPLOAD_TEXT, AnomalyWorkbench, LiveMonitor, load_records_from_file, load_records_from_text


app = Flask(__name__)
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
DEMO_RUNTIME_DIR = BASE_DIR / "demo_runtime"
DEMO_RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
SAMPLE_DIR = BASE_DIR / "sample_data"

MODEL_NAMES = {
    "baseline": {
        "label": "Baseline Sentinel",
        "subtitle": "Baseline sequence model",
    },
    "improved": {
        "label": "Apex Insight",
        "subtitle": "Improved argument-aware model",
    },
}

SAMPLE_SCENARIOS = [
    {
        "id": "executive-brief",
        "filename": "executive_brief.log",
        "title": "Executive Brief",
        "eyebrow": "Balanced sample",
        "description": "A premium walkthrough trace with a clean opening, a reconnaissance burst, and enough volume to light up every chart.",
        "tags": ["balanced", "demo-ready", "compare"],
        "mood": "Emerald Core",
    },
    {
        "id": "recon-surge",
        "filename": "recon_surge.log",
        "title": "Recon Surge",
        "eyebrow": "Attack-heavy sample",
        "description": "A louder stream with repeated reconnaissance-style spikes that makes the improved model story easy to visualize.",
        "tags": ["attack", "high-signal", "live-demo"],
        "mood": "Gold Pulse",
    },
    {
        "id": "night-shift",
        "filename": "night_shift.log",
        "title": "Night Shift Drift",
        "eyebrow": "Drift scenario",
        "description": "Starts quiet, shifts protocol mix, and ends with enough variance to trigger drift and adaptive-threshold storytelling.",
        "tags": ["drift", "adaptive", "timeline"],
        "mood": "Graphite Tide",
    },
    {
        "id": "disagreement-lab",
        "filename": "disagreement_lab.log",
        "title": "Disagreement Lab",
        "eyebrow": "Model showdown",
        "description": "A curated sequence meant to spotlight disagreement windows, mixed labels, and metric deltas between the two models.",
        "tags": ["disagreement", "benchmark", "storytelling"],
        "mood": "Copper Signal",
    },
]

workbench = AnomalyWorkbench(BASE_DIR)
live_monitor = LiveMonitor(workbench)

RUN_LIMIT = 80
RUN_ORDER: Deque[str] = deque(maxlen=RUN_LIMIT)
RUN_STORE: Dict[str, Dict[str, Any]] = {}
RUN_LOCK = threading.Lock()
CURRENT_RUN_ID: Optional[str] = None

BOOTSTRAP_STATUS: Dict[str, Any] = {
    "state": "starting",
    "message": "Warming the anomaly showcase...",
    "details": {},
}

EVALUATION_CACHE: Dict[str, Any] = {
    "state": "idle",
    "message": "Evaluation snapshot has not run yet.",
    "updated_at": None,
    "benchmark": None,
}

BOOTSTRAP_LOCK = threading.Lock()
BOOTSTRAP_THREAD: Optional[threading.Thread] = None
EVALUATION_THREAD: Optional[threading.Thread] = None


def _scenario_path(sample_id: str) -> Path:
    for scenario in SAMPLE_SCENARIOS:
        if scenario["id"] == sample_id:
            return SAMPLE_DIR / scenario["filename"]
    raise KeyError(f"Unknown scenario '{sample_id}'")


def _scenario_meta(sample_id: str) -> Dict[str, Any]:
    for scenario in SAMPLE_SCENARIOS:
        if scenario["id"] == sample_id:
            path = SAMPLE_DIR / scenario["filename"]
            line_count = 0
            if path.exists():
                line_count = len(path.read_text(encoding="utf-8", errors="ignore").splitlines())
            return {
                **scenario,
                "path": str(path.resolve()),
                "line_count": line_count,
            }
    raise KeyError(f"Unknown scenario '{sample_id}'")


def demo_catalog() -> List[Dict[str, Any]]:
    return [_scenario_meta(scenario["id"]) for scenario in SAMPLE_SCENARIOS]


def _timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _empty_result() -> Dict[str, Any]:
    return {"summary": {}, "items": [], "charts": {}}


def _summary_for(result: Dict[str, Any]) -> Dict[str, Any]:
    return dict((result or {}).get("summary") or {})


def _run_summary(run: Dict[str, Any]) -> Dict[str, Any]:
    summary = run.get("summary", {})
    return {
        "id": run["id"],
        "source": run["source"],
        "filename": run["filename"],
        "created_at": run["created_at"],
        "mode": run["mode"],
        "summary": summary,
        "metadata": run.get("metadata", {}),
        "detail_url": url_for("run_detail", run_id=run["id"]),
    }


def _list_runs() -> List[Dict[str, Any]]:
    with RUN_LOCK:
        return [_run_summary(RUN_STORE[run_id]) for run_id in RUN_ORDER if run_id in RUN_STORE]


def _current_run() -> Optional[Dict[str, Any]]:
    with RUN_LOCK:
        if CURRENT_RUN_ID and CURRENT_RUN_ID in RUN_STORE:
            return RUN_STORE[CURRENT_RUN_ID]
    return None


def _store_run(source: str, filename: str, mode: str, result: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    global CURRENT_RUN_ID
    run_id = uuid.uuid4().hex[:10]
    run = {
        "id": run_id,
        "source": source,
        "filename": filename,
        "created_at": _timestamp(),
        "mode": mode,
        "summary": _summary_for(result),
        "result": result,
        "metadata": metadata or {},
    }
    with RUN_LOCK:
        RUN_STORE[run_id] = run
        RUN_ORDER.appendleft(run_id)
        CURRENT_RUN_ID = run_id
        while len(RUN_ORDER) > RUN_LIMIT:
            stale_id = RUN_ORDER.pop()
            RUN_STORE.pop(stale_id, None)
    return run


def _run_by_id(run_id: str) -> Dict[str, Any]:
    with RUN_LOCK:
        run = RUN_STORE.get(run_id)
    if run is None:
        abort(404, description=f"Run '{run_id}' was not found.")
    return run


def _selected_run(run_id: Optional[str]) -> Dict[str, Any]:
    if run_id:
        return _run_by_id(run_id)
    run = _current_run()
    if run is None:
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
    return run


def _run_filename(run: Dict[str, Any], extension: str) -> str:
    stem = Path(run.get("filename") or "anomaly_report").stem
    mode = run.get("mode", "compare")
    return f"{stem}_{mode}.{extension}"


def _bootstrap_payload(page: str, extras: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    featured = _scenario_meta("executive-brief")
    current_run = _current_run()
    payload = {
        "page": page,
        "sample_text": Path(featured["path"]).read_text(encoding="utf-8", errors="ignore"),
        "sample_catalog": demo_catalog(),
        "model_names": MODEL_NAMES,
        "featured_sample": featured,
        "default_upload_text": DEFAULT_UPLOAD_TEXT,
        "current_run_id": current_run["id"] if current_run else None,
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
        metric_rows.append(
            {
                "metric": metric_name,
                "baseline": baseline_value,
                "improved": improved_value,
                "delta": delta,
            }
        )

    folds = cross_host.get("folds", [])
    baseline_cross = [fold.get("deeplog_accuracy") for fold in folds if fold.get("deeplog_accuracy") is not None]
    improved_cross = [fold.get("report_accuracy") for fold in folds if fold.get("report_accuracy") is not None]
    cross_summary = {
        "fold_count": len(folds),
        "baseline_avg_accuracy": round(sum(baseline_cross) / len(baseline_cross), 3) if baseline_cross else None,
        "improved_avg_accuracy": round(sum(improved_cross) / len(improved_cross), 3) if improved_cross else None,
    }
    if cross_summary["baseline_avg_accuracy"] is not None and cross_summary["improved_avg_accuracy"] is not None:
        cross_summary["delta"] = round(
            cross_summary["improved_avg_accuracy"] - cross_summary["baseline_avg_accuracy"],
            3,
        )
    else:
        cross_summary["delta"] = None

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
        "standard": {
            "summary": summary,
            "metric_rows": metric_rows,
        },
        "cross_host": {
            "note": cross_host.get("note"),
            "summary": cross_summary,
            "folds": folds,
        },
        "headline": headline,
    }


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
        featured_sample = _scenario_meta("executive-brief")
        sample_result = workbench.predict_records(load_records_from_file(Path(featured_sample["path"])))
        _store_run("bootstrap", featured_sample["filename"], "compare", sample_result, {"sample_id": "executive-brief"})
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
        BOOTSTRAP_THREAD = threading.Thread(target=bootstrap_models, daemon=True)
        BOOTSTRAP_THREAD.start()


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
    if mode == "deeplog":
        filtered_summary["active_model"] = MODEL_NAMES["baseline"]["label"]
    elif mode == "report":
        filtered_summary["active_model"] = MODEL_NAMES["improved"]["label"]
    else:
        filtered_summary["active_model"] = "Dual Command View"

    return {
        "summary": filtered_summary,
        "items": filtered_items,
        "charts": result["charts"],
    }


class DemoReplay:
    def __init__(self, live_monitor_: LiveMonitor) -> None:
        self.live_monitor = live_monitor_
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
        target_path = DEMO_RUNTIME_DIR / f"{sample_id}_live.log"
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
        self._thread = threading.Thread(
            target=self._run,
            args=(sample_id, source_path, target_path, interval),
            daemon=True,
        )
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


demo_replay = DemoReplay(live_monitor)


def project_status() -> Dict[str, Any]:
    current_run = _current_run()
    return {
        "bootstrap": BOOTSTRAP_STATUS,
        "artifacts": {
            "baseline_model": str(workbench.baseline_artifact_path),
            "report_model": str(workbench.report_model_path),
        },
        "adaptive": workbench.get_adaptive_status(),
        "live": live_monitor.status(),
        "replay": demo_replay.status(),
        "recent_runs": _list_runs(),
        "current_run": _run_summary(current_run) if current_run else None,
        "current_result": current_run["result"] if current_run else None,
        "model_names": MODEL_NAMES,
        "evaluation": {
            "state": EVALUATION_CACHE["state"],
            "message": EVALUATION_CACHE["message"],
            "updated_at": EVALUATION_CACHE["updated_at"],
        },
    }


def _persist_analysis(source: str, filename: str, mode: str, result: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return _store_run(source, filename, mode, result, metadata)


@app.before_request
def _ensure_background_tasks() -> None:
    ensure_bootstrap_started()


@app.route("/")
def home() -> Response:
    return redirect(url_for("overview"))


@app.route("/overview")
def overview() -> str:
    return render_template(
        "overview.html",
        active_page="overview",
        bootstrap_data=_bootstrap_payload("overview"),
    )


@app.route("/analyze")
def analyze_page() -> str:
    return render_template(
        "analyze.html",
        active_page="analyze",
        bootstrap_data=_bootstrap_payload("analyze"),
    )


@app.route("/live")
def live_page() -> str:
    return render_template(
        "live.html",
        active_page="live",
        bootstrap_data=_bootstrap_payload("live"),
    )


@app.route("/evaluation")
def evaluation_page() -> str:
    return render_template(
        "evaluation.html",
        active_page="evaluation",
        bootstrap_data=_bootstrap_payload("evaluation"),
    )


@app.route("/history")
def history_page() -> str:
    return render_template(
        "history.html",
        active_page="history",
        bootstrap_data=_bootstrap_payload("history"),
    )


@app.route("/runs/<run_id>")
def run_detail(run_id: str) -> str:
    run = _run_by_id(run_id)
    return render_template(
        "run_detail.html",
        active_page="history",
        bootstrap_data=_bootstrap_payload("run_detail", {"run_id": run["id"]}),
    )


@app.route("/api/status")
def api_status():
    return jsonify(project_status())


@app.route("/api/evaluation")
def api_evaluation():
    ensure_evaluation_started()
    return jsonify(EVALUATION_CACHE)


@app.route("/api/demo/catalog")
def api_demo_catalog():
    return jsonify({"samples": demo_catalog()})


@app.route("/api/demo/sample/<sample_id>/text")
def api_demo_sample_text(sample_id: str):
    path = _scenario_path(sample_id)
    return jsonify({"sample": _scenario_meta(sample_id), "text": path.read_text(encoding="utf-8", errors="ignore")})


@app.route("/api/demo/sample/<sample_id>/analyze", methods=["POST"])
def api_demo_sample_analyze(sample_id: str):
    payload = request.get_json(silent=True) or {}
    mode = payload.get("mode", "compare")
    meta = _scenario_meta(sample_id)
    records = load_records_from_file(Path(meta["path"]))
    result = apply_mode_filter(workbench.predict_records(records), mode)
    run = _persist_analysis("scenario", meta["filename"], mode, result, {"sample_id": sample_id})
    return jsonify({"sample": meta, "run": _run_summary(run), "result": result})


@app.route("/api/demo/sample/<sample_id>/download")
def api_demo_sample_download(sample_id: str):
    meta = _scenario_meta(sample_id)
    return send_file(
        meta["path"],
        as_attachment=True,
        download_name=meta["filename"],
        mimetype="text/plain",
    )


@app.route("/api/demo/replay/start", methods=["POST"])
def api_demo_replay_start():
    payload = request.get_json(force=True)
    sample_id = payload.get("sample_id", "executive-brief")
    interval = float(payload.get("interval", 0.45))
    return jsonify(demo_replay.start(sample_id, interval=interval))


@app.route("/api/demo/replay/stop", methods=["POST"])
def api_demo_replay_stop():
    return jsonify(demo_replay.stop())


@app.route("/api/analyze/text", methods=["POST"])
def api_analyze_text():
    payload = request.get_json(force=True)
    text = payload.get("text", "")
    mode = payload.get("mode", "compare")
    records = load_records_from_text(text)
    result = apply_mode_filter(workbench.predict_records(records), mode)
    run = _persist_analysis("text", "pasted_text.log", mode, result)
    return jsonify({"run": _run_summary(run), "result": result})


@app.route("/api/analyze/upload", methods=["POST"])
def api_analyze_upload():
    uploaded_file = request.files.get("file")
    mode = request.form.get("mode", "compare")
    if uploaded_file is None or uploaded_file.filename == "":
        return jsonify({"error": "No file uploaded."}), 400

    filename = secure_filename(uploaded_file.filename)
    saved_path = UPLOAD_DIR / filename
    uploaded_file.save(saved_path)

    records = load_records_from_file(saved_path)
    result = apply_mode_filter(workbench.predict_records(records), mode)
    run = _persist_analysis("upload", filename, mode, result, {"saved_path": str(saved_path.resolve())})
    return jsonify({"filename": filename, "saved_path": str(saved_path.resolve()), "run": _run_summary(run), "result": result})


@app.route("/api/runs")
def api_runs():
    return jsonify({"runs": _list_runs(), "current_run_id": _current_run()["id"] if _current_run() else None})


@app.route("/api/runs/<run_id>")
def api_run_detail(run_id: str):
    run = _run_by_id(run_id)
    return jsonify({"run": {**_run_summary(run), "result": run["result"]}})


@app.route("/api/live/start", methods=["POST"])
def api_live_start():
    payload = request.get_json(force=True)
    path = str(payload.get("path", "")).strip()
    if not path:
        return jsonify({"error": "Path is required."}), 400
    demo_replay.stop(stop_live=False)
    return jsonify(live_monitor.start(path))


@app.route("/api/live/stop", methods=["POST"])
def api_live_stop():
    demo_replay.stop(stop_live=False)
    return jsonify(live_monitor.stop())


@app.route("/api/live/status")
def api_live_status():
    return jsonify({"status": live_monitor.status(), "replay": demo_replay.status()})


@app.route("/api/live/save", methods=["POST"])
def api_live_save():
    payload = request.get_json(silent=True) or {}
    status = live_monitor.status()
    result = status.get("result")
    if not result:
        return jsonify({"error": "No live result is available yet."}), 400
    path = status.get("path") or "live_monitor.log"
    filename = Path(path).name
    run = _persist_analysis(
        "live",
        filename,
        payload.get("mode", "compare"),
        result,
        {"path": path, "saved_from_live": True},
    )
    return jsonify({"run": _run_summary(run), "result": result})


@app.route("/api/adaptive/status")
def api_adaptive_status():
    return jsonify(workbench.get_adaptive_status())


@app.route("/api/adaptive/toggle", methods=["POST"])
def api_adaptive_toggle():
    enabled = not workbench.get_adaptive_status().get("enabled", True)
    return jsonify(workbench.set_adaptive_thresholding(enabled))


@app.route("/api/report/export.json")
def api_report_export_json():
    run = _selected_run(request.args.get("run_id"))
    payload = json.dumps(run, indent=2)
    return Response(
        payload,
        mimetype="application/json",
        headers={"Content-Disposition": f"attachment; filename={_run_filename(run, 'json')}"},
    )


@app.route("/api/report/export.csv")
def api_report_export_csv():
    run = _selected_run(request.args.get("run_id"))
    payload = workbench.export_report_csv(run.get("result") or _empty_result())
    return Response(
        payload,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={_run_filename(run, 'csv')}"},
    )


@app.route("/api/report/export.html")
def api_report_export_html():
    run = _selected_run(request.args.get("run_id"))
    payload = workbench.export_report_html(
        run.get("result") or _empty_result(),
        title=f"Anomaly Report: {run.get('filename', 'Current Report')}",
    )
    return Response(
        payload,
        mimetype="text/html",
        headers={"Content-Disposition": f"attachment; filename={_run_filename(run, 'html')}"},
    )


if __name__ == "__main__":
    ensure_bootstrap_started()
    app.run(host="127.0.0.1", port=5000, debug=True)
