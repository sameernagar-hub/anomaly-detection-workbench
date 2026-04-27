# Anomaly Detection Workbench

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-Web_App-000000?style=for-the-badge&logo=flask&logoColor=white)
![Status](https://img.shields.io/badge/Status-Active_Prototype-157A6E?style=for-the-badge)
![Models](https://img.shields.io/badge/Models-Baseline_%2B_Argument--Aware-234B6D?style=for-the-badge)
![License](https://img.shields.io/badge/License-See_LICENSE-B3563B?style=for-the-badge)

An interactive anomaly-detection platform for structured log analysis with argument-aware scoring, drift-aware monitoring, cross-host evaluation, trusted-device access, personalized defaults, live monitoring, report generation, user-linked feedback, and archived run review.

---

## Author Spotlight

**Built and led by Sameer Nagar**

This project was designed and developed by **Sameer Nagar** as a graduate computer science project at **California State University, Fullerton (CSUF)**. It brings together anomaly detection research, applied machine learning, secure access design, live monitoring workflows, cross-host evaluation, and a full interactive workbench experience in one system.

The work reflects both the research side and the engineering side of the problem: not just training models, but shaping a usable platform around argument-aware analysis, drift-robust behavior, and practical review workflows for modern log data.

---

## What This Project Provides

This repository combines a small reusable sequence-model package with a larger Flask workbench. The web app lets a signed-in user:

- create a local account with profile and workspace preferences
- sign in with email and password, then complete a built-in human-verification step when the user or device still needs to be trusted
- use `Remember this device` to create a trusted-device record for the same user on the same machine
- trigger progressive account lockouts after repeated failed password attempts
- wait on a dedicated workspace buffer page while the environment is prepared after authentication
- analyze pasted text, uploaded files, or prepared demo samples
- compare a baseline sequence model against an argument-aware model
- watch a growing file or replay stream through the live monitoring service
- save account-scoped runs and revisit them later in the run archive
- generate theme-aware reports with embedded PDF preview using two dedicated PDF renderers: `Studio Canvas` and `Executive Brief`
- submit ratings, questions, ideas, and bug notes through an in-app feedback service with user-linked records
- export saved runs as JSON, CSV, HTML, or renderer-specific PDF
- manage profile settings, avatar uploads, theme preferences, and default analysis mode
- inspect benchmark and proxy cross-host evaluation results from a dedicated service page
- review real detection performance metrics that compare the argument-aware model against the baseline, including unseen generalization and false-positive behavior
- turn archived analytics into personalized suggestions, practical next actions, prevention ideas, and watch-next guidance on the Run Details page

The Evaluation service is not just a demo chart; it reports actual system metrics. In the current snapshot, the argument-aware model achieves 0.847 accuracy on the unseen benchmark with a 0.023 false-positive rate, while the baseline over-alerts with 0.271 accuracy and a 0.886 false-positive rate. The same-source holdout confirms strong in-domain learning, and the proxy cross-host folds demonstrate improved host-group transfer.

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

The root route opens the access flow first. After sign-in and any required human verification, the app sends the user to a temporary workspace buffer page while models and services warm up. Once initialization is ready, the user is redirected into the overview page automatically.

---

## Access Flow

1. Open `/auth/login` or `/auth/signup`.
2. Create an account if needed.
3. Sign in with email and password.
4. Complete the built-in human-verification challenge when the user or device still needs trust:
   - scribble code
   - emoji match
5. Wait on the workspace buffer page while the workbench prepares the environment.
6. Enter the authenticated workspace.

### Remembered Access

- The login page includes a `Remember this device` option.
- If enabled, the workbench stores a trusted-device token for that user and device.
- Later sign-ins on the same trusted device can skip human verification until that trust expires.
- Logging out ends the current session but does not automatically revoke the device trust.
- Resetting the password revokes existing trusted-device records for that account.

### Account Lockouts

- The access service tracks repeated failed password attempts.
- Lockouts escalate from short delays to longer blocks if failures continue.
- A successful login clears the failed-attempt ladder.

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
| `Reports Service` | Builds theme-aware exports with dual PDF renderers and embedded preview | Inline PDF preview + downloadable report |
| `FAQ / Docs` | Explains services, metrics, workflows, and troubleshooting | In-app documentation |
| `Run Archive` | Lists saved runs for the active account | Account-scoped run history |
| `Feedback Service` | Captures user-linked ratings, questions, bug notes, and suggestions | Saved feedback records |
| `Run Details` | Opens one archived run | Frozen charts, visual recommendation summary, evidence table, exports, personalized recommendations |
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
  Main Flask app, route wiring, bootstrap gating, run persistence, feedback persistence, live state, and exports.
- `examples/auth.py`
  Signup, login, trusted-device access, progressive lockouts, human verification, profile management, avatar handling, and password reset.
- `examples/workbench.py`
  Parsing, feature extraction, model loading, inference, reporting, live monitoring, and exports.
- `examples/db.py`
  SQLite schema and initialization helpers.
- `examples/emailer.py`
  SMTP or local-outbox delivery for reset emails.
- `examples/templates/`
  Multi-page Jinja templates for auth, buffer, profile, analysis, live monitoring, evaluation, reports, docs, and run history.
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
- `/reports`
- `/docs`
- `/history`
- `/feedback`
- `/runs/<run_id>`

Main API routes:

- `/api/status`
- `/api/evaluation`
- `/api/reports/catalog`
- `/api/reports/download.pdf`
- `/api/bootstrap/retry`
- `/api/analyze/text`
- `/api/analyze/upload`
- `/api/runs`
- `/api/feedback`
- `/api/profile/theme`
- `/api/live/start`
- `/api/live/stop`
- `/api/live/status`
- `/api/live/save`
- `/api/report/export.json`
- `/api/report/export.csv`
- `/api/report/export.html`

The app now keeps the main workbench routes gated until the environment finishes warming. If a user reaches the main workbench too early, the app redirects them back to the workspace buffer page.

---

## Reports Service

The Reports service gives the workbench a dedicated report workspace:

- choose a saved analysis run, the latest evaluation snapshot, or the current live-monitor result
- preview the real embedded PDF for the selected renderer before downloading
- switch between `Studio Canvas` and `Executive Brief`
- inherit the active workspace theme so exported PDFs follow `campus`, `midnight`, or `signal`
- keep long evidence values readable by moving oversized raw fields into appendix-style report sections
- use cache-busted embedded preview refresh so renderer, source, and theme changes load a fresh PDF instead of reusing a stale frame

Renderer notes:

- `Studio Canvas`
  A WeasyPrint-based PDF with a full-page layout, structured sections, and browser-based styling.
- `Executive Brief`
  A ReportLab-based PDF with compact sections, table-focused formatting, and print-oriented structure.

---

## Run Details Guidance

The Run Details page is more than a frozen archive view. It now includes a guided-response layer that helps translate saved analytics into action:

- explain what the current anomaly pattern means in user-facing language
- highlight the highest-priority interpretation signals
- suggest immediate investigation steps
- suggest prevention-oriented follow-up actions
- identify what to watch in future runs or live sessions

The guidance is derived from saved anomaly counts, drift posture, model agreement, host concentration, repeated event signatures, labeled-window metrics, and archived metadata.

This guided layer is a major analytics outcome in the workbench. The platform is designed to move beyond raw detection counts by translating a saved run into personalized suggestions and recommendations so the analyst can quickly understand what the result likely means, what to do next, what to prevent, and what to monitor in future runs.

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
- Trusted-device records and feedback history are stored in the same runtime SQLite database.

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
- remembered access uses trusted-device tokens stored as digests, not plaintext
- resetting a password revokes existing trusted-device records
- repeated failed password attempts trigger progressive temporary lockouts
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
- If the header theme resets unexpectedly, confirm the profile save request succeeded and the account is still signed in.
- If the avatar does not appear, use a supported image format and keep the file size within the configured limit.
- If the live monitor shows no updates, make sure the target file exists, is growing, and the correct system label is selected.
- If evaluation is still pending, allow the benchmark worker time to finish after bootstrap completes.
- If remembered access stops skipping verification, the trusted-device window may have expired or the password may have been reset.
- If a report preview looks blank, confirm the selected report source exists and that the chosen PDF renderer is installed from `requirements.txt`.
- If long evidence text seems abbreviated in a report table, check the appendix section of the PDF where wrapped raw excerpts are expanded.
- If inference fails, refresh model artifacts with `python examples/train_models.py`.

---

## Current Scope

This repository is still best understood as an academic and engineering prototype with a functional interface. It already supports a multi-service workflow with user-scoped personalization, buffered post-auth initialization, and archived reporting, but there is still room for future work such as:

- production-grade CSRF protection
- stronger secret and deployment management
- multi-user deployment packaging
- expanded live-ingestion integrations
- broader datasets and benchmark pipelines

---

## License

See `LICENSE`.
