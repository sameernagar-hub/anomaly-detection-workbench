(function () {
  const ui = window.WorkbenchUI;
  const els = {
    refreshEvaluation: document.getElementById("refreshEvaluation"),
    evaluationHeadline: document.getElementById("evaluationHeadline"),
    evaluationMessage: document.getElementById("evaluationMessage"),
    evalBaselineAccuracy: document.getElementById("evalBaselineAccuracy"),
    evalImprovedAccuracy: document.getElementById("evalImprovedAccuracy"),
    evalMetricWins: document.getElementById("evalMetricWins"),
    evalCrossDelta: document.getElementById("evalCrossDelta"),
    metricRows: document.getElementById("metricRows"),
    foldRows: document.getElementById("foldRows"),
  };

  function render(payload) {
    els.evaluationMessage.textContent = payload?.message || "";
    const benchmark = payload?.benchmark;
    if (!benchmark) {
      els.evaluationHeadline.textContent = "Waiting for benchmark snapshot.";
      return;
    }

    const headline = benchmark.headline || {};
    els.evaluationHeadline.textContent = `Apex Insight wins ${headline.improved_wins || 0} of ${headline.metric_count || 0} tracked metrics`;
    els.evalBaselineAccuracy.textContent = headline.baseline_accuracy !== null && headline.baseline_accuracy !== undefined ? ui.score(headline.baseline_accuracy) : "-";
    els.evalImprovedAccuracy.textContent = headline.improved_accuracy !== null && headline.improved_accuracy !== undefined ? ui.score(headline.improved_accuracy) : "-";
    els.evalMetricWins.textContent = `${headline.improved_wins || 0}/${headline.metric_count || 0}`;
    const crossDelta = benchmark.cross_host?.summary?.delta;
    els.evalCrossDelta.textContent = crossDelta !== null && crossDelta !== undefined ? ui.score(crossDelta) : "-";

    els.metricRows.innerHTML = (benchmark.standard?.metric_rows || []).map((row) => `
      <div class="metric-row">
        <header>
          <strong>${row.metric.replaceAll("_", " ")}</strong>
          <span class="${row.delta !== null && row.delta !== undefined && row.delta < 0 ? "delta negative" : "delta"}">${row.delta === null || row.delta === undefined ? "-" : ui.score(row.delta)}</span>
        </header>
        <div class="muted">Baseline ${ui.score(row.baseline)}</div>
        <div class="progress-track"><div class="progress-fill" style="width:${Math.max(4, Number(row.baseline || 0) * 100)}%"></div></div>
        <div class="muted">Improved ${ui.score(row.improved)}</div>
        <div class="progress-track"><div class="progress-fill-alt" style="width:${Math.max(4, Number(row.improved || 0) * 100)}%"></div></div>
      </div>
    `).join("");

    els.foldRows.innerHTML = (benchmark.cross_host?.folds || []).map((fold) => `
      <div class="fold-row">
        <header>
          <strong>${fold.host_group}</strong>
          <span>${fold.record_count} records</span>
        </header>
        <div class="muted">Baseline accuracy ${ui.score(fold.deeplog_accuracy)}</div>
        <div class="progress-track"><div class="progress-fill" style="width:${Math.max(4, Number(fold.deeplog_accuracy || 0) * 100)}%"></div></div>
        <div class="muted">Improved accuracy ${ui.score(fold.report_accuracy)}</div>
        <div class="progress-track"><div class="progress-fill-alt" style="width:${Math.max(4, Number(fold.report_accuracy || 0) * 100)}%"></div></div>
      </div>
    `).join("") || '<div class="report-card muted">Cross-host proxy folds are still warming up.</div>';
  }

  async function refresh() {
    try {
      const payload = await ui.fetchJSON("/api/evaluation");
      render(payload);
    } catch (error) {
      els.evaluationHeadline.textContent = "Evaluation snapshot unavailable.";
      els.evaluationMessage.textContent = error.message || "Unable to refresh evaluation right now.";
    }
  }

  els.refreshEvaluation.addEventListener("click", refresh);
  refresh();
  setInterval(refresh, 15000);
})();
