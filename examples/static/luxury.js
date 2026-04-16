(function () {
  const bootstrap = JSON.parse(document.getElementById("bootstrap-data").textContent);
  const state = {
    currentResult: null,
    currentItems: [],
    currentStatus: null,
    currentEvaluation: null,
    sampleCatalog: bootstrap.sample_catalog || [],
    featuredSample: bootstrap.featured_sample || null,
    evaluationFocus: false,
    slideIndex: 0,
    slideTimer: null,
    theme: localStorage.getItem("adw-theme") || "campus",
  };

  const els = {
    body: document.body,
    logText: document.getElementById("logText"),
    analysisMode: document.getElementById("analysisMode"),
    analysisStatus: document.getElementById("analysisStatus"),
    resultsBody: document.getElementById("resultsBody"),
    rowFilter: document.getElementById("rowFilter"),
    hostFilter: document.getElementById("hostFilter"),
    rowCountLabel: document.getElementById("rowCountLabel"),
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
    comparisonBars: document.getElementById("comparisonBars"),
    driftBars: document.getElementById("driftBars"),
    recentReports: document.getElementById("recentReports"),
    liveStatus: document.getElementById("liveStatus"),
    replayStatus: document.getElementById("replayStatus"),
    liveState: document.getElementById("liveState"),
    liveHint: document.getElementById("liveHint"),
    livePath: document.getElementById("livePath"),
    pathList: document.getElementById("pathList"),
    bootstrapState: document.getElementById("bootstrapState"),
    bootstrapMessage: document.getElementById("bootstrapMessage"),
    evaluationState: document.getElementById("evaluationState"),
    evaluationMessage: document.getElementById("evaluationMessage"),
    adaptiveState: document.getElementById("adaptiveState"),
    adaptiveReason: document.getElementById("adaptiveReason"),
    scenarioGrid: document.getElementById("scenarioGrid"),
    trendChart: document.getElementById("trendChart"),
    evaluationHeadline: document.getElementById("evaluationHeadline"),
    evalBaselineAccuracy: document.getElementById("evalBaselineAccuracy"),
    evalImprovedAccuracy: document.getElementById("evalImprovedAccuracy"),
    evalMetricWins: document.getElementById("evalMetricWins"),
    evalCrossDelta: document.getElementById("evalCrossDelta"),
    metricRows: document.getElementById("metricRows"),
    foldRows: document.getElementById("foldRows"),
    slideTitle: document.getElementById("slideTitle"),
    slideMeta: document.getElementById("slideMeta"),
    slideBody: document.getElementById("slideBody"),
    slideMetric: document.getElementById("slideMetric"),
    slideDots: document.getElementById("slideDots"),
    themeSelect: document.getElementById("themeSelect"),
    navLinks: Array.from(document.querySelectorAll(".nav-link")),
    focusPanels: Array.from(document.querySelectorAll(".focus-panel")),
  };

  function pct(value) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
    return `${Math.round(Number(value) * 100)}%`;
  }

  function score(value) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
    return Number(value).toFixed(3);
  }

  function badgeForLabel(value, positiveLabel = "Anomaly", negativeLabel = "Normal") {
    if (value === null || value === undefined) return '<span class="badge neutral">n/a</span>';
    if (Number(value) === 1) return `<span class="badge anomaly">${positiveLabel}</span>`;
    return `<span class="badge normal">${negativeLabel}</span>`;
  }

  function agreementBadge(value) {
    if (value === null || value === undefined) return '<span class="badge neutral">n/a</span>';
    return value ? '<span class="badge normal">Aligned</span>' : '<span class="badge warn">Diverged</span>';
  }

  function humanModeLabel(mode) {
    if (mode === "deeplog") return "Baseline Sentinel only";
    if (mode === "report") return "Apex Insight only";
    return "Dual Command View";
  }

  function setTheme(theme) {
    state.theme = theme;
    els.body.dataset.theme = theme;
    els.themeSelect.value = theme;
    localStorage.setItem("adw-theme", theme);
  }

  function renderScenarioGrid() {
    els.scenarioGrid.innerHTML = state.sampleCatalog.map((sample) => `
      <article class="scenario-card">
        <div>
          <div class="eyebrow">${sample.eyebrow}</div>
          <h3>${sample.title}</h3>
        </div>
        <p>${sample.description}</p>
        <div class="tag-list">${sample.tags.map((tag) => `<span>${tag}</span>`).join("")}</div>
        <div class="muted mono">${sample.line_count} lines</div>
        <div class="control-row wrap">
          <button class="ghost" data-action="load-sample" data-sample="${sample.id}">Load text</button>
          <button class="primary" data-action="analyze-sample" data-sample="${sample.id}">Analyze</button>
          <button class="ghost" data-action="replay-sample" data-sample="${sample.id}">Replay</button>
          <a class="ghost" href="/api/demo/sample/${sample.id}/download">Download</a>
        </div>
      </article>
    `).join("");
  }

  function renderPathList() {
    els.pathList.innerHTML = state.sampleCatalog.map((sample) => `
      <div class="path-card">
        <strong>${sample.title}</strong>
        <div class="mono muted">${sample.path}</div>
        <div class="control-row wrap">
          <button class="ghost" data-action="use-path" data-path="${sample.path}">Use path</button>
          <button class="ghost" data-action="replay-sample" data-sample="${sample.id}">Replay</button>
        </div>
      </div>
    `).join("");
  }

  function renderBarList(target, rows, formatter = (value) => value) {
    if (!rows || !rows.length) {
      target.innerHTML = '<div class="report-card muted">No data yet.</div>';
      return;
    }
    const max = Math.max(...rows.map((row) => Number(row.value || 0)), 1);
    target.innerHTML = rows.map((row) => `
      <div class="bar-row">
        <header>
          <strong>${row.label}</strong>
          <span>${formatter(row.value)}</span>
        </header>
        <div class="progress-track">
          <div class="progress-fill-alt" style="width:${Math.max(5, (Number(row.value || 0) / max) * 100)}%"></div>
        </div>
      </div>
    `).join("");
  }

  function updateHostFilter(items) {
    const selected = els.hostFilter.value;
    const hosts = ["all"].concat([...new Set((items || []).map((item) => item.host_group).filter(Boolean))].sort());
    els.hostFilter.innerHTML = hosts.map((host) => `<option value="${host}">${host === "all" ? "All hosts" : host}</option>`).join("");
    if (hosts.includes(selected)) els.hostFilter.value = selected;
  }

  function filteredItems() {
    const rows = state.currentItems || [];
    const filter = els.rowFilter.value;
    const host = els.hostFilter.value;
    return rows.filter((item) => {
      if (host !== "all" && item.host_group !== host) return false;
      if (filter === "anomaly") return Number(item.deeplog_prediction) === 1 || Number(item.report_prediction) === 1;
      if (filter === "disagreement") return item.agreement === false;
      if (filter === "truth-attack") return Number(item.label) === 1;
      return true;
    });
  }

  function renderTable() {
    const items = filteredItems();
    els.rowCountLabel.textContent = `${items.length} windows`;
    if (!items.length) {
      els.resultsBody.innerHTML = '<tr><td colspan="7" class="muted">No windows match the active filter.</td></tr>';
      return;
    }
    els.resultsBody.innerHTML = items.slice(0, 64).map((item) => `
      <tr>
        <td>${item.line_number}</td>
        <td>${item.host_group || "unknown"}</td>
        <td><code>${item.event}</code><div class="muted">${item.raw || ""}</div></td>
        <td>${badgeForLabel(item.deeplog_prediction)}<div class="muted">score ${score(item.deeplog_score)}</div></td>
        <td>${badgeForLabel(item.report_prediction)}<div class="muted">score ${score(item.report_score)}</div></td>
        <td>${agreementBadge(item.agreement)}</td>
        <td>${badgeForLabel(item.label, "Attack", "Normal")}<div class="muted">${item.attack_cat || ""}</div></td>
      </tr>
    `).join("");
  }

  function themeColor(name) {
    return getComputedStyle(document.body).getPropertyValue(name).trim();
  }

  function drawTrendChart(result) {
    const timeline = (result?.charts?.timeline || []).slice(-18);
    const width = 760;
    const height = 280;
    const left = 54;
    const right = 18;
    const top = 20;
    const bottom = 38;
    const plotWidth = width - left - right;
    const plotHeight = height - top - bottom;

    if (!timeline.length) {
      els.trendChart.innerHTML = '<text x="28" y="144" fill="rgba(100,100,100,0.7)">Need more windows for a trend graph.</text>';
      return;
    }

    function pointX(index) {
      return left + (index / Math.max(1, timeline.length - 1)) * plotWidth;
    }

    function pointY(value) {
      return top + (1 - Number(value || 0)) * plotHeight;
    }

    const baseline = [];
    const improved = [];
    const truthCircles = [];
    const labels = [];

    timeline.forEach((entry, index) => {
      const x = pointX(index);
      baseline.push(`${x},${pointY(entry.deeplog)}`);
      improved.push(`${x},${pointY(entry.report)}`);
      labels.push(`<text x="${x}" y="${height - 12}" text-anchor="middle" fill="${themeColor("--muted")}" font-size="11">${entry.line_number}</text>`);
      if (Number(entry.label) === 1) {
        truthCircles.push(`<circle cx="${x}" cy="${pointY(Math.max(entry.deeplog, entry.report)) - 9}" r="4" fill="${themeColor("--warn")}"></circle>`);
      }
    });

    const improvedArea = `${left},${height - bottom} ${improved.join(" ")} ${left + plotWidth},${height - bottom}`;
    const baselineArea = `${left},${height - bottom} ${baseline.join(" ")} ${left + plotWidth},${height - bottom}`;
    const gridLines = [0, 0.25, 0.5, 0.75, 1].map((ratio) => {
      const y = pointY(ratio);
      return `
        <line x1="${left}" y1="${y}" x2="${left + plotWidth}" y2="${y}" stroke="${themeColor("--line")}" stroke-dasharray="4 6"></line>
        <text x="18" y="${y + 4}" fill="${themeColor("--muted")}" font-size="11">${ratio.toFixed(2)}</text>
      `;
    }).join("");

    const markers = improved.map((point) => {
      const [x, y] = point.split(",");
      return `<circle cx="${x}" cy="${y}" r="3" fill="${themeColor("--accent-alt")}"></circle>`;
    }).join("");

    els.trendChart.innerHTML = `
      <defs>
        <linearGradient id="baselineArea" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stop-color="${themeColor("--accent")}" stop-opacity="0.22"></stop>
          <stop offset="100%" stop-color="${themeColor("--accent")}" stop-opacity="0.02"></stop>
        </linearGradient>
        <linearGradient id="improvedArea" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stop-color="${themeColor("--accent-alt")}" stop-opacity="0.22"></stop>
          <stop offset="100%" stop-color="${themeColor("--accent-alt")}" stop-opacity="0.03"></stop>
        </linearGradient>
      </defs>
      ${gridLines}
      <polygon points="${baselineArea}" fill="url(#baselineArea)"></polygon>
      <polygon points="${improvedArea}" fill="url(#improvedArea)"></polygon>
      <polyline fill="none" stroke="${themeColor("--accent")}" stroke-width="3" points="${baseline.join(" ")}"></polyline>
      <polyline fill="none" stroke="${themeColor("--accent-alt")}" stroke-width="3" points="${improved.join(" ")}"></polyline>
      ${markers}
      ${truthCircles.join("")}
      ${labels.join("")}
      <line x1="${left}" y1="${height - bottom}" x2="${left + plotWidth}" y2="${height - bottom}" stroke="${themeColor("--line-strong")}"></line>
      <line x1="${left}" y1="${top}" x2="${left}" y2="${height - bottom}" stroke="${themeColor("--line-strong")}"></line>
    `;
  }

  function renderReport(result, sourceLabel, modeLabel) {
    state.currentResult = result;
    state.currentItems = result.items || [];
    updateHostFilter(state.currentItems);
    renderTable();
    drawTrendChart(result);
    renderSlides();

    const summary = result.summary || {};
    const lastItem = state.currentItems[state.currentItems.length - 1];

    els.metricWindows.textContent = summary.window_count || 0;
    els.metricBaselineAnomalies.textContent = summary.deeplog_anomalies || 0;
    els.metricImprovedAnomalies.textContent = summary.report_anomalies || 0;
    els.metricAgreement.textContent = pct(summary.agreement_rate);
    els.metricImprovedAccuracy.textContent = summary.report_vs_label_accuracy !== null && summary.report_vs_label_accuracy !== undefined ? score(summary.report_vs_label_accuracy) : "-";

    els.currentReportName.textContent = sourceLabel || "Current report";
    els.currentReportMode.textContent = modeLabel || summary.active_model || "Dual Command View";

    els.latestBaselineScore.textContent = lastItem ? score(lastItem.deeplog_score) : "-";
    els.latestBaselineVerdict.innerHTML = lastItem ? badgeForLabel(lastItem.deeplog_prediction) : "Awaiting prediction";
    els.latestImprovedScore.textContent = lastItem ? score(lastItem.report_score) : "-";
    els.latestImprovedVerdict.innerHTML = lastItem ? badgeForLabel(lastItem.report_prediction) : "Awaiting prediction";

    const drift = summary.drift || {};
    els.driftStatus.textContent = drift.status || "n/a";
    els.driftMessage.textContent = drift.message || "Need analysis to evaluate drift.";

    renderBarList(els.comparisonBars, result.charts?.comparison || []);
    renderBarList(els.driftBars, result.charts?.drift || [], score);
    els.analysisStatus.textContent = `${sourceLabel} analyzed in ${modeLabel || summary.active_model || "dual"} mode. ${summary.window_count || 0} windows ready.`;
  }

  function renderRecentReports(recentReports) {
    if (!recentReports || !recentReports.length) {
      els.recentReports.innerHTML = '<div class="report-card muted">No reports yet.</div>';
      return;
    }
    els.recentReports.innerHTML = recentReports.map((report) => `
      <div class="report-card">
        <strong>${report.filename}</strong>
        <div class="muted">${report.created_at} | ${report.mode}</div>
        <div class="muted">windows ${report.summary.window_count || 0} | baseline ${report.summary.deeplog_anomalies || 0} | improved ${report.summary.report_anomalies || 0}</div>
      </div>
    `).join("");
  }

  function renderStatus(status) {
    state.currentStatus = status;
    els.bootstrapState.textContent = status.bootstrap?.state || "unknown";
    els.bootstrapMessage.textContent = status.bootstrap?.message || "";
    els.evaluationState.textContent = status.evaluation?.state || "idle";
    els.evaluationMessage.textContent = status.evaluation?.message || "";

    const adaptive = status.adaptive || {};
    els.adaptiveState.textContent = adaptive.enabled ? `On | ${adaptive.threshold}` : `Off | ${adaptive.threshold}`;
    els.adaptiveReason.textContent = adaptive.reason || "";

    els.liveState.textContent = status.live?.status || "idle";
    els.liveHint.textContent = status.live?.path || "Replay or manual path";
    els.liveStatus.textContent = `${status.live?.status || "idle"} | ${status.live?.path || "No path selected"} | ${status.live?.updated_at || "not updated yet"}`;

    const replay = status.replay || {};
    els.replayStatus.textContent = `${replay.state || "idle"} | ${replay.message || "Replay idle."}`;

    renderRecentReports(status.recent_reports || []);
    if (status.current_report?.result) {
      renderReport(status.current_report.result, status.current_report.filename, humanModeLabel(status.current_report.mode));
    } else {
      renderSlides();
    }
  }

  function renderEvaluation(payload) {
    state.currentEvaluation = payload;
    els.evaluationState.textContent = payload?.state || "idle";
    els.evaluationMessage.textContent = payload?.message || "";
    const benchmark = payload?.benchmark;
    if (!benchmark) {
      renderSlides();
      return;
    }

    const headline = benchmark.headline || {};
    els.evaluationHeadline.textContent = `Apex Insight wins ${headline.improved_wins || 0} of ${headline.metric_count || 0} tracked metrics`;
    els.evalBaselineAccuracy.textContent = headline.baseline_accuracy !== null && headline.baseline_accuracy !== undefined ? score(headline.baseline_accuracy) : "-";
    els.evalImprovedAccuracy.textContent = headline.improved_accuracy !== null && headline.improved_accuracy !== undefined ? score(headline.improved_accuracy) : "-";
    els.evalMetricWins.textContent = `${headline.improved_wins || 0}/${headline.metric_count || 0}`;
    const crossDelta = benchmark.cross_host?.summary?.delta;
    els.evalCrossDelta.textContent = crossDelta !== null && crossDelta !== undefined ? score(crossDelta) : "-";

    els.metricRows.innerHTML = (benchmark.standard?.metric_rows || []).map((row) => `
      <div class="metric-row">
        <header>
          <strong>${row.metric.replaceAll("_", " ")}</strong>
          <span class="${row.delta !== null && row.delta !== undefined && row.delta < 0 ? "delta negative" : "delta"}">${row.delta === null || row.delta === undefined ? "-" : score(row.delta)}</span>
        </header>
        <div class="muted">Baseline ${score(row.baseline)}</div>
        <div class="progress-track"><div class="progress-fill" style="width:${Math.max(4, Number(row.baseline || 0) * 100)}%"></div></div>
        <div class="muted">Improved ${score(row.improved)}</div>
        <div class="progress-track"><div class="progress-fill-alt" style="width:${Math.max(4, Number(row.improved || 0) * 100)}%"></div></div>
      </div>
    `).join("");

    els.foldRows.innerHTML = (benchmark.cross_host?.folds || []).map((fold) => `
      <div class="fold-row">
        <header>
          <strong>${fold.host_group}</strong>
          <span>${fold.record_count} records</span>
        </header>
        <div class="muted">Baseline accuracy ${score(fold.deeplog_accuracy)}</div>
        <div class="progress-track"><div class="progress-fill" style="width:${Math.max(4, Number(fold.deeplog_accuracy || 0) * 100)}%"></div></div>
        <div class="muted">Improved accuracy ${score(fold.report_accuracy)}</div>
        <div class="progress-track"><div class="progress-fill-alt" style="width:${Math.max(4, Number(fold.report_accuracy || 0) * 100)}%"></div></div>
      </div>
    `).join("") || '<div class="report-card muted">Cross-host proxy folds are still warming up.</div>';

    renderSlides();
  }

  function buildSlides() {
    const slides = [];
    const reportSummary = state.currentResult?.summary;
    const benchmark = state.currentEvaluation?.benchmark;
    const live = state.currentStatus?.live;
    const recentReport = state.currentStatus?.recent_reports?.[0];

    if (reportSummary) {
      slides.push({
        title: "Current sample",
        metric: `${reportSummary.window_count || 0} windows`,
        meta: `${state.currentStatus?.current_report?.filename || "Current report"} | ${humanModeLabel(state.currentStatus?.current_report?.mode)}`,
        body: `Baseline flagged ${reportSummary.deeplog_anomalies || 0} anomalies, Apex Insight flagged ${reportSummary.report_anomalies || 0}, and agreement is ${pct(reportSummary.agreement_rate)}.`,
      });
    }
    if (benchmark?.headline) {
      slides.push({
        title: "Evaluation summary",
        metric: `${benchmark.headline.improved_wins || 0}/${benchmark.headline.metric_count || 0}`,
        meta: "Tracked benchmark metrics",
        body: `Apex Insight accuracy is ${score(benchmark.headline.improved_accuracy)} versus ${score(benchmark.headline.baseline_accuracy)} for the baseline model.`,
      });
    }
    if (benchmark?.cross_host?.summary) {
      slides.push({
        title: "Cross-host proxy result",
        metric: `${score(benchmark.cross_host.summary.delta)}`,
        meta: `${benchmark.cross_host.summary.fold_count || 0} evaluated folds`,
        body: `Average proxy-host accuracy improves from ${score(benchmark.cross_host.summary.baseline_avg_accuracy)} to ${score(benchmark.cross_host.summary.improved_avg_accuracy)}.`,
      });
    }
    if (live?.history?.length) {
      const latest = live.history[0];
      slides.push({
        title: "Latest live snapshot",
        metric: `${latest.line_count || 0} lines`,
        meta: latest.timestamp || "Live update",
        body: `Latest live run shows ${latest.deeplog_anomalies || 0} baseline anomalies, ${latest.report_anomalies || 0} improved anomalies, and ${pct(latest.agreement_rate)} agreement.`,
      });
    }
    if (recentReport) {
      slides.push({
        title: "Recent report",
        metric: recentReport.filename,
        meta: recentReport.created_at || "Recent report",
        body: `Most recent stored report has ${recentReport.summary.window_count || 0} windows and ${recentReport.summary.report_anomalies || 0} improved-model anomaly flags.`,
      });
    }
    if (!slides.length) {
      slides.push({
        title: "Loading",
        metric: "Stand by",
        meta: "Waiting for data",
        body: "Slides will begin rotating after status and evaluation data are available.",
      });
    }
    return slides;
  }

  function renderSlides() {
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

  function startSlideTimer() {
    if (state.slideTimer) clearInterval(state.slideTimer);
    state.slideTimer = setInterval(() => advanceSlide(1), 4500);
  }

  function setNavFocus(targetId) {
    els.navLinks.forEach((button) => {
      button.classList.toggle("active", button.dataset.navTarget === targetId);
    });
    els.focusPanels.forEach((panel) => {
      panel.classList.toggle("focused", panel.dataset.section === targetId);
    });
  }

  function bindObserver() {
    const observer = new IntersectionObserver((entries) => {
      const visible = entries.filter((entry) => entry.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio);
      if (visible[0]) setNavFocus(visible[0].target.dataset.section);
    }, { threshold: [0.25, 0.45, 0.65] });
    els.focusPanels.forEach((panel) => observer.observe(panel));
  }

  async function refreshStatus() {
    const response = await fetch("/api/status");
    renderStatus(await response.json());
  }

  async function refreshEvaluation() {
    const response = await fetch("/api/evaluation");
    renderEvaluation(await response.json());
  }

  async function loadSampleText(sampleId) {
    const response = await fetch(`/api/demo/sample/${sampleId}/text`);
    const data = await response.json();
    els.logText.value = data.text || "";
    els.analysisStatus.textContent = `${data.sample.title} loaded into the studio.`;
  }

  async function analyzeSample(sampleId) {
    const response = await fetch(`/api/demo/sample/${sampleId}/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode: els.analysisMode.value }),
    });
    const data = await response.json();
    renderReport(data.result, data.sample.title, els.analysisMode.options[els.analysisMode.selectedIndex].textContent);
    await refreshStatus();
  }

  async function analyzeText() {
    const response = await fetch("/api/analyze/text", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: els.logText.value, mode: els.analysisMode.value }),
    });
    const data = await response.json();
    renderReport(data.result, "Pasted input", els.analysisMode.options[els.analysisMode.selectedIndex].textContent);
    await refreshStatus();
  }

  async function analyzeUpload() {
    const fileInput = document.getElementById("uploadFile");
    if (!fileInput.files.length) {
      els.analysisStatus.textContent = "Choose an upload file first.";
      return;
    }
    const formData = new FormData();
    formData.append("file", fileInput.files[0]);
    formData.append("mode", els.analysisMode.value);
    const response = await fetch("/api/analyze/upload", { method: "POST", body: formData });
    const data = await response.json();
    renderReport(data.result, data.filename, els.analysisMode.options[els.analysisMode.selectedIndex].textContent);
    await refreshStatus();
  }

  async function startManualLive() {
    const response = await fetch("/api/live/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: els.livePath.value }),
    });
    const data = await response.json();
    els.liveStatus.textContent = `${data.status || data.error} | ${data.path || els.livePath.value}`;
    await refreshStatus();
  }

  async function stopLive() {
    await fetch("/api/live/stop", { method: "POST" });
    await refreshStatus();
  }

  async function toggleAdaptive() {
    const response = await fetch("/api/adaptive/toggle", { method: "POST" });
    const data = await response.json();
    els.adaptiveState.textContent = data.enabled ? `On | ${data.threshold}` : `Off | ${data.threshold}`;
    els.adaptiveReason.textContent = data.reason || "";
  }

  async function startReplay(sampleId) {
    const response = await fetch("/api/demo/replay/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sample_id: sampleId || state.featuredSample?.id || "executive-brief" }),
    });
    const data = await response.json();
    if (data.target_path) els.livePath.value = data.target_path;
    els.replayStatus.textContent = `${data.state} | ${data.message}`;
    await refreshStatus();
  }

  async function stopReplay() {
    const response = await fetch("/api/demo/replay/stop", { method: "POST" });
    const data = await response.json();
    els.replayStatus.textContent = `${data.state} | ${data.message}`;
    await refreshStatus();
  }

  async function pollLive() {
    const response = await fetch("/api/live/status");
    const data = await response.json();
    els.liveStatus.textContent = `${data.status?.status || "idle"} | ${data.status?.path || "No live path"} | ${data.status?.updated_at || "not updated yet"}`;
    els.replayStatus.textContent = `${data.replay?.state || "idle"} | ${data.replay?.message || "Replay idle."}`;
    if (data.status?.result) renderReport(data.status.result, "Live feed", els.analysisMode.options[els.analysisMode.selectedIndex].textContent);
  }

  function openExport(path) {
    window.open(path, "_blank");
  }

  function bindEvents() {
    document.getElementById("analyzeTextBtn").addEventListener("click", analyzeText);
    document.getElementById("analyzeUploadBtn").addEventListener("click", analyzeUpload);
    document.getElementById("loadFeaturedBtn").addEventListener("click", () => {
      els.logText.value = bootstrap.sample_text || "";
      els.analysisStatus.textContent = "Featured sample loaded into the text console.";
    });
    document.getElementById("heroLoadSample").addEventListener("click", () => {
      els.logText.value = bootstrap.sample_text || "";
      els.analysisStatus.textContent = "Featured sample loaded from the overview panel.";
    });
    document.getElementById("heroReplay").addEventListener("click", () => startReplay(state.featuredSample?.id));
    document.getElementById("startReplayBtn").addEventListener("click", () => startReplay(state.featuredSample?.id));
    document.getElementById("stopReplayBtn").addEventListener("click", stopReplay);
    document.getElementById("startLiveBtn").addEventListener("click", startManualLive);
    document.getElementById("stopLiveBtn").addEventListener("click", stopLive);
    document.getElementById("toggleAdaptiveBtn").addEventListener("click", toggleAdaptive);
    document.getElementById("toggleMetricsBtn").addEventListener("click", (event) => {
      state.evaluationFocus = !state.evaluationFocus;
      event.currentTarget.classList.toggle("active", state.evaluationFocus);
      document.getElementById("evaluation").scrollIntoView({ behavior: "smooth", block: "start" });
    });
    document.getElementById("refreshEvaluation").addEventListener("click", refreshEvaluation);
    document.getElementById("slidePrev").addEventListener("click", () => advanceSlide(-1));
    document.getElementById("slideNext").addEventListener("click", () => advanceSlide(1));
    els.themeSelect.addEventListener("change", (event) => setTheme(event.target.value));

    document.getElementById("exportCsvBtn").addEventListener("click", () => openExport("/api/report/export.csv"));
    document.getElementById("exportJsonBtn").addEventListener("click", () => openExport("/api/report/export.json"));
    document.getElementById("exportHtmlBtn").addEventListener("click", () => openExport("/api/report/export.html"));

    els.rowFilter.addEventListener("change", renderTable);
    els.hostFilter.addEventListener("change", renderTable);

    els.navLinks.forEach((button) => {
      button.addEventListener("click", () => {
        const target = document.getElementById(button.dataset.navTarget);
        setNavFocus(button.dataset.navTarget);
        if (target) target.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    });

    els.slideDots.addEventListener("click", (event) => {
      const dot = event.target.closest("[data-slide-index]");
      if (!dot) return;
      state.slideIndex = Number(dot.dataset.slideIndex);
      renderSlides();
    });

    document.body.addEventListener("click", (event) => {
      const actionTarget = event.target.closest("[data-action]");
      if (!actionTarget) return;
      const action = actionTarget.dataset.action;
      if (action === "load-sample") loadSampleText(actionTarget.dataset.sample);
      else if (action === "analyze-sample") analyzeSample(actionTarget.dataset.sample);
      else if (action === "replay-sample") startReplay(actionTarget.dataset.sample);
      else if (action === "use-path") {
        els.livePath.value = actionTarget.dataset.path;
        els.analysisStatus.textContent = "Sample path moved into the live monitor input.";
      }
    });
  }

  function init() {
    setTheme(state.theme);
    els.logText.value = bootstrap.sample_text || "";
    renderScenarioGrid();
    renderPathList();
    renderSlides();
    bindEvents();
    bindObserver();
    setNavFocus("overview");
    refreshStatus();
    refreshEvaluation();
    startSlideTimer();
    setInterval(refreshStatus, 6000);
    setInterval(refreshEvaluation, 15000);
    setInterval(pollLive, 2500);
  }

  init();
})();
