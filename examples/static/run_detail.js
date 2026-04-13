(function () {
  const ui = window.WorkbenchUI;
  const runId = ui.bootstrap.run_id;
  const els = {
    runTitle: document.getElementById("runTitle"),
    runMeta: document.getElementById("runMeta"),
    runContext: document.getElementById("runContext"),
    metricWindows: document.getElementById("metricWindows"),
    metricBaselineAnomalies: document.getElementById("metricBaselineAnomalies"),
    metricImprovedAnomalies: document.getElementById("metricImprovedAnomalies"),
    metricAgreement: document.getElementById("metricAgreement"),
    metricImprovedAccuracy: document.getElementById("metricImprovedAccuracy"),
    currentReportName: document.getElementById("currentReportName"),
    currentReportMode: document.getElementById("currentReportMode"),
    latestBaselineScore: document.getElementById("latestBaselineScore"),
    latestBaselineVerdict: document.getElementById("latestBaselineVerdict"),
    latestImprovedScore: document.getElementById("latestImprovedScore"),
    latestImprovedVerdict: document.getElementById("latestImprovedVerdict"),
    driftStatus: document.getElementById("driftStatus"),
    driftMessage: document.getElementById("driftMessage"),
    trendChart: document.getElementById("trendChart"),
    rowFilter: document.getElementById("rowFilter"),
    hostFilter: document.getElementById("hostFilter"),
    rowCountLabel: document.getElementById("rowCountLabel"),
    resultsBody: document.getElementById("resultsBody"),
    exportCsvBtn: document.getElementById("exportCsvBtn"),
    exportJsonBtn: document.getElementById("exportJsonBtn"),
    exportHtmlBtn: document.getElementById("exportHtmlBtn"),
  };

  let items = [];

  function renderRun(run) {
    const result = run.result || {};
    items = result.items || [];
    ui.applyRunDetail(result, run, els);
    ui.renderTrendChart(els.trendChart, result);
    ui.populateHostFilter(els.hostFilter, items);
    ui.renderResultsTable(items, els);

    els.runTitle.textContent = `${run.filename} (${ui.humanModeLabel(run.mode)})`;
    els.runMeta.innerHTML = `
      <article class="runway-tile"><span>Run ID</span><strong>${run.id}</strong><small>Persistent saved result</small></article>
      <article class="runway-tile"><span>Created</span><strong>${run.created_at || "-"}</strong><small>${run.source}</small></article>
      <article class="runway-tile"><span>Windows</span><strong>${run.summary?.window_count || 0}</strong><small>Frozen chart + table</small></article>
      <article class="runway-tile"><span>Mode</span><strong>${ui.humanModeLabel(run.mode)}</strong><small>Viewing filter used when saved</small></article>
    `;

    const metadata = run.metadata || {};
    els.runContext.innerHTML = Object.keys(metadata).length
      ? Object.entries(metadata).map(([key, value]) => `<div class="report-card"><strong>${key}</strong><div class="muted">${value}</div></div>`).join("")
      : '<div class="report-card muted">No additional metadata was recorded for this run.</div>';

    els.exportCsvBtn.addEventListener("click", () => ui.openExport(`/api/report/export.csv?run_id=${run.id}`));
    els.exportJsonBtn.addEventListener("click", () => ui.openExport(`/api/report/export.json?run_id=${run.id}`));
    els.exportHtmlBtn.addEventListener("click", () => ui.openExport(`/api/report/export.html?run_id=${run.id}`));
  }

  async function refresh() {
    const data = await ui.fetchJSON(`/api/runs/${runId}`);
    renderRun(data.run);
  }

  els.rowFilter.addEventListener("change", () => ui.renderResultsTable(items, els));
  els.hostFilter.addEventListener("change", () => ui.renderResultsTable(items, els));
  refresh();
})();
