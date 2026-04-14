const state = {
  dashboard: null,
};

const elements = {
  form: document.getElementById("analysis-form"),
  fileInput: document.getElementById("csv-file"),
  analyzeButton: document.getElementById("analyze-button"),
  downloadButton: document.getElementById("download-report"),
  newSessionButton: document.getElementById("new-session"),
  selectedFile: document.getElementById("selected-file"),
  statusBanner: document.getElementById("status-banner"),
  threadId: document.getElementById("thread-id"),
  results: document.getElementById("results"),
  resultTitle: document.getElementById("result-title"),
  resultSubtitle: document.getElementById("result-subtitle"),
  summaryGrid: document.getElementById("summary-grid"),
  metricCards: document.getElementById("metric-cards"),
  issueChart: document.getElementById("issue-chart"),
  severityChart: document.getElementById("severity-chart"),
  machineBreakdown: document.getElementById("machine-breakdown"),
  analysisCopy: document.getElementById("analysis-copy"),
  solutionsList: document.getElementById("solutions-list"),
};

function createThreadId() {
  if (globalThis.crypto && typeof globalThis.crypto.randomUUID === "function") {
    return globalThis.crypto.randomUUID();
  }
  return `session-${Date.now()}`;
}

function setStatus(message, tone = "idle") {
  elements.statusBanner.textContent = message;
  elements.statusBanner.dataset.tone = tone;
}

function setSelectedFileLabel(file) {
  elements.selectedFile.textContent = file ? file.name : "None yet";
}

function formatMetricValue(metric, value, unit) {
  if (metric === "error_rate") {
    return `${(Number(value) * 100).toFixed(2)}${unit}`;
  }
  return `${Number(value).toFixed(2)} ${unit}`;
}

function formatChartValue(value) {
  return Number(value).toFixed(0);
}

function titleCase(value) {
  return String(value).replace(/_/g, " ").replace(/\b\w/g, (character) => character.toUpperCase());
}

function renderSummary(dashboard) {
  const cards = [
    {
      label: "Rows",
      value: dashboard.plant_snapshot.record_count,
      caption: "Telemetry entries loaded",
    },
    {
      label: "Machines",
      value: dashboard.plant_snapshot.machine_count,
      caption: "Unique assets covered",
    },
    {
      label: "Issues",
      value: dashboard.analysis_result.issues.length,
      caption: "Detected threshold breaches",
    },
    {
      label: "Confidence",
      value: `${Math.round(dashboard.analysis_result.confidence_score * 100)}%`,
      caption: "Validation score",
    },
  ];

  elements.summaryGrid.innerHTML = cards
    .map(
      (card) => `
        <article class="summary-card">
          <div class="meta-label">${card.label}</div>
          <div class="value">${card.value}</div>
          <p class="drop-copy">${card.caption}</p>
        </article>
      `,
    )
    .join("");
}

function renderMetricCards(cards) {
  elements.metricCards.innerHTML = cards
    .map((card) => {
      const ratio = card.threshold > 0 ? Math.min((card.max_value / card.threshold) * 100, 100) : 0;
      return `
        <article class="metric-card" data-status="${card.status}">
          <div class="metric-top">
            <div>
              <p class="eyebrow">${card.label}</p>
              <h4>${card.label}</h4>
            </div>
            <span class="status-pill" data-status="${card.status}">${card.status}</span>
          </div>
          <div class="chart-track" aria-hidden="true">
            <div class="chart-fill" style="--fill: ${ratio}%; --bar-color: ${
              card.status === "alert"
                ? "var(--alert)"
                : card.status === "watch"
                  ? "var(--watch)"
                  : "var(--success)"
            };"></div>
          </div>
          <div class="metric-values">
            <div class="metric-row">
              <span>Average</span>
              <strong>${formatMetricValue(card.metric, card.average_value, card.unit)}</strong>
            </div>
            <div class="metric-row">
              <span>Peak</span>
              <strong>${formatMetricValue(card.metric, card.max_value, card.unit)}</strong>
            </div>
            <div class="metric-row">
              <span>Threshold</span>
              <strong>${formatMetricValue(card.metric, card.threshold, card.unit)}</strong>
            </div>
            <div class="metric-row">
              <span>Breaches</span>
              <strong>${card.breach_count} rows / ${card.impacted_machine_count} machines</strong>
            </div>
          </div>
        </article>
      `;
    })
    .join("");
}

function renderChart(container, items) {
  const maxValue = Math.max(...items.map((item) => Number(item.value)), 1);
  container.innerHTML = items
    .map(
      (item) => `
        <div class="chart-row">
          <header>
            <strong>${item.label}</strong>
            <span>${formatChartValue(item.value)}</span>
          </header>
          <div class="chart-track" aria-hidden="true">
            <div class="chart-fill" style="--fill: ${(Number(item.value) / maxValue) * 100}%; --bar-color: ${
              item.color || "var(--steel)"
            };"></div>
          </div>
        </div>
      `,
    )
    .join("");
}

function renderMachines(machines) {
  if (!machines.length) {
    elements.machineBreakdown.innerHTML =
      '<p class="drop-copy">No machine hotspots were highlighted for this dataset.</p>';
    return;
  }

  elements.machineBreakdown.innerHTML = machines
    .map(
      (machine) => `
        <article class="machine-card">
          <div class="solution-head">
            <h4>${machine.machine_id}</h4>
            <span class="status-pill" data-status="${
              machine.issue_count > 0 ? "watch" : "stable"
            }">${machine.issue_count} issues</span>
          </div>
          <dl>
            <div>
              <dt>Avg temperature</dt>
              <dd>${Number(machine.average_temperature).toFixed(2)} C</dd>
            </div>
            <div>
              <dt>Avg error rate</dt>
              <dd>${(Number(machine.average_error_rate) * 100).toFixed(2)}%</dd>
            </div>
            <div>
              <dt>Total downtime</dt>
              <dd>${Number(machine.total_downtime_minutes).toFixed(2)} min</dd>
            </div>
            <div>
              <dt>Issue count</dt>
              <dd>${machine.issue_count}</dd>
            </div>
          </dl>
        </article>
      `,
    )
    .join("");
}

function renderSolutions(solutions) {
  if (!solutions.length) {
    elements.solutionsList.innerHTML =
      '<p class="drop-copy">No actions were returned for the current analysis.</p>';
    return;
  }

  elements.solutionsList.innerHTML = solutions
    .map((solution) => {
      const title = solution.title || solution.action || "Recommended action";
      const priority = titleCase(solution.priority || "unspecified");
      const rationale =
        solution.rationale ||
        solution.expected_impact ||
        "Action recommended by the analysis workflow.";
      const actions =
        Array.isArray(solution.actions) && solution.actions.length
          ? solution.actions
          : solution.action
            ? [solution.action]
            : [];

      return `
        <article class="solution-card">
          <div class="solution-head">
            <h4>${title}</h4>
            <span class="priority-pill">${priority}</span>
          </div>
          <p>${rationale}</p>
          ${
            actions.length
              ? `<ul>${actions.map((action) => `<li>${action}</li>`).join("")}</ul>`
              : ""
          }
        </article>
      `;
    })
    .join("");
}

function renderDashboard(dashboard, fallbackSourceName) {
  const sourceName = dashboard.source_name || fallbackSourceName || "Uploaded dataset";
  elements.results.classList.remove("hidden");
  elements.resultTitle.textContent = `${sourceName} analysis`;
  elements.resultSubtitle.textContent =
    `Session ${dashboard.thread_id} | ${dashboard.plant_snapshot.machine_count} machines | ` +
    `${dashboard.plant_snapshot.record_count} telemetry rows`;
  elements.analysisCopy.textContent = dashboard.analysis_result.analysis;

  renderSummary(dashboard);
  renderMetricCards(dashboard.metric_cards);
  renderChart(elements.issueChart, dashboard.issue_breakdown);
  renderChart(elements.severityChart, dashboard.severity_breakdown);
  renderMachines(dashboard.machine_breakdown);
  renderSolutions(dashboard.analysis_result.solutions);
}

async function parseError(response) {
  try {
    const payload = await response.json();
    if (payload && payload.detail) {
      return payload.detail;
    }
  } catch (error) {
    return response.statusText || "Request failed.";
  }
  return response.statusText || "Request failed.";
}

async function runAnalysis(event) {
  event.preventDefault();
  const file = elements.fileInput.files[0];
  if (!file) {
    setStatus("Choose a CSV file before running the analysis.", "error");
    return;
  }

  state.dashboard = null;
  elements.downloadButton.disabled = true;
  elements.analyzeButton.disabled = true;
  setStatus("Running the LangGraph pipeline and building the dashboard...", "loading");

  const formData = new FormData();
  formData.append("file", file);
  formData.append("thread_id", elements.threadId.value);

  try {
    const response = await fetch("/analyze/dashboard", {
      method: "POST",
      body: formData,
    });
    if (!response.ok) {
      throw new Error(await parseError(response));
    }

    state.dashboard = await response.json();
    elements.threadId.value = state.dashboard.thread_id || elements.threadId.value;
    renderDashboard(state.dashboard, file.name);
    elements.downloadButton.disabled = false;
    setStatus("Analysis ready. Review the visuals or download the PDF report.", "success");
  } catch (error) {
    setStatus(error.message || "Analysis failed.", "error");
  } finally {
    elements.analyzeButton.disabled = false;
  }
}

async function downloadPdf() {
  if (!state.dashboard) {
    return;
  }

  elements.downloadButton.disabled = true;
  setStatus("Generating PDF report...", "loading");

  try {
    const response = await fetch("/reports/pdf", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(state.dashboard),
    });
    if (!response.ok) {
      throw new Error(await parseError(response));
    }

    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    const baseName = (state.dashboard.source_name || "manufacturing-analysis").replace(/\.[^.]+$/, "");
    anchor.href = url;
    anchor.download = `${baseName}-report.pdf`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
    setStatus("PDF report downloaded.", "success");
  } catch (error) {
    setStatus(error.message || "PDF generation failed.", "error");
  } finally {
    elements.downloadButton.disabled = false;
  }
}

elements.threadId.value = createThreadId();
elements.fileInput.addEventListener("change", () => {
  setSelectedFileLabel(elements.fileInput.files[0]);
});
elements.newSessionButton.addEventListener("click", () => {
  elements.threadId.value = createThreadId();
  setStatus("Started a new memory session for the next analysis.", "idle");
});
elements.form.addEventListener("submit", runAnalysis);
elements.downloadButton.addEventListener("click", downloadPdf);
