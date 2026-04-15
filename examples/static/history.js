(function () {
  const ui = window.WorkbenchUI;
  const grid = document.getElementById("historyGrid");
  const feedbackGrid = document.getElementById("feedbackHistoryGrid");

  async function refresh() {
    try {
      const [runData, feedbackData] = await Promise.all([
        ui.fetchJSON("/api/runs"),
        ui.fetchJSON("/api/feedback"),
      ]);
      const data = runData || {};
      ui.renderRunCards(grid, data.runs || [], "No runs saved yet.");
      ui.renderFeedbackCards(feedbackGrid, (feedbackData || {}).feedback || [], "No feedback saved yet.");
    } catch (error) {
      grid.innerHTML = `<div class="report-card muted">${error.message || "Unable to load run history right now."}</div>`;
      if (feedbackGrid) {
        feedbackGrid.innerHTML = `<div class="report-card muted">${error.message || "Unable to load feedback history right now."}</div>`;
      }
    }
  }

  refresh();
})();
