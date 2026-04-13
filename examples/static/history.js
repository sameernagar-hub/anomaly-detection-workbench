(function () {
  const ui = window.WorkbenchUI;
  const grid = document.getElementById("historyGrid");

  async function refresh() {
    const data = await ui.fetchJSON("/api/runs");
    ui.renderRunCards(grid, data.runs || [], "No runs saved yet.");
  }

  refresh();
})();
