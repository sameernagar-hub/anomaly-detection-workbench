from __future__ import annotations

import json
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from workbench import AnomalyWorkbench


def print_metric_block(name: str, metrics: dict) -> None:
    print(name)
    print(f"  accuracy: {metrics.get('accuracy')}")
    print(f"  precision: {metrics.get('precision')}")
    print(f"  recall: {metrics.get('recall')}")
    print(f"  f1: {metrics.get('f1')}")
    print(f"  false_positive_rate: {metrics.get('false_positive_rate')}")
    print(f"  tp/fp/tn/fn: {metrics.get('tp')}/{metrics.get('fp')}/{metrics.get('tn')}/{metrics.get('fn')}")


def main() -> None:
    workbench = AnomalyWorkbench(BASE_DIR)
    workbench.ensure_ready()

    train_normal, test_normal, test_attack = workbench._training_records()
    evaluation_records = test_normal + test_attack
    result = workbench.predict_records(evaluation_records)

    print("Standard evaluation")
    print(json.dumps({
        "window_count": result["summary"]["window_count"],
        "distinct_host_groups": result["summary"]["distinct_host_groups"],
        "agreement_rate": result["summary"]["agreement_rate"],
        "drift": result["summary"]["drift"],
        "adaptive_threshold": result["summary"]["adaptive_threshold"],
    }, indent=2))
    print_metric_block("DeepLog baseline", result["summary"]["deeplog_metrics"])
    print_metric_block("Argument-aware report model", result["summary"]["report_metrics"])

    cross_host = workbench.evaluate_cross_host_proxy()
    print("\nCross-host proxy evaluation")
    print(cross_host["note"])
    print(json.dumps(cross_host["folds"], indent=2))


if __name__ == "__main__":
    main()
