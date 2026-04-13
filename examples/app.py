from __future__ import annotations

import json
import threading
from collections import deque
from datetime import datetime
from pathlib import Path
import sys
from typing import Any, Deque, Dict, Optional

from flask import Flask, Response, jsonify, render_template_string, request
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from workbench import DEFAULT_UPLOAD_TEXT, AnomalyWorkbench, LiveMonitor, load_records_from_file, load_records_from_text


app = Flask(__name__)
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

workbench = AnomalyWorkbench(BASE_DIR)
live_monitor = LiveMonitor(workbench)

RECENT_REPORTS: Deque[Dict[str, Any]] = deque(maxlen=20)
CURRENT_REPORT: Dict[str, Any] = {
    "source": "bootstrap",
    "filename": "sample_unsw.log",
    "created_at": None,
    "mode": "compare",
    "result": None,
}

BOOTSTRAP_STATUS: Dict[str, Any] = {
    "state": "starting",
    "message": "Loading and training models...",
    "details": {},
}


def _set_current_report(source: str, filename: str, mode: str, result: Dict[str, Any]) -> None:
    report = {
        "source": source,
        "filename": filename,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "mode": mode,
        "result": result,
    }
    CURRENT_REPORT.update(report)
    RECENT_REPORTS.appendleft(
        {
            "source": source,
            "filename": filename,
            "created_at": report["created_at"],
            "mode": mode,
            "summary": result["summary"],
        }
    )


def bootstrap_models() -> None:
    try:
        details = workbench.ensure_ready()
        sample_result = workbench.predict_records(load_records_from_text(DEFAULT_UPLOAD_TEXT))
        _set_current_report("bootstrap", "sample_unsw.log", "compare", sample_result)
        BOOTSTRAP_STATUS["state"] = "ready"
        BOOTSTRAP_STATUS["message"] = "Models are ready."
        BOOTSTRAP_STATUS["details"] = details
    except Exception as exc:
        BOOTSTRAP_STATUS["state"] = "error"
        BOOTSTRAP_STATUS["message"] = str(exc)


def project_status() -> Dict[str, Any]:
    return {
        "bootstrap": BOOTSTRAP_STATUS,
        "artifacts": {
            "baseline_model": str(workbench.baseline_artifact_path),
            "report_model": str(workbench.report_model_path),
        },
        "adaptive": workbench.get_adaptive_status(),
        "live": live_monitor.status(),
        "recent_reports": list(RECENT_REPORTS),
        "current_report": CURRENT_REPORT,
    }


def apply_mode_filter(result: Dict[str, Any], mode: str) -> Dict[str, Any]:
    if mode == "compare":
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
        filtered_summary["active_model"] = "Baseline sequence model"
    elif mode == "report":
        filtered_summary["active_model"] = "Argument-aware report model"
    else:
        filtered_summary["active_model"] = "Compare both"

    return {
        "summary": filtered_summary,
        "items": filtered_items,
        "charts": result["charts"],
    }


def current_report_filename(extension: str) -> str:
    stem = Path(CURRENT_REPORT.get("filename") or "anomaly_report").stem
    return f"{stem}_{CURRENT_REPORT.get('mode', 'compare')}.{extension}"


@app.route("/")
def index() -> str:
    return render_template_string(
        """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Baseline vs Report Model Workbench</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    :root {
      --bg: #eef2e3;
      --panel: #fffdf7;
      --ink: #1d2a22;
      --muted: #53635a;
      --accent: #1f6f5f;
      --accent-soft: #d8efe8;
      --warn: #a43b2c;
      --warn-soft: #fde6df;
      --border: #d9e1d2;
      --shadow: 0 14px 34px rgba(46, 68, 54, 0.12);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background:
        radial-gradient(circle at top right, rgba(31, 111, 95, 0.12), transparent 28%),
        linear-gradient(180deg, #f6f9ef 0%, var(--bg) 100%);
      color: var(--ink);
      font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
    }
    .shell {
      width: min(1320px, calc(100% - 32px));
      margin: 24px auto 40px;
    }
    .hero, .panel, .table-card, .log-card {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 22px;
      box-shadow: var(--shadow);
    }
    .hero {
      padding: 28px;
      display: grid;
      grid-template-columns: 1.3fr 1fr;
      gap: 18px;
      margin-bottom: 18px;
    }
    .hero h1 {
      margin: 0 0 8px;
      font-size: clamp(1.9rem, 2.8vw, 3rem);
    }
    .hero p {
      margin: 0;
      color: var(--muted);
      line-height: 1.55;
    }
    .badge-row {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 16px;
    }
    .chip {
      background: var(--accent-soft);
      color: var(--accent);
      border-radius: 999px;
      padding: 8px 12px;
      font-size: 0.9rem;
      font-weight: 600;
    }
    .hero-status {
      background: linear-gradient(180deg, #f5fbf8 0%, #eef6f2 100%);
      border-radius: 18px;
      padding: 18px;
      border: 1px solid #d7ebe3;
    }
    .hero-status strong {
      display: block;
      margin-bottom: 8px;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 16px;
      margin-bottom: 18px;
    }
    .panel {
      padding: 18px;
    }
    .metric {
      font-size: 2rem;
      font-weight: 700;
      margin-top: 6px;
    }
    .muted {
      color: var(--muted);
    }
    .workspace {
      display: grid;
      grid-template-columns: 1.15fr 0.85fr;
      gap: 18px;
      margin-bottom: 18px;
    }
    .stack {
      display: grid;
      gap: 18px;
    }
    textarea, input[type="text"], select {
      width: 100%;
      border-radius: 14px;
      border: 1px solid #c6d3c6;
      background: #fcfdf9;
      color: var(--ink);
      padding: 12px 14px;
      font: inherit;
    }
    textarea {
      min-height: 220px;
      resize: vertical;
      line-height: 1.45;
    }
    .actions {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 12px;
    }
    button {
      border: 0;
      border-radius: 14px;
      padding: 11px 16px;
      cursor: pointer;
      font: inherit;
      font-weight: 700;
    }
    .primary {
      background: var(--accent);
      color: white;
    }
    .secondary {
      background: #ecf3eb;
      color: var(--ink);
    }
    .danger {
      background: var(--warn-soft);
      color: var(--warn);
    }
    .section-title {
      margin: 0 0 12px;
      font-size: 1.05rem;
    }
    .mini-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
    }
    .log-card {
      padding: 18px;
    }
    .bars {
      display: grid;
      gap: 10px;
      margin-top: 10px;
    }
    .bar-row {
      display: grid;
      grid-template-columns: 170px 1fr 56px;
      gap: 12px;
      align-items: center;
    }
    .bar {
      height: 12px;
      background: #e4ebe0;
      border-radius: 999px;
      overflow: hidden;
    }
    .fill {
      height: 100%;
      background: linear-gradient(90deg, #277765 0%, #79bfaa 100%);
      border-radius: 999px;
    }
    .timeline {
      display: grid;
      gap: 8px;
      margin-top: 12px;
      max-height: 260px;
      overflow: auto;
    }
    .timeline-row {
      display: grid;
      grid-template-columns: 70px 1fr 1fr 70px;
      gap: 10px;
      align-items: center;
      font-size: 0.92rem;
    }
    .spark {
      height: 10px;
      background: #e6ece2;
      border-radius: 999px;
      overflow: hidden;
    }
    .spark span {
      display: block;
      height: 100%;
      background: linear-gradient(90deg, #275f8c 0%, #7eb5df 100%);
      border-radius: 999px;
    }
    .spark.report span {
      background: linear-gradient(90deg, #9d4d1e 0%, #e5a565 100%);
    }
    .table-card {
      padding: 18px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.94rem;
    }
    th, td {
      padding: 10px 8px;
      border-bottom: 1px solid #ebefe7;
      text-align: left;
      vertical-align: top;
    }
    th {
      color: var(--muted);
      font-weight: 700;
      font-size: 0.82rem;
      letter-spacing: 0.03em;
      text-transform: uppercase;
    }
    code {
      white-space: pre-wrap;
      word-break: break-word;
      font-family: Consolas, "Courier New", monospace;
      font-size: 0.86rem;
    }
    .pill {
      display: inline-block;
      border-radius: 999px;
      padding: 5px 10px;
      font-size: 0.8rem;
      font-weight: 700;
    }
    .normal { background: #e4f4eb; color: #25624e; }
    .anomaly { background: #fde6df; color: #a43b2c; }
    .agree { background: #edf5ea; color: #375c2a; }
    .disagree { background: #fff0cb; color: #8c6418; }
    .status-box {
      margin-top: 12px;
      padding: 12px 14px;
      border-radius: 14px;
      background: #f4f8f0;
      border: 1px solid #dce7d5;
      color: var(--muted);
    }
    .recent-list {
      display: grid;
      gap: 10px;
      margin-top: 12px;
      max-height: 200px;
      overflow: auto;
    }
    .recent-item {
      border: 1px solid #e5ebe1;
      border-radius: 14px;
      padding: 10px 12px;
      background: #fcfdf9;
    }
    @media (max-width: 1100px) {
      .hero, .workspace { grid-template-columns: 1fr; }
      .grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    }
    @media (max-width: 720px) {
      .grid, .mini-grid { grid-template-columns: 1fr; }
      .bar-row, .timeline-row { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <div>
        <h1>Baseline vs Your Report Model</h1>
        <p>
          Upload UNSW-style traces, paste raw log text, or tail a live file path.
          The dashboard compares the baseline sequence model against an argument-aware
          sequence model so you can review the same windows from both perspectives.
        </p>
        <div class="badge-row">
          <div class="chip">UNSW-trained baseline</div>
          <div class="chip">Argument-aware comparison model</div>
          <div class="chip">Upload + live file monitoring</div>
        </div>
      </div>
      <div class="hero-status">
        <strong>System status</strong>
        <div id="bootstrapState">Loading...</div>
        <div class="muted" id="bootstrapMessage">Preparing artifacts...</div>
        <div class="muted" id="artifactInfo" style="margin-top:10px;">-</div>
      </div>
    </section>

    <section class="grid">
      <div class="panel">
        <div class="muted">Analyzed Windows</div>
        <div class="metric" id="metricWindows">0</div>
      </div>
      <div class="panel">
        <div class="muted">Baseline Anomalies</div>
        <div class="metric" id="metricDeep">0</div>
      </div>
      <div class="panel">
        <div class="muted">Report Model Anomalies</div>
        <div class="metric" id="metricReport">0</div>
      </div>
      <div class="panel">
        <div class="muted">Agreement Rate</div>
        <div class="metric" id="metricAgreement">0%</div>
      </div>
    </section>

    <section class="workspace">
      <div class="stack">
        <div class="panel">
          <h2 class="section-title">Upload Or Paste Logs</h2>
          <div class="mini-grid">
            <div>
              <label class="muted" for="analysisMode">View</label>
              <select id="analysisMode">
                <option value="compare">Compare Both</option>
                <option value="deeplog">Baseline Only</option>
                <option value="report">Report Model Only</option>
              </select>
            </div>
            <div>
              <label class="muted" for="uploadFile">Upload file</label>
              <input type="file" id="uploadFile" accept=".txt,.log,.csv">
            </div>
          </div>
          <div style="margin-top: 12px;">
            <label class="muted" for="logText">Or paste UNSW-style log lines</label>
            <textarea id="logText"></textarea>
          </div>
          <div class="actions">
            <button class="primary" id="analyzeTextBtn">Analyze Text</button>
            <button class="secondary" id="analyzeUploadBtn">Analyze Uploaded File</button>
            <button class="secondary" id="loadSampleBtn">Load Sample</button>
            <button class="secondary" id="exportCsvBtn">Export CSV</button>
            <button class="secondary" id="exportJsonBtn">Export JSON</button>
            <button class="secondary" id="exportHtmlBtn">Printable Report</button>
          </div>
          <div class="status-box" id="analysisStatus">Waiting for input.</div>
        </div>

        <div class="table-card">
          <h2 class="section-title">Window Review</h2>
          <div class="muted" style="margin-bottom: 10px;">Recent windows show raw line content, both anomaly scores, and where the models agree or diverge.</div>
          <div style="overflow:auto;">
            <table>
              <thead>
                <tr>
                  <th>Line</th>
                  <th>Event</th>
                  <th>Baseline</th>
                  <th>Report Model</th>
                  <th>Agreement</th>
                  <th>Truth</th>
                </tr>
              </thead>
              <tbody id="resultsBody"></tbody>
            </table>
          </div>
        </div>
      </div>

      <div class="stack">
        <div class="panel">
          <h2 class="section-title">Live File Monitoring</h2>
          <label class="muted" for="livePath">Absolute file path to tail on this machine</label>
          <input type="text" id="livePath" placeholder="C:\\path\\to\\trace.log">
          <div class="actions">
            <button class="primary" id="startLiveBtn">Start Live Mode</button>
            <button class="danger" id="stopLiveBtn">Stop</button>
            <button class="secondary" id="toggleAdaptiveBtn">Toggle Adaptive Threshold</button>
          </div>
          <div class="status-box" id="liveStatus">Live monitor idle.</div>
          <div class="status-box" id="adaptiveStatus">Adaptive threshold status will appear here.</div>
        </div>

        <div class="log-card">
          <h2 class="section-title">Comparison Snapshot</h2>
          <div class="bars" id="comparisonBars"></div>
        </div>

        <div class="log-card">
          <h2 class="section-title">Drift Monitor</h2>
          <div class="status-box" id="driftSummary">Drift monitoring will appear after analysis.</div>
          <div class="bars" id="driftBars"></div>
        </div>

        <div class="log-card">
          <h2 class="section-title">Score Timeline</h2>
          <div class="timeline" id="timelineRows"></div>
        </div>

        <div class="log-card">
          <h2 class="section-title">Recent Reports</h2>
          <div class="recent-list" id="recentReports"></div>
        </div>
      </div>
    </section>
  </div>

  <script>
    const sampleText = {{ sample_text|tojson }};

    function labelBadge(value) {
      if (value === null || value === undefined) return '<span class="pill">n/a</span>';
      return value === 1
        ? '<span class="pill anomaly">Anomaly</span>'
        : '<span class="pill normal">Normal</span>';
    }

    function agreementBadge(value) {
      if (value === null || value === undefined) return '<span class="pill">n/a</span>';
      return value
        ? '<span class="pill agree">Agree</span>'
        : '<span class="pill disagree">Disagree</span>';
    }

    function pct(value) {
      return `${Math.round((value || 0) * 100)}%`;
    }

    function renderReport(result, sourceLabel) {
      const summary = result.summary || {};
      document.getElementById('metricWindows').textContent = summary.window_count || 0;
      document.getElementById('metricDeep').textContent = summary.deeplog_anomalies || 0;
      document.getElementById('metricReport').textContent = summary.report_anomalies || 0;
      document.getElementById('metricAgreement').textContent = pct(summary.agreement_rate);

      document.getElementById('analysisStatus').textContent =
        `${sourceLabel} loaded. ${summary.window_count || 0} windows analyzed.`;

      const rows = (result.items || []).slice(0, 24).map(item => `
        <tr>
          <td>${item.line_number}</td>
          <td><code>${item.event}</code><br><span class="muted">${item.raw || ''}</span></td>
          <td>${labelBadge(item.deeplog_prediction)}<br><span class="muted">score ${item.deeplog_score ?? 'n/a'}</span></td>
          <td>${labelBadge(item.report_prediction)}<br><span class="muted">score ${item.report_score ?? 'n/a'}</span></td>
          <td>${agreementBadge(item.agreement)}</td>
          <td>${labelBadge(item.label)}<br><span class="muted">${item.attack_cat || ''}</span></td>
        </tr>
      `).join('');
      document.getElementById('resultsBody').innerHTML = rows || '<tr><td colspan="6">Not enough events yet. Add more lines to create windows.</td></tr>';

      const bars = (result.charts?.comparison || []).map(entry => {
        const maxValue = Math.max(...(result.charts.comparison || []).map(x => x.value || 0), 1);
        const width = ((entry.value || 0) / maxValue) * 100;
        return `
          <div class="bar-row">
            <div>${entry.label}</div>
            <div class="bar"><div class="fill" style="width:${width}%"></div></div>
            <div>${entry.value || 0}</div>
          </div>
        `;
      }).join('');
      document.getElementById('comparisonBars').innerHTML = bars || '<div class="muted">No comparison data yet.</div>';

      const drift = summary.drift || {};
      document.getElementById('driftSummary').textContent =
        `${drift.status || 'n/a'} | score shift ${drift.score_shift ?? 0} | anomaly-rate shift ${drift.anomaly_rate_shift ?? 0} | protocol shift ${drift.protocol_shift ?? 0}`;
      const adaptive = summary.adaptive_threshold || {};
      document.getElementById('adaptiveStatus').textContent =
        `Adaptive ${adaptive.enabled ? 'on' : 'off'} | threshold ${adaptive.threshold ?? 'n/a'} | base ${adaptive.base_threshold ?? 'n/a'} | ${adaptive.reason || ''}`;
      const driftBars = (result.charts?.drift || []).map(entry => {
        const width = Math.min(100, Math.max(6, (entry.value || 0) * 100));
        return `
          <div class="bar-row">
            <div>${entry.label}</div>
            <div class="bar"><div class="fill" style="width:${width}%"></div></div>
            <div>${entry.value || 0}</div>
          </div>
        `;
      }).join('');
      document.getElementById('driftBars').innerHTML = driftBars || '<div class="muted">Need more data for drift trends.</div>';

      const timeline = (result.charts?.timeline || []).slice(-18).reverse().map(entry => `
        <div class="timeline-row">
          <div>#${entry.line_number}</div>
          <div>
            <div class="muted">Baseline ${entry.deeplog}</div>
            <div class="spark"><span style="width:${Math.max(6, (entry.deeplog || 0) * 100)}%"></span></div>
          </div>
          <div>
            <div class="muted">Report ${entry.report}</div>
            <div class="spark report"><span style="width:${Math.max(6, (entry.report || 0) * 100)}%"></span></div>
          </div>
          <div>${labelBadge(entry.label)}</div>
        </div>
      `).join('');
      document.getElementById('timelineRows').innerHTML = timeline || '<div class="muted">Timeline will appear after analysis.</div>';
    }

    function renderStatus(status) {
      document.getElementById('bootstrapState').textContent = status.bootstrap.state || 'unknown';
      document.getElementById('bootstrapMessage').textContent = status.bootstrap.message || '';
      document.getElementById('artifactInfo').textContent =
        `Baseline artifact: ${status.artifacts.baseline_model} | Report artifact: ${status.artifacts.report_model}`;
      const adaptive = status.adaptive || {};
      document.getElementById('adaptiveStatus').textContent =
        `Adaptive ${adaptive.enabled ? 'on' : 'off'} | threshold ${adaptive.threshold ?? 'n/a'} | base ${adaptive.base_threshold ?? 'n/a'} | ${adaptive.reason || ''}`;

      const live = status.live || {};
      const livePath = live.path || 'No file selected';
      const liveTime = live.updated_at || 'not updated yet';
      document.getElementById('liveStatus').textContent =
        `${live.status || 'idle'} | ${livePath} | last update ${liveTime}`;

      const recent = (status.recent_reports || []).map(report => `
        <div class="recent-item">
          <strong>${report.filename}</strong><br>
          <span class="muted">${report.created_at} • ${report.mode}</span><br>
          <span class="muted">windows ${report.summary.window_count}, baseline ${report.summary.deeplog_anomalies}, report model ${report.summary.report_anomalies}</span>
        </div>
      `).join('');
      document.getElementById('recentReports').innerHTML = recent || '<div class="muted">No reports yet.</div>';

      if (status.current_report && status.current_report.result) {
        renderReport(status.current_report.result, status.current_report.filename || 'Current report');
      }
    }

    async function refreshStatus() {
      const response = await fetch('/api/status');
      const data = await response.json();
      renderStatus(data);
    }

    async function analyzeText() {
      const response = await fetch('/api/analyze/text', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: document.getElementById('logText').value,
          mode: document.getElementById('analysisMode').value
        })
      });
      const data = await response.json();
      renderReport(data.result, 'Pasted text');
      await refreshStatus();
    }

    async function analyzeUpload() {
      const fileInput = document.getElementById('uploadFile');
      if (!fileInput.files.length) {
        document.getElementById('analysisStatus').textContent = 'Choose a file first.';
        return;
      }
      const formData = new FormData();
      formData.append('file', fileInput.files[0]);
      formData.append('mode', document.getElementById('analysisMode').value);
      const response = await fetch('/api/analyze/upload', { method: 'POST', body: formData });
      const data = await response.json();
      renderReport(data.result, data.filename || 'Uploaded file');
      await refreshStatus();
    }

    async function startLive() {
      const response = await fetch('/api/live/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: document.getElementById('livePath').value })
      });
      const data = await response.json();
      document.getElementById('liveStatus').textContent = `${data.status} | ${data.path || 'no path'}`;
    }

    async function stopLive() {
      await fetch('/api/live/stop', { method: 'POST' });
      await refreshStatus();
    }

    async function toggleAdaptive() {
      const response = await fetch('/api/adaptive/toggle', { method: 'POST' });
      const data = await response.json();
      document.getElementById('adaptiveStatus').textContent =
        `Adaptive ${data.enabled ? 'on' : 'off'} | threshold ${data.threshold ?? 'n/a'} | base ${data.base_threshold ?? 'n/a'} | ${data.reason || ''}`;
      await refreshStatus();
    }

    async function pollLive() {
      const response = await fetch('/api/live/status');
      const data = await response.json();
      const status = data.status || {};
      document.getElementById('liveStatus').textContent =
        `${status.status || 'idle'} | ${status.path || 'No file selected'} | last update ${status.updated_at || 'not updated yet'}`;
      if (status.result) {
        renderReport(status.result, 'Live monitor');
      }
    }

    document.getElementById('analyzeTextBtn').addEventListener('click', analyzeText);
    document.getElementById('analyzeUploadBtn').addEventListener('click', analyzeUpload);
    document.getElementById('startLiveBtn').addEventListener('click', startLive);
    document.getElementById('stopLiveBtn').addEventListener('click', stopLive);
    document.getElementById('toggleAdaptiveBtn').addEventListener('click', toggleAdaptive);
    document.getElementById('loadSampleBtn').addEventListener('click', () => {
      document.getElementById('logText').value = sampleText;
    });
    document.getElementById('exportCsvBtn').addEventListener('click', () => {
      window.open('/api/report/export.csv', '_blank');
    });
    document.getElementById('exportJsonBtn').addEventListener('click', () => {
      window.open('/api/report/export.json', '_blank');
    });
    document.getElementById('exportHtmlBtn').addEventListener('click', () => {
      window.open('/api/report/export.html', '_blank');
    });

    document.getElementById('logText').value = sampleText;
    refreshStatus();
    setInterval(refreshStatus, 6000);
    setInterval(pollLive, 3000);
  </script>
</body>
</html>
        """,
        sample_text=DEFAULT_UPLOAD_TEXT,
    )


@app.route("/api/status")
def api_status():
    return jsonify(project_status())


@app.route("/api/analyze/text", methods=["POST"])
def api_analyze_text():
    payload = request.get_json(force=True)
    text = payload.get("text", "")
    mode = payload.get("mode", "compare")
    records = load_records_from_text(text)
    result = apply_mode_filter(workbench.predict_records(records), mode)
    _set_current_report("text", "pasted_text.log", mode, result)
    return jsonify({"result": result})


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
    _set_current_report("upload", filename, mode, result)
    return jsonify({"filename": filename, "result": result})


@app.route("/api/live/start", methods=["POST"])
def api_live_start():
    payload = request.get_json(force=True)
    path = str(payload.get("path", "")).strip()
    if not path:
        return jsonify({"error": "Path is required."}), 400
    return jsonify(live_monitor.start(path))


@app.route("/api/live/stop", methods=["POST"])
def api_live_stop():
    return jsonify(live_monitor.stop())


@app.route("/api/live/status")
def api_live_status():
    return jsonify({"status": live_monitor.status()})


@app.route("/api/adaptive/status")
def api_adaptive_status():
    return jsonify(workbench.get_adaptive_status())


@app.route("/api/adaptive/toggle", methods=["POST"])
def api_adaptive_toggle():
    enabled = not workbench.get_adaptive_status().get("enabled", True)
    return jsonify(workbench.set_adaptive_thresholding(enabled))


@app.route("/api/report/export.json")
def api_report_export_json():
    payload = json.dumps(CURRENT_REPORT, indent=2)
    return Response(
        payload,
        mimetype="application/json",
        headers={"Content-Disposition": f"attachment; filename={current_report_filename('json')}"},
    )


@app.route("/api/report/export.csv")
def api_report_export_csv():
    result = CURRENT_REPORT.get("result") or {"summary": {}, "items": [], "charts": {}}
    payload = workbench.export_report_csv(result)
    return Response(
        payload,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={current_report_filename('csv')}"},
    )


@app.route("/api/report/export.html")
def api_report_export_html():
    result = CURRENT_REPORT.get("result") or {"summary": {}, "items": [], "charts": {}}
    payload = workbench.export_report_html(
        result,
        title=f"Anomaly Report: {CURRENT_REPORT.get('filename', 'Current Report')}",
    )
    return Response(
        payload,
        mimetype="text/html",
        headers={"Content-Disposition": f"attachment; filename={current_report_filename('html')}"},
    )


if __name__ == "__main__":
    bootstrap_thread = threading.Thread(target=bootstrap_models, daemon=True)
    bootstrap_thread.start()
    app.run(host="127.0.0.1", port=5000, debug=True)
