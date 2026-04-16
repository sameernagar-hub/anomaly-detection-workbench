(function () {
  const ui = window.WorkbenchUI;
  const runId = ui.bootstrap.run_id;
  const els = {
    runTitle: document.getElementById("runTitle"),
    runMeta: document.getElementById("runMeta"),
    runContext: document.getElementById("runContext"),
    runContextSummary: document.getElementById("runContextSummary"),
    runContextHighlights: document.getElementById("runContextHighlights"),
    recommendationHeadline: document.getElementById("recommendationHeadline"),
    recommendationOverview: document.getElementById("recommendationOverview"),
    recommendationSignals: document.getElementById("recommendationSignals"),
    recommendationBars: document.getElementById("recommendationBars"),
    recommendationDial: document.getElementById("recommendationDial"),
    recommendationDialValue: document.getElementById("recommendationDialValue"),
    recommendationDialLabel: document.getElementById("recommendationDialLabel"),
    recommendationPriorities: document.getElementById("recommendationPriorities"),
    recommendationTabs: document.getElementById("recommendationTabs"),
    recommendationPanels: document.getElementById("recommendationPanels"),
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
  let activeRecommendationTab = "meaning";
  let exportHandlersBound = false;

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function pctNumber(value) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) return 0;
    return Math.round(Number(value) * 100);
  }

  function severityLabel(level) {
    if (level >= 70) return "High signal";
    if (level >= 40) return "Active review";
    return "Steady review";
  }

  function buildRecommendationMetrics(recommendations) {
    const priorities = recommendations?.priorities || [];
    const top = priorities[0] || {};
    const topSignals = top.signals || [];
    const signalMap = Object.fromEntries(
      topSignals.map((entry) => {
        const parts = String(entry).split(":");
        const key = parts.shift() || "Signal";
        return [key.trim(), parts.join(":").trim()];
      }),
    );
    const anomalyShareText = signalMap["Anomaly share"] || signalMap["Disagreement share"] || "0%";
    const disagreementText = signalMap["Disagreement share"] || "0%";
    const highCount = priorities.filter((entry) => String(entry.priority).toLowerCase() === "high").length;
    const mediumCount = priorities.filter((entry) => String(entry.priority).toLowerCase() === "medium").length;
    const intensity = Math.min(
      100,
      Math.max(
        priorities.length * 18 + highCount * 16 + mediumCount * 8,
        parseInt(anomalyShareText, 10) || 0,
        parseInt(disagreementText, 10) || 0,
      ),
    );

    return {
      intensity,
      label: severityLabel(intensity),
      bars: [
        { label: "Priority load", value: Math.min(100, priorities.length * 22), tone: "accent" },
        { label: "High-priority items", value: Math.min(100, highCount * 33), tone: "warn" },
        { label: "Medium-priority items", value: Math.min(100, mediumCount * 24), tone: "steady" },
      ],
      signalChips: topSignals.slice(0, 4),
    };
  }

  function renderRecommendationDial(metrics) {
    if (!els.recommendationDial) return;
    const value = Math.max(0, Math.min(100, Number(metrics?.intensity || 0)));
    const radius = 84;
    const circumference = 2 * Math.PI * radius;
    const dash = (value / 100) * circumference;
    const theme = getComputedStyle(document.body);
    const accent = theme.getPropertyValue("--accent-alt").trim();
    const warn = theme.getPropertyValue("--warn").trim();
    const line = theme.getPropertyValue("--line").trim();
    const ink = theme.getPropertyValue("--text").trim();
    const tone = value >= 70 ? warn : accent;

    els.recommendationDial.innerHTML = `
      <circle cx="110" cy="110" r="${radius}" fill="none" stroke="${line}" stroke-width="18"></circle>
      <circle
        cx="110"
        cy="110"
        r="${radius}"
        fill="none"
        stroke="${tone}"
        stroke-width="18"
        stroke-linecap="round"
        stroke-dasharray="${dash} ${circumference - dash}"
        transform="rotate(-90 110 110)"
      ></circle>
      <circle cx="110" cy="110" r="58" fill="none" stroke="${line}" stroke-width="1.5" stroke-dasharray="3 7"></circle>
      <path d="M58 142 C92 106, 128 106, 162 76" fill="none" stroke="${ink}" stroke-opacity="0.22" stroke-width="4" stroke-linecap="round"></path>
      <circle cx="58" cy="142" r="5" fill="${ink}" fill-opacity="0.24"></circle>
      <circle cx="162" cy="76" r="6" fill="${tone}"></circle>
    `;
    els.recommendationDialValue.textContent = `${value}%`;
    els.recommendationDialLabel.textContent = metrics?.label || "Awaiting run";
  }

  function renderRecommendationVisuals(recommendations) {
    const metrics = buildRecommendationMetrics(recommendations);
    renderRecommendationDial(metrics);
    els.recommendationSignals.innerHTML = (metrics.signalChips.length ? metrics.signalChips : ["Guided analytics will appear here"]).map((entry) => `
      <span class="context-chip">${escapeHtml(entry)}</span>
    `).join("");
    els.recommendationBars.innerHTML = metrics.bars.map((entry) => `
      <article class="advisory-bar-card ${entry.tone}">
        <div class="advisory-bar-head">
          <strong>${escapeHtml(entry.label)}</strong>
          <span>${entry.value}%</span>
        </div>
        <div class="advisory-bar-track"><span style="width:${entry.value}%"></span></div>
      </article>
    `).join("");
  }

  function renderRecommendations(recommendations) {
    const tabs = recommendations?.tabs || [];
    const priorities = recommendations?.priorities || [];
    renderRecommendationVisuals(recommendations);
    if (!tabs.length) {
      els.recommendationHeadline.textContent = "Investigation guidance";
      els.recommendationOverview.textContent = "Recommendation guidance is not available for this run yet.";
      els.recommendationPriorities.innerHTML = '<article class="advisory-card muted">No prioritized guidance was generated for this archived run.</article>';
      els.recommendationTabs.innerHTML = "";
      els.recommendationPanels.innerHTML = "";
      return;
    }

    if (!tabs.some((tab) => tab.id === activeRecommendationTab)) {
      activeRecommendationTab = tabs[0].id;
    }

    els.recommendationHeadline.textContent = recommendations.headline || "Investigation guidance";
    els.recommendationOverview.textContent = recommendations.overview || "Guided interpretation for this run is available below.";
    els.recommendationPriorities.innerHTML = priorities.map((entry) => `
      <article class="advisory-card priority-${String(entry.priority || "Medium").toLowerCase()}">
        <div class="advisory-card-top">
          <div class="advisory-card-heading">
            <span class="pill-label">${entry.priority || "Medium"} priority</span>
            <strong>${entry.title}</strong>
          </div>
          <div class="advisory-card-glyph" aria-hidden="true">${String(entry.priority || "").toLowerCase() === "high" ? "!" : String(entry.priority || "").toLowerCase() === "medium" ? "~" : "i"}</div>
        </div>
        <p>${entry.summary || ""}</p>
        <div class="advisory-signals">${(entry.signals || []).map((signal) => `<span>${signal}</span>`).join("")}</div>
        <div class="advisory-copy-block">
          <strong>Why this matters</strong>
          <p>${entry.meaning || ""}</p>
        </div>
        <div class="advisory-copy-block">
          <strong>What to do</strong>
          <ul class="advisory-list">
            ${(entry.actions || []).map((action) => `<li>${action}</li>`).join("")}
          </ul>
        </div>
      </article>
    `).join("");

    els.recommendationTabs.innerHTML = tabs.map((tab) => `
      <button class="toggle ${tab.id === activeRecommendationTab ? "active" : ""}" type="button" data-recommendation-tab="${tab.id}">
        ${tab.label}
      </button>
    `).join("");

    els.recommendationPanels.innerHTML = tabs.map((tab) => `
      <section class="advisory-panel ${tab.id === activeRecommendationTab ? "active" : ""}" data-recommendation-panel="${tab.id}">
        <div class="advisory-panel-intro">${tab.intro || ""}</div>
        <ul class="advisory-list">
          ${(tab.items || []).map((item) => `<li>${item}</li>`).join("")}
        </ul>
      </section>
    `).join("");
  }

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
    const summary = run.summary || {};
    const highlights = [
      ["Source", run.source || "run"],
      ["Mode", ui.humanModeLabel(run.mode)],
      ["Created", run.created_at || "-"],
      ["Windows", summary.window_count || 0],
      ["Drift", summary.drift?.status || "n/a"],
      ["Agreement", ui.pct(summary.agreement_rate)],
    ];
    els.runContextSummary.innerHTML = `
      <strong>${escapeHtml(run.display_name || run.filename || "Run context")}</strong>
      <p class="muted">Saved ${escapeHtml(run.created_at || "recently")} from a ${escapeHtml(run.source || "run")} workflow in ${escapeHtml(ui.humanModeLabel(run.mode))}. Use this area for provenance and environment clues after reviewing the guided response.</p>
    `;
    els.runContextHighlights.innerHTML = highlights.map(([label, value]) => `
      <article class="context-chip-card">
        <span>${escapeHtml(label)}</span>
        <strong>${escapeHtml(value)}</strong>
      </article>
    `).join("");
    els.runContext.innerHTML = Object.keys(metadata).length
      ? Object.entries(metadata).map(([key, value]) => `
        <div class="report-card context-report-card">
          <span class="context-label">${escapeHtml(key.replace(/_/g, " "))}</span>
          <strong>${escapeHtml(value)}</strong>
        </div>
      `).join("")
      : '<div class="report-card muted">No additional metadata was recorded for this run.</div>';
    renderRecommendations(run.recommendations || {});

    if (!exportHandlersBound) {
      els.exportCsvBtn.addEventListener("click", () => ui.openExport(`/api/report/export.csv?run_id=${run.id}`));
      els.exportJsonBtn.addEventListener("click", () => ui.openExport(`/api/report/export.json?run_id=${run.id}`));
      els.exportHtmlBtn.addEventListener("click", () => ui.openExport(`/api/report/export.html?run_id=${run.id}`));
      exportHandlersBound = true;
    }
  }

  async function refresh() {
    const data = await ui.fetchJSON(`/api/runs/${runId}`);
    renderRun(data.run);
  }

  els.rowFilter.addEventListener("change", () => ui.renderResultsTable(items, els));
  els.hostFilter.addEventListener("change", () => ui.renderResultsTable(items, els));
  els.recommendationTabs.addEventListener("click", (event) => {
    const button = event.target.closest("[data-recommendation-tab]");
    if (!button) return;
    activeRecommendationTab = button.dataset.recommendationTab;
    document.querySelectorAll("[data-recommendation-tab]").forEach((element) => {
      element.classList.toggle("active", element.dataset.recommendationTab === activeRecommendationTab);
    });
    document.querySelectorAll("[data-recommendation-panel]").forEach((element) => {
      element.classList.toggle("active", element.dataset.recommendationPanel === activeRecommendationTab);
    });
  });
  refresh();
})();
