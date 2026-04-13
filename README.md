# Anomaly Detection Workbench

This repository contains a working anomaly-detection prototype for sequence-based system-log analysis. It includes:

- a baseline sequence model
- an argument-aware comparison model
- a Flask application for upload, live log monitoring, visualization, and report export
- evaluation scripts for standard and proxy cross-host experiments

## Project Focus

The prototype is designed for academic demonstration of anomaly detection on structured log data. The current implementation supports:

- baseline next-event anomaly detection
- argument-aware anomaly scoring
- adaptive threshold monitoring for drift-sensitive behavior
- upload and live file-tail analysis
- exportable JSON, CSV, and printable HTML reports

## Main Entry Points

- `python examples/app.py`
  Starts the main web application.

- `python examples/train_models.py`
  Builds or refreshes saved model artifacts.

- `python examples/evaluate_models.py`
  Runs the standard evaluation and proxy cross-host evaluation.

## Notes

- The live mode tails log files in real time; it does not capture kernel syscalls directly.
- Cross-host evaluation currently uses proxy host-group features derived from the available dataset fields.
- This repository includes baseline-model components for comparison, but the project presentation is framed as a general anomaly-detection system.
