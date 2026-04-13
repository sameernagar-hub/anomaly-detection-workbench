from __future__ import annotations

import json
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from workbench import AnomalyWorkbench


def main() -> None:
    workbench = AnomalyWorkbench()
    details = workbench.ensure_ready()
    print("Artifacts ready:")
    print(json.dumps(details, indent=2))


if __name__ == "__main__":
    main()
