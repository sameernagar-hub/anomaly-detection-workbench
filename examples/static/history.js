(function () {
  const ui = window.WorkbenchUI;
  const grid = document.getElementById("historyGrid");

  async function refresh() {
    try {
      const data = await ui.fetchJSON("/api/runs");
      ui.renderRunCards(grid, data.runs || [], "No runs saved yet.");
    } catch (error) {
      grid.innerHTML = `<div class="report-card muted">${error.message || "Unable to load run history right now."}</div>`;
    }
  }

  refresh();
})();
