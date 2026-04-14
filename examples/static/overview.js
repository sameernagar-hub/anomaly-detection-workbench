(function () {
  const ui = window.WorkbenchUI;
  const state = {
    currentStatus: null,
    currentEvaluation: null,
    slideIndex: 0,
  };
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
    slideTitle: document.getElementById("slideTitle"),
    slideMetric: document.getElementById("slideMetric"),
    slideMeta: document.getElementById("slideMeta"),
    slideBody: document.getElementById("slideBody"),
    slideDots: document.getElementById("slideDots"),
    slidePrev: document.getElementById("slidePrev"),
    slideNext: document.getElementById("slideNext"),
  };

  function buildSlides() {
    const slides = [];
    const status = state.currentStatus || {};
    const evaluation = state.currentEvaluation || {};
    const currentRun = status.current_run;
    const currentResult = status.current_result;
    const summary = currentResult?.summary;
    const benchmark = evaluation?.benchmark;
    const live = status.live;

    if (summary && currentRun) {
      slides.push({
        title: "Latest saved run",
        metric: `${summary.window_count || 0} windows`,
        meta: `${currentRun.filename} | ${ui.humanModeLabel(currentRun.mode)}`,
        body: `Baseline flagged ${summary.deeplog_anomalies || 0} anomalies, Apex Insight flagged ${summary.report_anomalies || 0}, and agreement is ${ui.pct(summary.agreement_rate)}.`,
      });
    }

    if (benchmark?.headline) {
      slides.push({
        title: "Evaluation snapshot",
        metric: `${benchmark.headline.improved_wins || 0}/${benchmark.headline.metric_count || 0}`,
        meta: "Tracked benchmark metrics",
        body: `Apex Insight accuracy is ${ui.score(benchmark.headline.improved_accuracy)} versus ${ui.score(benchmark.headline.baseline_accuracy)} for the baseline model.`,
      });
    }

    if (benchmark?.cross_host?.summary) {
      slides.push({
        title: "Cross-host result",
        metric: ui.score(benchmark.cross_host.summary.delta),
        meta: `${benchmark.cross_host.summary.fold_count || 0} proxy host folds`,
        body: `Average proxy-host accuracy changes from ${ui.score(benchmark.cross_host.summary.baseline_avg_accuracy)} to ${ui.score(benchmark.cross_host.summary.improved_avg_accuracy)}.`,
      });
    }

    if (live?.history?.length) {
      const latest = live.history[0];
      slides.push({
        title: "Latest live snapshot",
        metric: `${latest.line_count || 0} lines`,
        meta: latest.timestamp || "Live update",
        body: `The live monitor shows ${latest.deeplog_anomalies || 0} baseline anomalies, ${latest.report_anomalies || 0} improved-model anomalies, and ${ui.pct(latest.agreement_rate)} agreement.`,
      });
    }

    if (!slides.length) {
      slides.push({
        title: "Loading",
        metric: "Stand by",
        meta: "Waiting for status",
        body: "Slides will begin rotating after the current run, evaluation snapshot, or live-monitor data becomes available.",
      });
    }

    return slides;
  }

  function renderSlides() {
    if (!els.slideTitle || !els.slideMetric || !els.slideMeta || !els.slideBody || !els.slideDots) return;
    const slides = buildSlides();
    if (state.slideIndex >= slides.length) state.slideIndex = 0;
    const current = slides[state.slideIndex];
    els.slideTitle.textContent = current.title;
    els.slideMetric.textContent = current.metric;
    els.slideMeta.textContent = current.meta;
    els.slideBody.textContent = current.body;
    els.slideDots.innerHTML = slides.map((_, index) => `<button class="slide-dot ${index === state.slideIndex ? "active" : ""}" data-slide-index="${index}" aria-label="Go to slide ${index + 1}"></button>`).join("");
  }

  function advanceSlide(step) {
    const slides = buildSlides();
    state.slideIndex = (state.slideIndex + step + slides.length) % slides.length;
    renderSlides();
  }

  function bindSlideControls() {
    if (els.slidePrev) {
      els.slidePrev.addEventListener("click", () => advanceSlide(-1));
    }
    if (els.slideNext) {
      els.slideNext.addEventListener("click", () => advanceSlide(1));
    }
    if (els.slideDots) {
      els.slideDots.addEventListener("click", (event) => {
        const dot = event.target.closest("[data-slide-index]");
        if (!dot) return;
        state.slideIndex = Number(dot.dataset.slideIndex);
        renderSlides();
      });
    }
  }

  function renderStatus(status) {
    state.currentStatus = status;
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
    renderSlides();
  }

  function renderEvaluation(payload) {
    state.currentEvaluation = payload;
    const benchmark = payload?.benchmark;
    if (benchmark) {
      els.overviewEvaluationHeadline.textContent = `Apex Insight wins ${benchmark.headline?.improved_wins || 0} of ${benchmark.headline?.metric_count || 0} tracked metrics.`;
      const delta = benchmark.cross_host?.summary?.delta;
      els.overviewEvaluationDelta.textContent = delta === null || delta === undefined
        ? "Cross-host delta not ready yet."
        : `Cross-host delta: ${ui.score(delta)}.`;
    }
    renderSlides();
  }

  async function refresh() {
    const [status, evaluation] = await Promise.all([
      ui.fetchJSON("/api/status"),
      ui.fetchJSON("/api/evaluation"),
    ]);
    renderStatus(status);
    renderEvaluation(evaluation);
  }

  bindSlideControls();
  renderSlides();
  refresh();
  setInterval(() => advanceSlide(1), 4500);
  setInterval(refresh, 8000);
})();
