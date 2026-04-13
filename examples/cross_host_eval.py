from __future__ import annotations

import json
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from workbench import AnomalyWorkbench


def main() -> None:
    workbench = AnomalyWorkbench(BASE_DIR)
    workbench.ensure_ready()
    result = workbench.evaluate_cross_host_proxy()
    print("Cross-host proxy evaluation")
    print(result["note"])
    print(json.dumps(result["folds"], indent=2))


if __name__ == "__main__":
    main()
