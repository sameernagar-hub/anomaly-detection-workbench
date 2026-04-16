(function () {
  const bootstrapElement = document.getElementById("bootstrap-data");
  const bootstrap = bootstrapElement ? JSON.parse(bootstrapElement.textContent) : {};

  function pct(value) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
    return `${Math.round(Number(value) * 100)}%`;
  }

  function score(value) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
    return Number(value).toFixed(3);
  }

  function humanModeLabel(mode) {
    if (mode === "deeplog") return "Baseline Sentinel only";
    if (mode === "report") return "Apex Insight only";
    return "Dual Command View";
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

  function themeColor(name) {
    return getComputedStyle(document.body).getPropertyValue(name).trim();
  }

  async function persistTheme(theme) {
    if (!bootstrap.current_user) return;
    try {
      await fetchJSON("/api/profile/theme", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ theme }),
      });
      if (bootstrap.preferences) bootstrap.preferences.theme = theme;
    } catch (error) {
      console.error("Unable to persist theme preference.", error);
    }
  }

  function setTheme(theme) {
    const previousTheme = document.body.dataset.theme;
    document.body.dataset.theme = theme;
    const select = document.getElementById("themeSelect");
    if (select) select.value = theme;
    localStorage.setItem("adw-theme", theme);
    window.dispatchEvent(new CustomEvent("adw:theme-change", { detail: { theme, previousTheme } }));
  }

  function initTheme() {
    const theme = bootstrap.preferences?.theme || localStorage.getItem("adw-theme") || document.body.dataset.theme || "campus";
    setTheme(theme);
    const select = document.getElementById("themeSelect");
    if (select) {
      select.addEventListener("change", async (event) => {
        const value = event.target.value;
        setTheme(value);
        await persistTheme(value);
      });
    }
  }

  function initPageMotion() {
    document.body.classList.add("is-entering");
    window.setTimeout(() => document.body.classList.remove("is-entering"), 450);

    document.querySelectorAll("[data-nav-link]").forEach((link) => {
      link.addEventListener("click", (event) => {
        if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
        const href = link.getAttribute("href");
        if (!href || href === window.location.pathname) return;
        event.preventDefault();
        document.body.classList.add("is-leaving");
        window.setTimeout(() => {
          window.location.href = href;
        }, 170);
      });
    });
  }

  function initTooltips() {
    const tooltip = document.createElement("div");
    tooltip.className = "global-tooltip";
    tooltip.setAttribute("role", "tooltip");
    tooltip.hidden = true;
    document.body.appendChild(tooltip);

    let activeTrigger = null;

    function positionTooltip(trigger) {
      const rect = trigger.getBoundingClientRect();
      tooltip.style.left = "0px";
      tooltip.style.top = "0px";
      tooltip.hidden = false;

      const tipRect = tooltip.getBoundingClientRect();
      const viewportWidth = window.innerWidth;
      const viewportHeight = window.innerHeight;
      let left = rect.left + (rect.width / 2) - (tipRect.width / 2);
      left = Math.max(12, Math.min(left, viewportWidth - tipRect.width - 12));

      let top = rect.top - tipRect.height - 12;
      let placement = "top";
      if (top < 12) {
        top = rect.bottom + 12;
        placement = "bottom";
      }
      if (top + tipRect.height > viewportHeight - 12) {
        top = Math.max(12, viewportHeight - tipRect.height - 12);
      }

      tooltip.style.left = `${left + window.scrollX}px`;
      tooltip.style.top = `${top + window.scrollY}px`;
      tooltip.dataset.placement = placement;
    }

    function showTooltip(trigger) {
      const text = trigger.dataset.tooltip;
      if (!text) return;
      activeTrigger = trigger;
      tooltip.textContent = text;
      tooltip.hidden = false;
      positionTooltip(trigger);
      trigger.setAttribute("aria-expanded", "true");
    }

    function hideTooltip() {
      if (activeTrigger) {
        activeTrigger.setAttribute("aria-expanded", "false");
      }
      activeTrigger = null;
      tooltip.hidden = true;
    }

    document.querySelectorAll("[data-tooltip]").forEach((trigger) => {
      trigger.setAttribute("tabindex", trigger.getAttribute("tabindex") || "0");
      trigger.setAttribute("aria-haspopup", "true");
      trigger.setAttribute("aria-expanded", "false");
      trigger.addEventListener("mouseenter", () => showTooltip(trigger));
      trigger.addEventListener("focus", () => showTooltip(trigger));
      trigger.addEventListener("mouseleave", hideTooltip);
      trigger.addEventListener("blur", hideTooltip);
      trigger.addEventListener("click", (event) => {
        if (trigger.classList.contains("info-dot")) {
          event.preventDefault();
          if (activeTrigger === trigger && !tooltip.hidden) hideTooltip();
          else showTooltip(trigger);
        }
      });
    });

    document.addEventListener("click", (event) => {
      if (event.target.closest("[data-tooltip]")) return;
      hideTooltip();
    });
    window.addEventListener("scroll", () => {
      if (activeTrigger && !tooltip.hidden) positionTooltip(activeTrigger);
    }, { passive: true });
    window.addEventListener("resize", () => {
      if (activeTrigger && !tooltip.hidden) positionTooltip(activeTrigger);
    });
  }

  function initAccountMenu() {
    const menu = document.querySelector("[data-account-menu]");
    if (!menu) return;

    const trigger = menu.querySelector("[data-account-trigger]");
    const panel = menu.querySelector("[data-account-panel]");
    if (!trigger || !panel) return;

    function openMenu() {
      panel.hidden = false;
      menu.classList.add("open");
      trigger.setAttribute("aria-expanded", "true");
    }

    function closeMenu() {
      panel.hidden = true;
      menu.classList.remove("open");
      trigger.setAttribute("aria-expanded", "false");
    }

    trigger.addEventListener("click", () => {
      if (panel.hidden) openMenu();
      else closeMenu();
    });

    document.addEventListener("click", (event) => {
      if (menu.contains(event.target)) return;
      closeMenu();
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        closeMenu();
        trigger.focus();
      }
    });

    menu.querySelectorAll("a, button, input").forEach((element) => {
      element.addEventListener("focusout", () => {
        window.setTimeout(() => {
          if (!menu.contains(document.activeElement)) closeMenu();
        }, 0);
      });
    });
  }

  async function fetchJSON(url, options) {
    const response = await fetch(url, options);
    let payload = {};
    try {
      payload = await response.json();
    } catch (error) {
      payload = {};
    }
    if (response.status === 401) {
      window.location.href = "/auth/login";
      throw new Error("Authentication required.");
    }
    if (response.status === 503 && payload?.redirect) {
      window.location.href = payload.redirect;
      throw new Error(payload.error || "The workbench is still preparing your environment.");
    }
    if (!response.ok) {
      throw new Error(payload.error || payload.message || `Request failed for ${url}`);
    }
    return payload;
  }

  function openExport(path) {
    window.open(path, "_blank");
  }

  function renderTrendChart(svg, result) {
    if (!svg) return;
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
      svg.innerHTML = '<text x="28" y="144" fill="rgba(100,100,100,0.7)">Need more windows for a trend graph.</text>';
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

    svg.innerHTML = `
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

  function applyRunSummaryToMetrics(summary, els) {
    if (!els) return;
    if (els.metricWindows) els.metricWindows.textContent = summary.window_count || 0;
    if (els.metricBaselineAnomalies) els.metricBaselineAnomalies.textContent = summary.deeplog_anomalies || 0;
    if (els.metricImprovedAnomalies) els.metricImprovedAnomalies.textContent = summary.report_anomalies || 0;
    if (els.metricAgreement) els.metricAgreement.textContent = pct(summary.agreement_rate);
    if (els.metricImprovedAccuracy) {
      els.metricImprovedAccuracy.textContent =
        summary.report_vs_label_accuracy !== null && summary.report_vs_label_accuracy !== undefined ? score(summary.report_vs_label_accuracy) : "-";
    }
  }

  function applyRunDetail(result, meta, els) {
    if (!els) return;
    const summary = result?.summary || {};
    const items = result?.items || [];
    const lastItem = items[items.length - 1];
    const displayName = meta.display_name || meta.filename || "Current report";

    applyRunSummaryToMetrics(summary, els);
    if (els.currentReportName) els.currentReportName.textContent = displayName;
    if (els.currentReportMode) els.currentReportMode.textContent = humanModeLabel(meta.mode || summary.active_model || "compare");
    if (els.latestBaselineScore) els.latestBaselineScore.textContent = lastItem ? score(lastItem.deeplog_score) : "-";
    if (els.latestBaselineVerdict) els.latestBaselineVerdict.innerHTML = lastItem ? badgeForLabel(lastItem.deeplog_prediction) : "Awaiting prediction";
    if (els.latestImprovedScore) els.latestImprovedScore.textContent = lastItem ? score(lastItem.report_score) : "-";
    if (els.latestImprovedVerdict) els.latestImprovedVerdict.innerHTML = lastItem ? badgeForLabel(lastItem.report_prediction) : "Awaiting prediction";
    if (els.driftStatus) els.driftStatus.textContent = summary.drift?.status || "n/a";
    if (els.driftMessage) els.driftMessage.textContent = summary.drift?.message || "Need analysis to evaluate drift.";
  }

  function populateHostFilter(select, items) {
    if (!select) return;
    const current = select.value || "all";
    const hosts = ["all"].concat([...new Set((items || []).map((item) => item.host_group).filter(Boolean))].sort());
    select.innerHTML = hosts.map((host) => `<option value="${host}">${host === "all" ? "All hosts" : host}</option>`).join("");
    if (hosts.includes(current)) select.value = current;
  }

  function filterItems(items, rowFilter, hostFilter) {
    return (items || []).filter((item) => {
      if (hostFilter !== "all" && item.host_group !== hostFilter) return false;
      if (rowFilter === "anomaly") return Number(item.deeplog_prediction) === 1 || Number(item.report_prediction) === 1;
      if (rowFilter === "disagreement") return item.agreement === false;
      if (rowFilter === "truth-attack") return Number(item.label) === 1;
      return true;
    });
  }

  function renderResultsTable(items, els) {
    if (!els?.resultsBody) return;
    const rowFilter = els.rowFilter ? els.rowFilter.value : "all";
    const hostFilter = els.hostFilter ? els.hostFilter.value : "all";
    const visible = filterItems(items, rowFilter, hostFilter);
    if (els.rowCountLabel) els.rowCountLabel.textContent = `${visible.length} windows`;
    if (!visible.length) {
      els.resultsBody.innerHTML = '<tr><td colspan="7" class="muted">No windows match the active filter.</td></tr>';
      return;
    }
    els.resultsBody.innerHTML = visible.slice(0, 120).map((item) => `
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

  function renderRunCards(container, runs, emptyMessage) {
    if (!container) return;
    if (!runs || !runs.length) {
      container.innerHTML = `<div class="report-card muted">${emptyMessage}</div>`;
      return;
    }
    container.innerHTML = runs.map((run) => `
      <article class="report-card">
        <div class="report-card-head">
          <strong>${run.display_name || run.filename}</strong>
          <span class="pill-label">${humanModeLabel(run.mode)}</span>
        </div>
        <div class="muted">${run.created_at || "pending"} | ${run.source}</div>
        <div class="muted">windows ${run.summary?.window_count || 0} | baseline ${run.summary?.deeplog_anomalies || 0} | improved ${run.summary?.report_anomalies || 0}</div>
        <div class="control-row wrap report-actions">
          ${run.detail_url && run.detail_url !== "#" ? `<a class="ghost compact" href="${run.detail_url}">View run</a>` : ""}
          ${run.id && run.detail_url && run.detail_url !== "#" ? `<a class="ghost compact" href="/api/report/export.json?run_id=${run.id}">JSON</a>` : ""}
        </div>
      </article>
    `).join("");
  }

  function renderFeedbackCards(container, feedback, emptyMessage) {
    if (!container) return;
    if (!feedback || !feedback.length) {
      container.innerHTML = `<div class="report-card muted">${emptyMessage}</div>`;
      return;
    }
    container.innerHTML = feedback.map((entry) => `
      <article class="report-card">
        <div class="report-card-head">
          <strong>${entry.title}</strong>
          <span class="pill-label">${entry.category_label}</span>
        </div>
        <div class="muted">${entry.created_at || "pending"} | ${entry.id}</div>
        <div class="feedback-rating-row">
          <span>Overall ${entry.overall_rating}/5</span>
          <span>Usability ${entry.usability_rating}/5</span>
          <span>Visual ${entry.visual_rating}/5</span>
          <span>Clarity ${entry.clarity_rating}/5</span>
        </div>
        <p class="feedback-card-copy">${entry.message}</p>
        ${entry.question ? `<div class="report-card subtle"><strong>Question</strong><p>${entry.question}</p></div>` : ""}
      </article>
    `).join("");
  }

  function renderScenarioGrid(container, samples, handlers) {
    if (!container) return;
    container.innerHTML = (samples || []).map((sample) => `
      <article class="scenario-card">
        <div>
          <div class="eyebrow">${sample.eyebrow}</div>
          <h3>${sample.title}</h3>
          <div class="mood">${sample.mood}</div>
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

    container.addEventListener("click", (event) => {
      const target = event.target.closest("[data-action]");
      if (!target) return;
      const sampleId = target.dataset.sample;
      if (target.dataset.action === "load-sample" && handlers?.loadSample) handlers.loadSample(sampleId);
      if (target.dataset.action === "analyze-sample" && handlers?.analyzeSample) handlers.analyzeSample(sampleId);
      if (target.dataset.action === "replay-sample" && handlers?.replaySample) handlers.replaySample(sampleId);
    });
  }

  function renderPathList(container, samples, handlers) {
    if (!container) return;
    container.innerHTML = (samples || []).map((sample) => `
      <div class="path-card">
        <strong>${sample.title}</strong>
        <div class="mono muted">${sample.path}</div>
        <div class="control-row wrap">
          <button class="ghost" data-action="use-path" data-path="${sample.path}">Use path</button>
          <button class="ghost" data-action="replay-sample" data-sample="${sample.id}">Replay</button>
        </div>
      </div>
    `).join("");

    container.addEventListener("click", (event) => {
      const target = event.target.closest("[data-action]");
      if (!target) return;
      if (target.dataset.action === "use-path" && handlers?.usePath) handlers.usePath(target.dataset.path);
      if (target.dataset.action === "replay-sample" && handlers?.replaySample) handlers.replaySample(target.dataset.sample);
    });
  }

  window.WorkbenchUI = {
    bootstrap,
    pct,
    score,
    humanModeLabel,
    fetchJSON,
    openExport,
    initTheme,
    initPageMotion,
    initTooltips,
    initAccountMenu,
    renderTrendChart,
    applyRunSummaryToMetrics,
    applyRunDetail,
    populateHostFilter,
    renderResultsTable,
    renderRunCards,
    renderFeedbackCards,
    renderScenarioGrid,
    renderPathList,
  };

  initTheme();
  initPageMotion();
  initTooltips();
  initAccountMenu();
})();
