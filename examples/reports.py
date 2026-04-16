from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence


THEME_TOKENS = {
    "campus": {
        "ink": "#1f2833",
        "muted": "#5c6773",
        "line": "#d9e1e8",
        "line_strong": "#c8d3dc",
        "paper": "#fdf8f1",
        "paper_alt": "#f2eadf",
        "accent": "#234b6d",
        "accent_soft": "#e7eef7",
        "accent_alt": "#157a6e",
        "accent_alt_soft": "#e8f4f1",
        "warn": "#b3563b",
        "hero": "linear-gradient(135deg, rgba(35, 75, 109, 0.14), rgba(21, 122, 110, 0.08), rgba(255,255,255,0.92))",
        "canvas": "#ece4d8",
        "canvas_alt": "#dfe9f2",
        "panel": "rgba(255, 251, 245, 0.92)",
        "panel_strong": "#fffdf8",
        "panel_alt": "#f6efe5",
        "shadow_rgb": "34, 46, 61",
    },
    "midnight": {
        "ink": "#eaf1f8",
        "muted": "#aab8c9",
        "line": "#334354",
        "line_strong": "#45607f",
        "paper": "#121923",
        "paper_alt": "#18212d",
        "accent": "#8ab4ff",
        "accent_soft": "#203149",
        "accent_alt": "#5bd6b0",
        "accent_alt_soft": "#19362f",
        "warn": "#ff8e6b",
        "hero": "linear-gradient(135deg, rgba(138, 180, 255, 0.24), rgba(91, 214, 176, 0.16), rgba(18,25,35,0.96))",
        "canvas": "#0b1119",
        "canvas_alt": "#16212f",
        "panel": "rgba(17, 24, 35, 0.94)",
        "panel_strong": "#121923",
        "panel_alt": "#18212d",
        "shadow_rgb": "0, 0, 0",
    },
    "signal": {
        "ink": "#1f2730",
        "muted": "#61707f",
        "line": "#d9dfec",
        "line_strong": "#c0cae0",
        "paper": "#fcfbff",
        "paper_alt": "#eef0fb",
        "accent": "#7b3fe4",
        "accent_soft": "#f1ebfd",
        "accent_alt": "#0d9488",
        "accent_alt_soft": "#e9f8f6",
        "warn": "#db5a42",
        "hero": "linear-gradient(135deg, rgba(123, 63, 228, 0.14), rgba(13, 148, 136, 0.1), rgba(255,255,255,0.95))",
        "canvas": "#ece7fb",
        "canvas_alt": "#dff4f1",
        "panel": "rgba(255, 255, 255, 0.94)",
        "panel_strong": "#fdfcff",
        "panel_alt": "#f4f1fe",
        "shadow_rgb": "49, 37, 89",
    },
}


def _now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def report_theme(theme: str) -> Dict[str, str]:
    return dict(THEME_TOKENS.get(theme, THEME_TOKENS["campus"]))


def _safe_score(value: Any, digits: int = 3) -> str:
    if value is None:
        return "-"
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return str(value)


def _safe_pct(value: Any) -> str:
    if value is None:
        return "-"
    try:
        return f"{round(float(value) * 100)}%"
    except (TypeError, ValueError):
        return str(value)


def _hero_metric(label: str, value: Any, detail: str, tone: str = "default") -> Dict[str, Any]:
    return {"label": label, "value": str(value), "detail": detail, "tone": tone}


def _meta_items(items: Dict[str, Any]) -> List[Dict[str, str]]:
    result: List[Dict[str, str]] = []
    for key, value in items.items():
        if value is None or value == "":
            continue
        result.append({"label": str(key).replace("_", " ").title(), "value": str(value)})
    return result


def _summary_rows(summary: Dict[str, Any]) -> List[Dict[str, str]]:
    drift = summary.get("drift", {}) or {}
    return [
        {"label": "Windows analyzed", "value": str(summary.get("window_count", 0))},
        {"label": "Baseline anomalies", "value": str(summary.get("deeplog_anomalies", 0))},
        {"label": "Apex anomalies", "value": str(summary.get("report_anomalies", 0))},
        {"label": "Agreement", "value": _safe_pct(summary.get("agreement_rate"))},
        {"label": "Improved accuracy", "value": _safe_score(summary.get("report_vs_label_accuracy"))},
        {"label": "Baseline accuracy", "value": _safe_score(summary.get("deep_vs_label_accuracy"))},
        {"label": "Adaptive threshold", "value": _safe_score(summary.get("adaptive_threshold"), digits=4)},
        {"label": "Drift posture", "value": str(drift.get("status", "n/a")).replace("_", " ").title()},
    ]


def _clip_text(value: Any, limit: int = 80) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text or "-"
    return f"{text[:limit - 1]}..."


def _table_row(*cells: Any, raw_detail: str = "") -> Dict[str, Any]:
    return {"cells": [str(cell) for cell in cells], "raw_detail": str(raw_detail or "").strip()}


def _table_section(eyebrow: str, title: str, columns: Sequence[str], rows: Sequence[Dict[str, Any]], empty_message: str) -> Dict[str, Any]:
    return {
        "eyebrow": eyebrow,
        "title": title,
        "kind": "table",
        "columns": list(columns),
        "rows": list(rows),
        "empty_message": empty_message,
    }


def _timeline_rows(result: Dict[str, Any], limit: int = 18) -> List[Dict[str, Any]]:
    rows = []
    for entry in (result.get("charts", {}) or {}).get("timeline", [])[-limit:]:
        rows.append(
            _table_row(
                entry.get("line_number"),
                _safe_score(entry.get("deeplog")),
                _safe_score(entry.get("report")),
                "Attack" if int(entry.get("label", 0) or 0) == 1 else "Normal",
            )
        )
    return rows


def _evidence_rows(result: Dict[str, Any], limit: int = 14) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for item in result.get("items", [])[:limit]:
        rows.append(
            _table_row(
                item.get("line_number"),
                _clip_text(item.get("host_group", "unknown"), 18),
                _clip_text(item.get("event", "-"), 28),
                f"{item.get('deeplog_prediction') if item.get('deeplog_prediction') is not None else 'n/a'} | {_safe_score(item.get('deeplog_score'))}",
                f"{item.get('report_prediction') if item.get('report_prediction') is not None else 'n/a'} | {_safe_score(item.get('report_score'))}",
                "Aligned" if item.get("agreement") else "Diverged" if item.get("agreement") is not None else "n/a",
                f"{item.get('label', 0)} | {_clip_text(item.get('attack_cat', 'Unknown'), 18)}",
                raw_detail=item.get("raw", ""),
            )
        )
    return rows


def _appendix_rows(rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    appendix: List[Dict[str, Any]] = []
    for row in rows:
        detail = row.get("raw_detail", "")
        if detail:
            appendix.append(_table_row(row["cells"][0], _clip_text(detail, 150)))
    return appendix


def _report_shell(
    *,
    report_type: str,
    title: str,
    subtitle: str,
    source_label: str,
    source_value: str,
    filename_stem: str,
    theme: str,
    renderer: str,
    hero_metrics: Sequence[Dict[str, Any]],
    meta: Sequence[Dict[str, str]],
    sections: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    return {
        "report_type": report_type,
        "title": title,
        "subtitle": subtitle,
        "generated_at": _now_text(),
        "source_label": source_label,
        "source_value": source_value,
        "filename_stem": filename_stem,
        "theme_name": theme,
        "theme": report_theme(theme),
        "renderer": renderer,
        "hero_metrics": list(hero_metrics),
        "meta": list(meta),
        "sections": list(sections),
    }


def build_analysis_report(run: Dict[str, Any], model_names: Dict[str, Any], *, theme: str, renderer: str) -> Dict[str, Any]:
    summary = run.get("summary", {}) or {}
    result = run.get("result", {}) or {}
    metadata = run.get("metadata", {}) or {}
    filename = run.get("filename", "Analysis Report")
    stem = Path(filename).stem or "analysis_report"
    drift = summary.get("drift", {}) or {}
    evidence_rows = _evidence_rows(result)
    sections = [
        {"eyebrow": "Executive signal", "title": "Run summary", "kind": "facts", "rows": _summary_rows(summary)},
        _table_section("Timeline service", "Recent score ribbon", ["Line", "Baseline", "Apex", "Truth"], _timeline_rows(result), "Not enough timeline points were saved for this run."),
        _table_section("Evidence service", "High-signal evidence windows", ["Line", "Host", "Event", "Baseline", "Apex", "Agreement", "Truth"], evidence_rows, "No evidence windows were recorded for this run."),
        _table_section("Appendix", "Raw evidence excerpts", ["Line", "Raw excerpt"], _appendix_rows(evidence_rows), "No raw excerpts were captured for this report."),
    ]
    return _report_shell(
        report_type="analysis",
        title=f"Analysis Report: {filename}",
        subtitle="An exported view of the saved anomaly-detection run, with drift posture, evidence windows, and print-safe appendix details.",
        source_label="Saved run",
        source_value=run.get("id") or filename,
        filename_stem=f"{stem}_{run.get('mode', 'compare')}",
        theme=theme,
        renderer=renderer,
        hero_metrics=[
            _hero_metric("Windows", summary.get("window_count", 0), "Frozen report volume"),
            _hero_metric(model_names["baseline"]["label"], summary.get("deeplog_anomalies", 0), "Baseline anomaly count"),
            _hero_metric(model_names["improved"]["label"], summary.get("report_anomalies", 0), "Improved anomaly count", tone="accent"),
            _hero_metric("Agreement", _safe_pct(summary.get("agreement_rate")), "Shared verdict rate"),
        ],
        meta=_meta_items(
            {
                "run_id": run.get("id"),
                "saved_at": run.get("created_at"),
                "source": run.get("source"),
                "mode": run.get("mode"),
                "active_model": summary.get("active_model"),
                "drift_status": drift.get("status"),
                **metadata,
            }
        ),
        sections=sections,
    )


def build_evaluation_report(evaluation_cache: Dict[str, Any], model_names: Dict[str, Any], *, theme: str, renderer: str) -> Dict[str, Any]:
    benchmark = evaluation_cache.get("benchmark") or {}
    headline = benchmark.get("headline", {}) or {}
    standard = benchmark.get("standard", {}) or {}
    cross_host = benchmark.get("cross_host", {}) or {}
    metric_rows = [
        _table_row(
            str(row.get("metric", "")).replace("_", " ").title(),
            _safe_score(row.get("baseline")),
            _safe_score(row.get("improved")),
            _safe_score(row.get("delta")),
        )
        for row in standard.get("metric_rows", [])
    ]
    fold_rows = [
        _table_row(
            row.get("host_group"),
            row.get("record_count"),
            _safe_score(row.get("deeplog_accuracy")),
            _safe_score(row.get("report_accuracy")),
        )
        for row in cross_host.get("folds", [])
    ]
    return _report_shell(
        report_type="evaluation",
        title="Evaluation Report",
        subtitle="A benchmark summary comparing the baseline sequence model against the argument-aware model across tracked metrics and proxy host folds.",
        source_label="Evaluation snapshot",
        source_value=evaluation_cache.get("updated_at") or "latest",
        filename_stem="evaluation_report",
        theme=theme,
        renderer=renderer,
        hero_metrics=[
            _hero_metric("Improved wins", f"{headline.get('improved_wins', 0)}/{headline.get('metric_count', 0)}", "Tracked benchmark metrics", tone="accent"),
            _hero_metric(model_names["baseline"]["label"], _safe_score(headline.get("baseline_accuracy")), "Benchmark accuracy"),
            _hero_metric(model_names["improved"]["label"], _safe_score(headline.get("improved_accuracy")), "Benchmark accuracy", tone="accent"),
            _hero_metric("Cross-host delta", _safe_score((cross_host.get("summary") or {}).get("delta")), "Improved minus baseline"),
        ],
        meta=_meta_items(
            {
                "snapshot_state": evaluation_cache.get("state"),
                "updated_at": evaluation_cache.get("updated_at"),
                "message": evaluation_cache.get("message"),
                "cross_host_note": cross_host.get("note"),
            }
        ),
        sections=[
            {"eyebrow": "Benchmark service", "title": "Headline metrics", "kind": "facts", "rows": [
                {"label": "Window count", "value": str(headline.get("window_count", 0))},
                {"label": "Labeled windows", "value": str(headline.get("labeled_windows", 0))},
                {"label": "Agreement", "value": _safe_pct(headline.get("agreement_rate"))},
                {"label": "Baseline anomalies", "value": str(headline.get("baseline_anomalies", 0))},
                {"label": "Apex anomalies", "value": str(headline.get("improved_anomalies", 0))},
            ]},
            _table_section("Metric service", "Model comparison grid", ["Metric", "Baseline", "Apex", "Delta"], metric_rows, "Benchmark metric rows are not available yet."),
            _table_section("Cross-host proxy", "Fold-by-fold comparison", ["Host group", "Records", "Baseline accuracy", "Apex accuracy"], fold_rows, "Cross-host folds are still warming up."),
        ],
    )


def build_live_report(live_status: Dict[str, Any], live_context: Optional[Dict[str, Any]], model_names: Dict[str, Any], *, theme: str, renderer: str) -> Dict[str, Any]:
    result = live_status.get("result") or {}
    summary = result.get("summary", {}) or {}
    context = dict(live_context or {})
    history_rows = [
        _table_row(
            row.get("timestamp"),
            row.get("line_count"),
            row.get("deeplog_anomalies"),
            row.get("report_anomalies"),
            _safe_pct(row.get("agreement_rate")),
        )
        for row in live_status.get("history", [])
    ]
    evidence_rows = _evidence_rows(result)
    return _report_shell(
        report_type="live",
        title="Live Monitor Report",
        subtitle="A printable snapshot of the current live-monitor session, including recent state, anomaly counts, and evidence windows.",
        source_label="Live source",
        source_value=live_status.get("path") or context.get("sample_id") or "active session",
        filename_stem="live_monitor_report",
        theme=theme,
        renderer=renderer,
        hero_metrics=[
            _hero_metric("Monitor state", live_status.get("status", "idle").title(), "Current live workspace posture"),
            _hero_metric(model_names["baseline"]["label"], summary.get("deeplog_anomalies", 0), "Live anomaly count"),
            _hero_metric(model_names["improved"]["label"], summary.get("report_anomalies", 0), "Improved live anomaly count", tone="accent"),
            _hero_metric("Updated", live_status.get("updated_at") or "-", "Most recent live refresh"),
        ],
        meta=_meta_items(
            {
                "path": live_status.get("path"),
                "system": context.get("system"),
                "sample_id": context.get("sample_id"),
                "public_user_id": context.get("public_user_id"),
            }
        ),
        sections=[
            {"eyebrow": "Live monitor", "title": "Live summary", "kind": "facts", "rows": _summary_rows(summary)},
            _table_section("Replay history", "Recent monitor snapshots", ["Timestamp", "Line count", "Baseline anomalies", "Apex anomalies", "Agreement"], history_rows, "Live monitor history has not accumulated enough snapshots yet."),
            _table_section("Evidence service", "Most recent live windows", ["Line", "Host", "Event", "Baseline", "Apex", "Agreement", "Truth"], evidence_rows, "The live monitor does not have a reportable result yet."),
            _table_section("Appendix", "Raw evidence excerpts", ["Line", "Raw excerpt"], _appendix_rows(evidence_rows), "No raw excerpts were captured for this report."),
        ],
    )


def empty_report(report_type: str, title: str, message: str, source_label: str = "Source", source_value: str = "Unavailable", *, theme: str = "campus", renderer: str = "weasyprint") -> Dict[str, Any]:
    return _report_shell(
        report_type=report_type,
        title=title,
        subtitle=message,
        source_label=source_label,
        source_value=source_value,
        filename_stem=f"{report_type}_report",
        theme=theme,
        renderer=renderer,
        hero_metrics=[_hero_metric("Status", "Unavailable", message, tone="warn")],
        meta=[],
        sections=[{"eyebrow": "Availability", "title": "Report not ready", "kind": "message", "body": message}],
    )


def report_catalog(*, runs: Iterable[Dict[str, Any]], evaluation_cache: Dict[str, Any], live_status: Dict[str, Any], live_context: Optional[Dict[str, Any]], renderers: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    analysis_sources = [
        {"id": run.get("id"), "label": run.get("display_name") or run.get("filename", "Saved run"), "detail": f"{run.get('created_at', '-')} | {run.get('source', 'run')} | {run.get('mode', 'compare')}"}
        for run in runs
    ]
    evaluation_ready = evaluation_cache.get("state") == "ready" and bool(evaluation_cache.get("benchmark"))
    live_ready = bool((live_status or {}).get("result"))
    live_path = (live_status or {}).get("path") or (live_context or {}).get("sample_id") or "active session"
    return {
        "types": [
            {"id": "analysis", "label": "Analysis Report", "description": "An investigation report with evidence tables, wrapped appendix excerpts, and service-level summary blocks.", "sources": analysis_sources, "available": bool(analysis_sources)},
            {"id": "evaluation", "label": "Evaluation Report", "description": "A benchmark report with metric deltas, headline wins, and cross-host comparison folds.", "sources": [{"id": "latest", "label": "Latest benchmark snapshot", "detail": evaluation_cache.get("updated_at") or evaluation_cache.get("message", "Pending")}], "available": evaluation_ready},
            {"id": "live", "label": "Live Monitor Report", "description": "A live-operations snapshot with replay history, anomaly posture, and recent evidence windows.", "sources": [{"id": "current", "label": "Current live session", "detail": live_path}], "available": live_ready},
        ],
        "renderers": renderers,
    }
