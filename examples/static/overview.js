(function () {
  const ui = window.WorkbenchUI;
  const els = {
    bootstrapState: document.getElementById("bootstrapState"),
    bootstrapMessage: document.getElementById("bootstrapMessage"),
    evaluationState: document.getElementById("evaluationState"),
    evaluationMessage: document.getElementById("evaluationMessage"),
    liveState: document.getElementById("liveState"),
    liveHint: document.getElementById("liveHint"),
    adaptiveState: document.getElementById("adaptiveState"),
    adaptiveReason: document.getElementById("adaptiveReason"),
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
    recentRuns: document.getElementById("recentRuns"),
    viewCurrentRunLink: document.getElementById("viewCurrentRunLink"),
    overviewEvaluationHeadline: document.getElementById("overviewEvaluationHeadline"),
    overviewEvaluationDelta: document.getElementById("overviewEvaluationDelta"),
  };

  function renderStatus(status) {
    els.bootstrapState.textContent = status.bootstrap?.state || "unknown";
    els.bootstrapMessage.textContent = status.bootstrap?.message || "";
    els.evaluationState.textContent = status.evaluation?.state || "idle";
    els.evaluationMessage.textContent = status.evaluation?.message || "";
    els.liveState.textContent = status.live?.status || "idle";
    els.liveHint.textContent = status.live?.path || "Replay or manual path";

    const adaptive = status.adaptive || {};
    els.adaptiveState.textContent = adaptive.enabled ? `On | ${adaptive.threshold}` : `Off | ${adaptive.threshold}`;
    els.adaptiveReason.textContent = adaptive.reason || "";

    if (status.current_run && status.current_result) {
      ui.applyRunDetail(status.current_result, status.current_run, els);
      els.viewCurrentRunLink.href = status.current_run.detail_url;
    }

    ui.renderRunCards(els.recentRuns, status.recent_runs || [], "No runs saved yet.");
  }

  function renderEvaluation(payload) {
    const benchmark = payload?.benchmark;
    if (!benchmark) return;
    els.overviewEvaluationHeadline.textContent = `Apex Insight wins ${benchmark.headline?.improved_wins || 0} of ${benchmark.headline?.metric_count || 0} tracked metrics.`;
    const delta = benchmark.cross_host?.summary?.delta;
    els.overviewEvaluationDelta.textContent = delta === null || delta === undefined
      ? "Cross-host delta not ready yet."
      : `Cross-host delta: ${ui.score(delta)}.`;
  }

  async function refresh() {
    const [status, evaluation] = await Promise.all([
      ui.fetchJSON("/api/status"),
      ui.fetchJSON("/api/evaluation"),
    ]);
    renderStatus(status);
    renderEvaluation(evaluation);
  }

  refresh();
  setInterval(refresh, 8000);
})();
