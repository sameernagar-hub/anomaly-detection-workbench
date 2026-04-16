(function () {
  const ui = window.WorkbenchUI;
  const runId = ui.bootstrap.run_id;
  const els = {
    runTitle: document.getElementById("runTitle"),
    runMeta: document.getElementById("runMeta"),
    runContext: document.getElementById("runContext"),
    recommendationHeadline: document.getElementById("recommendationHeadline"),
    recommendationOverview: document.getElementById("recommendationOverview"),
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

  function renderRecommendations(recommendations) {
    const tabs = recommendations?.tabs || [];
    const priorities = recommendations?.priorities || [];
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
          <span class="pill-label">${entry.priority || "Medium"} priority</span>
          <strong>${entry.title}</strong>
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
    els.runContext.innerHTML = Object.keys(metadata).length
      ? Object.entries(metadata).map(([key, value]) => `<div class="report-card"><strong>${key}</strong><div class="muted">${value}</div></div>`).join("")
      : '<div class="report-card muted">No additional metadata was recorded for this run.</div>';
    renderRecommendations(run.recommendations || {});

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
