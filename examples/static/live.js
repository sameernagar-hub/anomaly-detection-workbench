(function () {
  const ui = window.WorkbenchUI;
  const bootstrap = ui.bootstrap;
  const params = new URLSearchParams(window.location.search);
  const requestedSample = params.get("sample");
  const els = {
    livePath: document.getElementById("livePath"),
    liveSystem: document.getElementById("liveSystem"),
    startLiveBtn: document.getElementById("startLiveBtn"),
    stopLiveBtn: document.getElementById("stopLiveBtn"),
    startReplayBtn: document.getElementById("startReplayBtn"),
    stopReplayBtn: document.getElementById("stopReplayBtn"),
    saveLiveBtn: document.getElementById("saveLiveBtn"),
    liveStatus: document.getElementById("liveStatus"),
    replayStatus: document.getElementById("replayStatus"),
    liveSaveStatus: document.getElementById("liveSaveStatus"),
    trendChart: document.getElementById("trendChart"),
    pathList: document.getElementById("pathList"),
    liveHistory: document.getElementById("liveHistory"),
  };

  async function refresh() {
    try {
      const data = await ui.fetchJSON("/api/live/status");
      els.liveStatus.textContent = `${data.status?.status || "idle"} | ${data.context?.system || "System not set"} | ${data.status?.path || "No live path"} | ${data.status?.updated_at || "not updated yet"}`;
      els.replayStatus.textContent = `${data.replay?.state || "idle"} | ${data.replay?.message || "Replay idle."}`;
      if (data.context?.system) els.liveSystem.value = data.context.system;
      ui.renderTrendChart(els.trendChart, data.status?.result);
      const history = (data.status?.history || []).map((item, index) => ({
        id: `live-${index}`,
        filename: `${item.line_count || 0} lines`,
        created_at: item.timestamp,
        mode: "compare",
        source: "live",
        summary: {
          window_count: item.line_count,
          deeplog_anomalies: item.deeplog_anomalies,
          report_anomalies: item.report_anomalies,
        },
        detail_url: "#",
      }));
      ui.renderRunCards(els.liveHistory, history, "No live updates yet.");
    } catch (error) {
      els.liveStatus.textContent = error.message || "Unable to refresh live status.";
    }
  }

  async function startLive() {
    try {
      const data = await ui.fetchJSON("/api/live/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: els.livePath.value, system: els.liveSystem.value }),
      });
      els.liveStatus.textContent = `${data.status || data.error} | ${data.path || els.livePath.value}`;
      refresh();
    } catch (error) {
      els.liveStatus.textContent = error.message || "Unable to start live monitoring.";
    }
  }

  async function stopLive() {
    try {
      await ui.fetchJSON("/api/live/stop", { method: "POST" });
      refresh();
    } catch (error) {
      els.liveStatus.textContent = error.message || "Unable to stop live monitoring.";
    }
  }

  async function startReplay(sampleId) {
    try {
      const data = await ui.fetchJSON("/api/demo/replay/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sample_id: sampleId || bootstrap.featured_sample?.id || "executive-brief", system: els.liveSystem.value }),
      });
      if (data.target_path) els.livePath.value = data.target_path;
      els.replayStatus.textContent = `${data.state} | ${data.message}`;
      refresh();
    } catch (error) {
      els.replayStatus.textContent = error.message || "Unable to start replay.";
    }
  }

  async function stopReplay() {
    try {
      const data = await ui.fetchJSON("/api/demo/replay/stop", { method: "POST" });
      els.replayStatus.textContent = `${data.state} | ${data.message}`;
      refresh();
    } catch (error) {
      els.replayStatus.textContent = error.message || "Unable to stop replay.";
    }
  }

  async function saveLiveSnapshot() {
    try {
      const data = await ui.fetchJSON("/api/live/save", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: "compare", system: els.liveSystem.value }),
      });
      els.liveSaveStatus.textContent = `Snapshot saved. Opening run ${data.run.id}.`;
      window.location.href = data.run.detail_url;
    } catch (error) {
      els.liveSaveStatus.textContent = error.message;
    }
  }

  ui.renderPathList(els.pathList, bootstrap.sample_catalog || [], {
    usePath(path) {
      els.livePath.value = path;
      els.liveSaveStatus.textContent = "Sample path copied into the live input.";
    },
    replaySample: startReplay,
  });

  if (bootstrap.preferences?.live_trace_os) {
    els.liveSystem.value = bootstrap.preferences.live_trace_os;
  }

  els.startLiveBtn.addEventListener("click", startLive);
  els.stopLiveBtn.addEventListener("click", stopLive);
  els.startReplayBtn.addEventListener("click", () => startReplay(requestedSample || bootstrap.featured_sample?.id));
  els.stopReplayBtn.addEventListener("click", stopReplay);
  els.saveLiveBtn.addEventListener("click", saveLiveSnapshot);

  if (requestedSample) startReplay(requestedSample);
  refresh();
  setInterval(refresh, 3000);
})();
