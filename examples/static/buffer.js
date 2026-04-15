(function () {
  const ui = window.WorkbenchUI;
  const bootstrapElement = document.getElementById("bootstrap-data");
  const bootstrap = bootstrapElement ? JSON.parse(bootstrapElement.textContent) : {};
  const bufferConfig = bootstrap.buffer || {};
  const messages = Array.isArray(bufferConfig.messages) && bufferConfig.messages.length
    ? bufferConfig.messages
    : ["Preparing your workbench..."];
  const nextPath = bufferConfig.next_path || "/overview";
  const els = {
    rotatingMessage: document.getElementById("bufferRotatingMessage"),
    detailMessage: document.getElementById("bufferDetailMessage"),
    bootstrapState: document.getElementById("bufferBootstrapState"),
    bootstrapMessage: document.getElementById("bufferBootstrapMessage"),
    handoffState: document.getElementById("bufferHandoffState"),
    handoffMessage: document.getElementById("bufferHandoffMessage"),
    leadStatus: document.getElementById("bufferLeadStatus"),
    supportStatus: document.getElementById("bufferSupportStatus"),
    retryBtn: document.getElementById("bufferRetryBtn"),
  };

  let messageIndex = 0;
  let redirecting = false;

  function rotateMessage() {
    if (!els.rotatingMessage) return;
    messageIndex = (messageIndex + 1) % messages.length;
    els.rotatingMessage.textContent = messages[messageIndex];
  }

  function applyBootstrapState(bootstrapStatus) {
    const state = bootstrapStatus?.state || "starting";
    const message = bootstrapStatus?.message || "Preparing your workbench.";
    if (els.bootstrapState) els.bootstrapState.textContent = state.charAt(0).toUpperCase() + state.slice(1);
    if (els.bootstrapMessage) els.bootstrapMessage.textContent = message;
    if (els.detailMessage) els.detailMessage.textContent = message;

    if (state === "ready") {
      if (els.handoffState) els.handoffState.textContent = "Ready";
      if (els.handoffMessage) els.handoffMessage.textContent = "Opening your personalized workspace now.";
      if (els.leadStatus) els.leadStatus.textContent = "Workspace ready. Redirecting now.";
      if (els.supportStatus) els.supportStatus.textContent = "Your analysis services are loaded and your environment is prepared.";
      if (els.retryBtn) els.retryBtn.hidden = true;
      if (!redirecting) {
        redirecting = true;
        window.setTimeout(() => {
          window.location.href = nextPath;
        }, 700);
      }
      return;
    }

    if (state === "error") {
      if (els.handoffState) els.handoffState.textContent = "Attention";
      if (els.handoffMessage) els.handoffMessage.textContent = "Preparation hit a problem. Retry the environment warmup to continue.";
      if (els.leadStatus) els.leadStatus.textContent = "We hit a snag while preparing your workspace.";
      if (els.supportStatus) els.supportStatus.textContent = message;
      if (els.retryBtn) els.retryBtn.hidden = false;
      return;
    }

    if (els.handoffState) els.handoffState.textContent = "Buffering";
    if (els.handoffMessage) els.handoffMessage.textContent = "You will continue automatically once initialization finishes.";
    if (els.leadStatus) els.leadStatus.textContent = "Please wait while we prepare your workbench.";
    if (els.supportStatus) els.supportStatus.textContent = "Loading models, applying preferences, and securing your environment.";
    if (els.retryBtn) els.retryBtn.hidden = true;
  }

  async function refreshStatus() {
    const status = await ui.fetchJSON("/api/status");
    applyBootstrapState(status.bootstrap);
  }

  async function retryBootstrap() {
    const payload = await ui.fetchJSON("/api/bootstrap/retry", { method: "POST" });
    applyBootstrapState(payload.bootstrap);
  }

  if (els.retryBtn) {
    els.retryBtn.addEventListener("click", () => {
      retryBootstrap().catch((error) => {
        if (els.supportStatus) els.supportStatus.textContent = error.message;
      });
    });
  }

  applyBootstrapState({
    state: document.getElementById("bufferBootstrapState")?.textContent?.toLowerCase() || "starting",
    message: document.getElementById("bufferBootstrapMessage")?.textContent || "Preparing your workbench.",
  });
  refreshStatus().catch((error) => {
    if (els.supportStatus) els.supportStatus.textContent = error.message;
  });
  window.setInterval(rotateMessage, 2200);
  window.setInterval(() => {
    if (!redirecting) {
      refreshStatus().catch((error) => {
        if (els.supportStatus) els.supportStatus.textContent = error.message;
      });
    }
  }, 2500);
})();
