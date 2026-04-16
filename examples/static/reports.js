(function () {
  const ui = window.WorkbenchUI;
  const defaults = ui.bootstrap.report_defaults || {};
  const initialCatalog = ui.bootstrap.report_catalog || { types: [], renderers: {} };
  const initialRenderers = ui.bootstrap.report_renderers || {};

  const els = {
    reportTypeCount: document.getElementById("reportTypeCount"),
    reportRunCount: document.getElementById("reportRunCount"),
    rendererReadyCount: document.getElementById("rendererReadyCount"),
    activeReportLabel: document.getElementById("activeReportLabel"),
    reportTypeSelect: document.getElementById("reportTypeSelect"),
    reportSourceSelect: document.getElementById("reportSourceSelect"),
    rendererGrid: document.getElementById("rendererGrid"),
    reportDescription: document.getElementById("reportDescription"),
    reportSourceHint: document.getElementById("reportSourceHint"),
    refreshReportCatalog: document.getElementById("refreshReportCatalog"),
    openPreviewTabBtn: document.getElementById("openPreviewTabBtn"),
    downloadPdfBtn: document.getElementById("downloadPdfBtn"),
    reportPreviewFrame: document.getElementById("reportPreviewFrame"),
    selectedRendererPill: document.getElementById("selectedRendererPill"),
  };

  const state = {
    catalog: { types: [], renderers: { ...initialRenderers, ...(initialCatalog.renderers || {}) } },
    reportType: defaults.report_type || "analysis",
    sourceId: defaults.source_id || "",
    renderer: defaults.renderer || Object.entries({ ...initialRenderers, ...(initialCatalog.renderers || {}) }).find(([, entry]) => entry.available)?.[0] || "weasyprint",
  };

  function selectedType() {
    return (state.catalog.types || []).find((entry) => entry.id === state.reportType) || state.catalog.types?.[0] || null;
  }

  function updateTopline() {
    const types = state.catalog.types || [];
    const runs = (types.find((entry) => entry.id === "analysis") || {}).sources || [];
    const renderers = state.catalog.renderers || {};
    const readyCount = Object.values(renderers).filter((entry) => entry.available).length;
    els.reportTypeCount.textContent = String(types.length || 0);
    els.reportRunCount.textContent = String(runs.length || 0);
    els.rendererReadyCount.textContent = `${readyCount}/${Object.keys(renderers).length || 0}`;
    els.activeReportLabel.textContent = selectedType()?.label || "Report";
    els.selectedRendererPill.textContent = renderers[state.renderer]?.label || state.renderer;
  }

  function renderTypeSelect() {
    const types = state.catalog.types || [];
    els.reportTypeSelect.innerHTML = types.map((entry) => `
      <option value="${entry.id}" ${entry.id === state.reportType ? "selected" : ""}>${entry.label}</option>
    `).join("");
    if (!types.some((entry) => entry.id === state.reportType) && types[0]) {
      state.reportType = types[0].id;
    }
  }

  function renderSourceSelect() {
    const type = selectedType();
    const sources = type?.sources || [];
    if (!sources.length) {
      els.reportSourceSelect.innerHTML = '<option value="">No sources ready</option>';
      els.reportSourceSelect.disabled = true;
      state.sourceId = "";
      return;
    }
    if (!sources.some((entry) => String(entry.id) === String(state.sourceId))) {
      state.sourceId = String(sources[0].id);
    }
    els.reportSourceSelect.disabled = false;
    els.reportSourceSelect.innerHTML = sources.map((entry) => `
      <option value="${entry.id}" ${String(entry.id) === String(state.sourceId) ? "selected" : ""}>${entry.label}</option>
    `).join("");
    els.reportSourceHint.textContent = sources.find((entry) => String(entry.id) === String(state.sourceId))?.detail || type?.description || "";
  }

  function renderRendererGrid() {
    const renderers = state.catalog.renderers || {};
    els.rendererGrid.innerHTML = Object.entries(renderers).map(([id, entry]) => `
      <button class="renderer-card ${state.renderer === id ? "active" : ""} ${entry.available ? "" : "disabled"}" type="button" data-renderer="${id}" ${entry.available ? "" : "disabled"}>
        <strong>${entry.label}</strong>
        <span>${entry.detail}</span>
      </button>
    `).join("");
  }

  function previewUrl() {
    const params = new URLSearchParams({ report_type: state.reportType, renderer: state.renderer, theme: document.body.dataset.theme || ui.bootstrap.preferences?.theme || "campus" });
    if (state.sourceId) params.set("source_id", state.sourceId);
    return `/reports/preview?${params.toString()}`;
  }

  function downloadUrl() {
    const params = new URLSearchParams({
      report_type: state.reportType,
      renderer: state.renderer,
      theme: document.body.dataset.theme || ui.bootstrap.preferences?.theme || "campus",
    });
    if (state.sourceId) params.set("source_id", state.sourceId);
    return `/api/reports/download.pdf?${params.toString()}`;
  }

  function refreshPreview() {
    const type = selectedType();
    const rendererLabel = (state.catalog.renderers || {})[state.renderer]?.label || state.renderer;
    els.reportDescription.textContent = type?.description || "Select a report configuration to preview the generated report.";
    els.reportSourceHint.textContent = `${rendererLabel} preview is embedded below as a real PDF and will follow the active workspace theme.`;
    els.reportPreviewFrame.src = previewUrl();
    updateTopline();
  }

  function syncUI() {
    renderTypeSelect();
    renderSourceSelect();
    renderRendererGrid();
    refreshPreview();
  }

  async function refreshCatalog() {
    const payload = await ui.fetchJSON("/api/reports/catalog");
    state.catalog = {
      types: payload.types || [],
      renderers: payload.renderers || state.catalog.renderers || {},
    };
    syncUI();
  }

  els.reportTypeSelect.addEventListener("change", (event) => {
    state.reportType = event.target.value;
    state.sourceId = "";
    syncUI();
  });

  els.reportSourceSelect.addEventListener("change", (event) => {
    state.sourceId = event.target.value;
    refreshPreview();
  });

  els.rendererGrid.addEventListener("click", (event) => {
    const card = event.target.closest("[data-renderer]");
    if (!card || card.disabled) return;
    state.renderer = card.dataset.renderer;
    renderRendererGrid();
    refreshPreview();
  });

  els.refreshReportCatalog.addEventListener("click", async () => {
    try {
      await refreshCatalog();
    } catch (error) {
      els.reportDescription.textContent = error.message || "Unable to refresh the reports catalog right now.";
    }
  });

  els.openPreviewTabBtn.addEventListener("click", () => {
    window.open(previewUrl(), "_blank");
  });

  els.downloadPdfBtn.addEventListener("click", () => {
    ui.openExport(downloadUrl());
  });

  window.addEventListener("adw:theme-change", () => {
    refreshPreview();
  });

  state.catalog = {
    types: initialCatalog.types || [],
    renderers: { ...initialRenderers, ...(initialCatalog.renderers || {}) },
  };
  syncUI();
})();
