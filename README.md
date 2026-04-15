# Anomaly Detection Workbench

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-Web_App-000000?style=for-the-badge&logo=flask&logoColor=white)
![Status](https://img.shields.io/badge/Status-Active_Prototype-157A6E?style=for-the-badge)
![Models](https://img.shields.io/badge/Models-Baseline_%2B_Argument--Aware-234B6D?style=for-the-badge)
![License](https://img.shields.io/badge/License-See_LICENSE-B3563B?style=for-the-badge)

An interactive anomaly-detection platform for structured log analysis with account-aware workspaces, personalized defaults, buffered post-auth initialization, live monitoring, benchmark evaluation, and archived run review.

---

## What This Project Provides

This repository combines a small reusable sequence-model package with a larger Flask workbench. The web app lets a signed-in user:

- create a local account with profile and workspace preferences
- sign in with email and password, then complete a built-in human-verification step
- wait on a dedicated workspace buffer page while the environment is prepared after authentication
- analyze pasted text, uploaded files, or prepared demo samples
- compare a baseline sequence model against an argument-aware model
- watch a growing file or replay stream through the live monitoring service
- save account-scoped runs and revisit them later in the run archive
- export saved runs as JSON, CSV, or HTML
- manage profile settings, avatar uploads, theme preferences, and default analysis mode
- inspect benchmark and proxy cross-host evaluation results from a dedicated service page

---

## Quick Start

### 1. Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

macOS / Linux:

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

The root route opens the access flow first. After sign-in and human verification, the app sends the user to a temporary workspace buffer page while models and services warm up. Once initialization is ready, the user is redirected into the overview page automatically.

---

## Access Flow

1. Open `/auth/login` or `/auth/signup`.
2. Create an account if needed.
3. Sign in with email and password.
4. Complete the built-in human-verification challenge:
   - scribble code
   - emoji match
5. Wait on the workspace buffer page while the workbench prepares the environment.
6. Enter the authenticated workspace.

### Remembered Access

- The login page includes a `Remember this device` option.
- If enabled, the session can remain active longer on that device.
- If disabled, the session behaves like a shorter-lived standard session.

### Password Recovery

- Forgot-password requests generate a reset link.
- In development, email delivery can fall back to a local outbox file under `examples/runtime/outbox/`.
- Creating a new reset request invalidates earlier unconsumed reset links for that account.

---

## App Services

| Service | Purpose | Main Output |
| --- | --- | --- |
| `Access Service` | Handles signup, login, password reset, and human verification | Authenticated session |
| `Workspace Buffer` | Prepares the personalized environment after authentication | Automatic handoff to overview |
| `Overview` | Shows readiness, status, current run summary, and navigation | Status + latest run |
| `Analysis Service` | Runs text, upload, and sample analysis | New saved run |
| `Live Monitoring Service` | Tails a growing file or replay stream with system context | Live-updating inference stream |
| `Evaluation Service` | Compares baseline and improved models using benchmark metrics | Metrics + cross-host comparison |
| `FAQ / Docs` | Explains services, metrics, workflows, and troubleshooting | In-app documentation |
| `Run Archive` | Lists saved runs for the active account | Account-scoped run history |
| `Run Details` | Opens one archived run | Frozen charts, evidence table, exports |
| `Profile Service` | Manages account identity, avatar, and defaults | Personalized settings |

---

## Analysis Modes

The workbench supports three saved-result modes:

- `Dual Command View`: show baseline and improved-model outputs together
- `Baseline Sentinel only`: hide improved-model columns in the saved run
- `Apex Insight only`: hide baseline-model columns in the saved run

---

## Project Structure

```text
anomaly-detection-workbench/
|-- README.md
|-- requirements.txt
|-- setup.py
|-- anomaly_detection/
|   |-- __init__.py
|   |-- __main__.py
|   |-- model.py
|   `-- preprocessor.py
`-- examples/
    |-- app.py
    |-- auth.py
    |-- db.py
    |-- emailer.py
    |-- human_verification.py
    |-- security.py
    |-- workbench.py
    |-- train_models.py
    |-- evaluate_models.py
    |-- cross_host_eval.py
    |-- templates/
    |-- static/
    |-- sample_data/
    |-- artifacts/
    |-- uploads/
    |-- demo_runtime/
    `-- runtime/
```

### Key Files

- `anomaly_detection/model.py`
  Baseline LSTM sequence anomaly model.
- `anomaly_detection/preprocessor.py`
  Event sequencing and CSV/TXT preprocessing helpers.
- `examples/app.py`
  Main Flask app, route wiring, bootstrap gating, run persistence, live state, and exports.
- `examples/auth.py`
  Signup, login, remembered sessions, human verification, profile management, avatar handling, and password reset.
- `examples/workbench.py`
  Parsing, feature extraction, model loading, inference, reporting, live monitoring, and exports.
- `examples/db.py`
  SQLite schema and initialization helpers.
- `examples/emailer.py`
  SMTP or local-outbox delivery for reset emails.
- `examples/templates/`
  Multi-page Jinja templates for auth, buffer, profile, analysis, live monitoring, evaluation, docs, and run history.
- `examples/static/`
  Shared UI behavior, page-specific scripts, and theme styling.

---

## How To Run The App

From the project root:

```bash
python examples/app.py
```

Main user-facing routes:

- `/`
- `/auth/login`
- `/auth/signup`
- `/auth/verify-human`
- `/auth/forgot-password`
- `/auth/reset-password/<token>`
- `/workspace-buffer`
- `/profile`
- `/overview`
- `/analyze`
- `/live`
- `/evaluation`
- `/docs`
- `/history`
- `/runs/<run_id>`

Main API routes:

- `/api/status`
- `/api/evaluation`
- `/api/bootstrap/retry`
- `/api/analyze/text`
- `/api/analyze/upload`
- `/api/runs`
- `/api/live/start`
- `/api/live/stop`
- `/api/live/status`
- `/api/live/save`
- `/api/report/export.json`
- `/api/report/export.csv`
- `/api/report/export.html`

The app now keeps the main workbench routes gated until the environment finishes warming. If a user reaches the main workbench too early, the app redirects them back to the workspace buffer page.

---

## Evaluation And Training Scripts

Run standard evaluation:

```bash
python examples/evaluate_models.py
```

Run proxy cross-host evaluation:

```bash
python examples/cross_host_eval.py
```

Train or refresh model artifacts:

```bash
python examples/train_models.py
```

Run the package CLI:

```bash
python -m anomaly_detection train --csv path/to/events.csv --save model.pt
python -m anomaly_detection predict --csv path/to/events.csv --load model.pt
```

---

## Data And Runtime Paths

- Prepared sample inputs: `examples/sample_data/`
- Model artifacts: `examples/artifacts/`
- Uploaded files: `examples/uploads/`
- Replay-generated live files: `examples/demo_runtime/`
- Runtime database, avatars, and local mail outbox: `examples/runtime/`

---

## Environment Variables

The project runs without extra configuration for local development, but these variables are supported:

- `WORKBENCH_SECRET_KEY`
  Explicit Flask session secret. Recommended outside throwaway local runs.
- `WORKBENCH_SECURE_COOKIE=1`
  Marks the session cookie as secure. Use when serving over HTTPS.
- `FLASK_DEBUG=1`
  Enables Flask debug mode.
- `PORT`
  Overrides the default local port `5000`.
- `WORKBENCH_SMTP_HOST`
- `WORKBENCH_SMTP_PORT`
- `WORKBENCH_SMTP_USERNAME`
- `WORKBENCH_SMTP_PASSWORD`
- `WORKBENCH_SMTP_SENDER`
- `WORKBENCH_SMTP_TLS`

If SMTP variables are not configured, reset emails are captured to the local outbox instead of being sent externally.

---

## Security And Development Notes

This is still a prototype, but a few guardrails are built in:

- password hashing uses Werkzeug password hashes
- password policy checks enforce length and character diversity
- password reset tokens are stored as digests, not plaintext
- generating a new reset request invalidates older pending reset tokens for that user
- the app keeps the main workspace gated until post-auth initialization completes
- session cookies are configured as `HttpOnly` and `SameSite=Lax`
- the app supports an explicit secret key via environment variable instead of requiring a hardcoded development secret

Still important:

- this is not production-grade anti-bot protection
- there is no full CSRF framework in place yet
- SQLite with `check_same_thread=False` is acceptable for this prototype but not a production concurrency strategy
- model artifact trust matters because PyTorch model loading assumes trusted local files

---

## Troubleshooting

If the app does not behave as expected, check these first:

1. The virtual environment is active.
2. Dependencies were installed from `requirements.txt`.
3. You are running the app from the project root.
4. `http://127.0.0.1:5000/` is reachable.
5. Model artifacts exist or can be regenerated with `python examples/train_models.py`.

Common checks:

- If login succeeds but the app pauses on the buffer page, give the model warmup worker time to finish or use the retry button if initialization failed.
- If password-reset emails do not appear in an inbox, check `examples/runtime/outbox/`.
- If the avatar does not appear, use a supported image format and keep the file size within the configured limit.
- If the live monitor shows no updates, make sure the target file exists, is growing, and the correct system label is selected.
- If evaluation is still pending, allow the benchmark worker time to finish after bootstrap completes.
- If inference fails, refresh model artifacts with `python examples/train_models.py`.

---

## Current Scope

This repository is still best understood as an academic and engineering prototype with a functional interface. It already supports a multi-service workflow with account-aware personalization, buffered post-auth initialization, and archived reporting, but there is still room for future work such as:

- production-grade CSRF protection
- stronger secret and deployment management
- multi-user deployment packaging
- richer live-ingestion integrations
- broader datasets and benchmark pipelines

---

## License

See `LICENSE`.
