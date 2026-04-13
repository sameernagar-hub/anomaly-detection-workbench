(function () {
  const ui = window.WorkbenchUI;
  const bootstrap = ui.bootstrap;
  const els = {
    logText: document.getElementById("logText"),
    analysisMode: document.getElementById("analysisMode"),
    analysisStatus: document.getElementById("analysisStatus"),
    scenarioGrid: document.getElementById("scenarioGrid"),
    uploadFile: document.getElementById("uploadFile"),
    analyzeTextBtn: document.getElementById("analyzeTextBtn"),
    analyzeUploadBtn: document.getElementById("analyzeUploadBtn"),
    loadFeaturedBtn: document.getElementById("loadFeaturedBtn"),
    loadDefaultBtn: document.getElementById("loadDefaultBtn"),
  };

  function goToRun(run) {
    window.location.href = run.detail_url;
  }

  async function loadSample(sampleId) {
    const data = await ui.fetchJSON(`/api/demo/sample/${sampleId}/text`);
    els.logText.value = data.text || "";
    els.analysisStatus.textContent = `${data.sample.title} loaded into the text console.`;
  }

  async function analyzeSample(sampleId) {
    els.analysisStatus.textContent = "Running sample analysis...";
    const data = await ui.fetchJSON(`/api/demo/sample/${sampleId}/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode: els.analysisMode.value }),
    });
    goToRun(data.run);
  }

  async function analyzeText() {
    els.analysisStatus.textContent = "Analyzing pasted text...";
    const data = await ui.fetchJSON("/api/analyze/text", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: els.logText.value, mode: els.analysisMode.value }),
    });
    goToRun(data.run);
  }

  async function analyzeUpload() {
    if (!els.uploadFile.files.length) {
      els.analysisStatus.textContent = "Choose an upload file first.";
      return;
    }
    els.analysisStatus.textContent = "Uploading and analyzing file...";
    const formData = new FormData();
    formData.append("file", els.uploadFile.files[0]);
    formData.append("mode", els.analysisMode.value);
    const response = await fetch("/api/analyze/upload", { method: "POST", body: formData });
    const data = await response.json();
    if (!response.ok) {
      els.analysisStatus.textContent = data.error || "Upload failed.";
      return;
    }
    goToRun(data.run);
  }

  els.logText.value = bootstrap.sample_text || "";
  ui.renderScenarioGrid(els.scenarioGrid, bootstrap.sample_catalog || [], {
    loadSample,
    analyzeSample,
    replaySample(sampleId) {
      window.location.href = `/live?sample=${encodeURIComponent(sampleId)}`;
    },
  });

  els.analyzeTextBtn.addEventListener("click", analyzeText);
  els.analyzeUploadBtn.addEventListener("click", analyzeUpload);
  els.loadFeaturedBtn.addEventListener("click", () => {
    els.logText.value = bootstrap.sample_text || "";
    els.analysisStatus.textContent = "Featured sample loaded.";
  });
  els.loadDefaultBtn.addEventListener("click", () => {
    els.logText.value = bootstrap.default_upload_text || "";
    els.analysisStatus.textContent = "Default text loaded.";
  });
})();
