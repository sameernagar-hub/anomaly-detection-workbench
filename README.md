# Anomaly Detection Workbench

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-Web_App-000000?style=for-the-badge&logo=flask&logoColor=white)
![Status](https://img.shields.io/badge/Status-Active_Prototype-157A6E?style=for-the-badge)
![Models](https://img.shields.io/badge/Models-Baseline_%2B_Argument--Aware-234B6D?style=for-the-badge)
![License](https://img.shields.io/badge/License-See_LICENSE-B3563B?style=for-the-badge)

An interactive anomaly-detection system for structured log analysis with separate services for analysis, live monitoring, evaluation, and archived run review.

---

## Why This Project Pops

This project is not just a model demo. It is a working multi-page analysis application that lets you:

- run anomaly detection on pasted text, uploaded files, and prepared samples
- monitor a live-updating log stream without overwriting archived results
- compare a baseline sequence model against an improved argument-aware model
- save, reopen, and export completed runs
- inspect benchmark and proxy cross-host evaluation results in a separate service view

---

## Quick Start

### 1. Create and activate a virtual environment

#### Windows PowerShell

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

#### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Start the app

```bash
python examples/app.py
```

### 4. Open the web app

```text
http://127.0.0.1:5000/
```

You will be redirected to:

```text
http://127.0.0.1:5000/overview
```

> Tip
> The app starts on the `Overview` page and then branches into dedicated service pages for analysis, live monitoring, evaluation, and archived runs.

---

## Table Of Contents

- [Features](#features)
- [App Services](#app-services)
- [Typical Workflow](#typical-workflow)
- [Project Structure](#project-structure)
- [Setup And Installation](#setup-and-installation)
- [How To Run The App](#how-to-run-the-app)
- [Evaluation Scripts](#evaluation-scripts)
- [Data And Runtime Paths](#data-and-runtime-paths)
- [Exports](#exports)
- [Technical Notes](#technical-notes)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

## Features

### Core Detection

- baseline next-event anomaly detection
- improved argument-aware anomaly scoring
- adaptive threshold status reporting
- drift-aware reporting signals

### Application Workflow

- text analysis
- uploaded file analysis
- prepared sample analysis
- live file-tail monitoring
- replay-driven live demo flow
- archived run history with dedicated result pages

### Review And Reporting

- frozen run detail pages
- evidence tables with filtering
- run exports to JSON, CSV, and HTML
- benchmark evaluation page
- proxy cross-host comparison page

---

## App Services

The web app is now organized into separate service windows so each workflow has its own space.

| Service | Purpose | Main Output |
| --- | --- | --- |
| `Overview` | Shows app health, current run summary, and navigation | Status + latest archived run |
| `Analysis Service` | Runs text, upload, and sample analysis | New saved run |
| `Live Monitoring Service` | Tails a growing file or replay stream | Live-updating result stream |
| `Evaluation Service` | Compares models using benchmark metrics | Metrics + cross-host comparison |
| `Run Archive` | Lists saved runs | Run history |
| `Run Details` | Opens one archived run | Frozen chart, evidence table, exports |

---

## Typical Workflow

1. Open `Overview` to confirm the system is ready.
2. Go to `Analysis Service` to submit text, a file, or a sample scenario.
3. Let the app generate a new saved run.
4. Review the dedicated `Run Details` page for that run.
5. Use `Run Archive` to reopen older results later.
6. Use `Live Monitoring Service` when you want a continuously updating stream.
7. Archive a live snapshot when you want that state preserved as a normal run.
8. Open `Evaluation Service` to review benchmark metrics separately from operational analysis.

---

## Project Structure

```text
anomaly-detection-workbench/
|-- README.md
|-- requirements.txt
|-- LICENSE
|-- examples/
|   |-- app.py
|   |-- workbench.py
|   |-- train_models.py
|   |-- evaluate_models.py
|   |-- cross_host_eval.py
|   |-- templates/
|   |-- static/
|   |-- sample_data/
|   |-- uploads/
|   |-- demo_runtime/
|   `-- artifacts/
```

### Key Files

- `examples/app.py`
  Flask routes, API endpoints, run archive storage, and page wiring.
- `examples/workbench.py`
  Parsing, feature extraction, inference, reporting, export, and live-monitor logic.
- `examples/templates/`
  Multi-page HTML templates for the app services.
- `examples/static/`
  Shared UI logic, service-specific scripts, and styling.
- `examples/train_models.py`
  Generates or refreshes model artifacts.
- `examples/evaluate_models.py`
  Runs standard evaluation.
- `examples/cross_host_eval.py`
  Runs proxy cross-host evaluation.

---

## Setup And Installation

### Requirements

- Python 3.10 or newer recommended
- `pip`
- local terminal access

### Install Steps

1. Clone or extract this repository.
2. Open a terminal in the project root.
3. Create a virtual environment.
4. Activate the virtual environment.
5. Install dependencies with `pip install -r requirements.txt`.

### Windows PowerShell

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## How To Run The App

Run the Flask application from the project root:

```bash
python examples/app.py
```

Then open:

```text
http://127.0.0.1:5000/
```

### Main Routes

- `/overview`
- `/analyze`
- `/live`
- `/evaluation`
- `/history`
- `/runs/<run_id>`

> Note
> The app stores recent runs in memory during the current Flask session. Restarting the server clears that in-memory archive unless you add persistence later.

---

## Analysis Modes

When running analysis, the app supports three result views:

- `Dual Command View`
  Shows baseline and improved model outputs together.
- `Baseline Sentinel only`
  Hides the improved-model columns in the saved run.
- `Apex Insight only`
  Hides the baseline-model columns in the saved run.

---

## Evaluation Scripts

### Run Standard Evaluation

```bash
python examples/evaluate_models.py
```

### Run Proxy Cross-Host Evaluation

```bash
python examples/cross_host_eval.py
```

### Train Or Refresh Model Artifacts

```bash
python examples/train_models.py
```

---

## Data And Runtime Paths

### Prepared Sample Inputs

- `examples/sample_data/`

### Uploaded Files

- `examples/uploads/`

### Replay-Generated Live Files

- `examples/demo_runtime/`

### Model Artifacts

- `examples/artifacts/`

---

## Exports

Saved runs can be exported as:

- `JSON`
- `CSV`
- `HTML`

The run export flow is tied to a specific archived run so a previously completed result can be revisited and exported later without rerunning the analysis.

---

## Technical Notes

- The live monitor watches a local file and re-runs inference when the file grows.
- The live page is intentionally separated from archived run details so ongoing updates do not overwrite previously reviewed charts.
- Cross-host evaluation uses proxy host-group features derived from available dataset fields.
- Host grouping can come from explicit host fields, machine values, or fallback derived groups.
- Adaptive thresholding is exposed as a runtime status/control concept inside the app.
- The current run archive is session-based and stored in memory by the Flask process.

---

## Troubleshooting

If the app does not behave as expected, check these first:

1. Your virtual environment is active.
2. Dependencies were installed from `requirements.txt`.
3. You are running the app from the project root.
4. `http://127.0.0.1:5000/` is reachable in your browser.
5. Model artifacts exist or can be generated with:

```bash
python examples/train_models.py
```

### Common Checks

- If the app starts but predictions fail, retrain or refresh artifacts.
- If the live monitor shows no updates, make sure the target file is actually growing.
- If run history looks empty after a restart, remember that the current archive is in memory.

---

## Current Scope

This repository is best understood as an academic and engineering prototype with a functional interface. It already supports a multi-service workflow, but there is still room for future work such as:

- persistent run storage
- richer authentication and user management
- stronger production deployment packaging
- deeper live-ingestion integrations
- expanded datasets and benchmark pipelines

---

## License

See `LICENSE`.
