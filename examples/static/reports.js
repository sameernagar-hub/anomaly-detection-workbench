(function () {
  const ui = window.WorkbenchUI;
  const defaults = ui.bootstrap.report_defaults || {};
  const initialCatalog = ui.bootstrap.report_catalog || { types: [], renderers: {} };
  const initialRenderers = ui.bootstrap.report_renderers || {};
  const rendererOrder = ["weasyprint", "reportlab"];

  const els = {
    reportTypeCount: document.getElementById("reportTypeCount"),
    reportRunCount: document.getElementById("reportRunCount"),
    rendererReadyCount: document.getElementById("rendererReadyCount"),
    activeReportLabel: document.getElementById("activeReportLabel"),
    reportTypeSelect: document.getElementById("reportTypeSelect"),
    reportSourceSelect: document.getElementById("reportSourceSelect"),
    reportDescription: document.getElementById("reportDescription"),
    reportSourceHint: document.getElementById("reportSourceHint"),
    refreshReportCatalog: document.getElementById("refreshReportCatalog"),
    reportPreviewGrid: document.getElementById("reportPreviewGrid"),
  };

  const state = {
    catalog: { types: [], renderers: { ...initialRenderers, ...(initialCatalog.renderers || {}) } },
    reportType: defaults.report_type || "analysis",
    sourceId: defaults.source_id || "",
    previewNonce: Date.now(),
  };

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, (char) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      "\"": "&quot;",
      "'": "&#39;",
    }[char]));
  }

  function selectedType() {
    return (state.catalog.types || []).find((entry) => entry.id === state.reportType) || state.catalog.types?.[0] || null;
  }

  function selectedSource() {
    const type = selectedType();
    return (type?.sources || []).find((entry) => String(entry.id) === String(state.sourceId)) || null;
  }

  function rendererEntries() {
    const renderers = state.catalog.renderers || {};
    return rendererOrder.map((id) => [id, renderers[id] || { label: id, available: false, detail: "Renderer status is not available." }]);
  }

  function currentTheme() {
    return document.body.dataset.theme || ui.bootstrap.preferences?.theme || "campus";
  }

  function currentSourceLabel() {
    return selectedSource()?.label || els.reportSourceSelect.options[els.reportSourceSelect.selectedIndex]?.text || "selected source";
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
  }

  function renderTypeSelect() {
    const types = state.catalog.types || [];
    els.reportTypeSelect.innerHTML = types.map((entry) => `
      <option value="${escapeHtml(entry.id)}" ${entry.id === state.reportType ? "selected" : ""}>${escapeHtml(entry.label)}</option>
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
      els.reportSourceHint.textContent = type?.description || "No source is ready for this report yet.";
      return;
    }
    if (!sources.some((entry) => String(entry.id) === String(state.sourceId))) {
      state.sourceId = String(sources[0].id);
    }
    els.reportSourceSelect.disabled = false;
    els.reportSourceSelect.innerHTML = sources.map((entry) => `
      <option value="${escapeHtml(entry.id)}" ${String(entry.id) === String(state.sourceId) ? "selected" : ""}>${escapeHtml(entry.label)}</option>
    `).join("");
    els.reportSourceHint.textContent = selectedSource()?.detail || type?.description || "";
  }

  function previewUrl(renderer) {
    const params = new URLSearchParams({
      report_type: state.reportType,
      renderer,
      theme: currentTheme(),
      preview_nonce: String(state.previewNonce),
    });
    if (state.sourceId) params.set("source_id", state.sourceId);
    return `/reports/preview?${params.toString()}`;
  }

  function embeddedPreviewUrl(renderer) {
    return `${previewUrl(renderer)}#page=1&zoom=page-width&toolbar=0&navpanes=0`;
  }

  function downloadUrl(renderer) {
    const params = new URLSearchParams({
      report_type: state.reportType,
      renderer,
      theme: currentTheme(),
    });
    if (state.sourceId) params.set("source_id", state.sourceId);
    return `/api/reports/download.pdf?${params.toString()}`;
  }

  function updateRendererCards() {
    rendererEntries().forEach(([id, entry]) => {
      const available = Boolean(entry.available);
      const card = els.reportPreviewGrid.querySelector(`[data-renderer-card="${id}"]`);
      if (!card) return;
      const stateLabel = card.querySelector(`[data-renderer-state="${id}"]`);
      const pill = card.querySelector(`[data-renderer-pill="${id}"]`);
      const detail = card.querySelector(`[data-renderer-detail="${id}"]`);
      const frame = card.querySelector(`[data-renderer-frame="${id}"]`);
      const unavailable = card.querySelector(`[data-renderer-unavailable="${id}"]`);
      const actions = card.querySelectorAll("[data-report-action]");

      card.classList.toggle("unavailable", !available);
      if (stateLabel) stateLabel.textContent = available ? "Preview online" : "Preview unavailable";
      if (pill) pill.textContent = available ? "Ready" : "Offline";
      if (detail) detail.textContent = entry.detail || "";
      actions.forEach((button) => {
        button.disabled = !available;
      });

      if (frame) {
        frame.hidden = !available;
        if (!available) frame.removeAttribute("src");
      }
      if (unavailable) {
        unavailable.hidden = available;
        unavailable.textContent = entry.detail || "This renderer is not available.";
      }
    });
  }

  function refreshPreviews() {
    const type = selectedType();
    const sourceLabel = currentSourceLabel();
    state.previewNonce = Date.now();
    els.reportDescription.textContent = type?.description || "Select a report configuration to preview the generated report.";
    els.reportSourceHint.textContent = selectedSource()?.detail || `Both previews are rendering ${sourceLabel} with the active workspace theme.`;

    updateRendererCards();
    rendererEntries().forEach(([id, entry]) => {
      const card = els.reportPreviewGrid.querySelector(`[data-renderer-card="${id}"]`);
      const frame = card?.querySelector("[data-renderer-frame]");
      if (!entry.available || !frame) return;
      frame.src = embeddedPreviewUrl(id);
    });
    updateTopline();
  }

  function syncUI() {
    renderTypeSelect();
    renderSourceSelect();
    refreshPreviews();
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
    syncUI();
  });

  els.refreshReportCatalog.addEventListener("click", async () => {
    try {
      await refreshCatalog();
    } catch (error) {
      els.reportDescription.textContent = error.message || "Unable to refresh the reports catalog right now.";
    }
  });

  els.reportPreviewGrid.addEventListener("click", (event) => {
    const button = event.target.closest("[data-report-action]");
    if (!button || button.disabled) return;
    const renderer = button.dataset.renderer;
    if (button.dataset.reportAction === "open") {
      window.open(previewUrl(renderer), "_blank");
      return;
    }
    if (button.dataset.reportAction === "download") {
      ui.openExport(downloadUrl(renderer));
    }
  });

  window.addEventListener("adw:theme-change", () => {
    refreshPreviews();
  });

  state.catalog = {
    types: initialCatalog.types || [],
    renderers: { ...initialRenderers, ...(initialCatalog.renderers || {}) },
  };
  syncUI();
})();
