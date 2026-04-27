from __future__ import annotations

import csv
import io
import json
import math
import statistics
import threading
import time
from collections import Counter, deque
from dataclasses import asdict, dataclass
from pathlib import Path
import sys
from typing import Any, Deque, Dict, Iterable, List, Optional, Sequence, Tuple

import torch
import torch.nn as nn

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from anomaly_detection import SequenceAnomalyModel

DATA_DIR = BASE_DIR / "data"
ARTIFACT_DIR = BASE_DIR / "artifacts"
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_WINDOW_SIZE = 10
DEFAULT_BASELINE_TOP_K = 5
DEFAULT_TRAIN_LIMIT = 1200
DEFAULT_ATTACK_LIMIT = 700
DRIFT_ALERT_THRESHOLD = 0.2
DEFAULT_REPORT_THRESHOLD = 0.5
ADAPT_BLEND = 0.35

# Remove attack_cat from feature inputs to prevent label leakage.
KEY_FIELDS = ("proto", "service", "state")
NUMERIC_FIELDS = (
    "dur",
    "spkts",
    "dpkts",
    "sbytes",
    "dbytes",
    "rate",
    "sttl",
    "dttl",
    "sload",
    "dload",
    "sloss",
    "dloss",
    "sinpkt",
    "dinpkt",
    "smean",
    "dmean",
    "ct_srv_src",
    "ct_state_ttl",
    "ct_dst_ltm",
    "ct_src_dport_ltm",
    "ct_dst_sport_ltm",
    "ct_dst_src_ltm",
    "ct_src_ltm",
    "ct_srv_dst",
    "is_sm_ips_ports",
)

DEFAULT_UPLOAD_TEXT = """id=1 dur=0.000011 proto=udp service=- state=INT spkts=2 dpkts=0 sbytes=496 dbytes=0 rate=90909.0902 sttl=254 dttl=0 sload=180363632.0 dload=0.0 sloss=0 dloss=0 sinpkt=0.011 dinpkt=0.0 smean=248 dmean=0 ct_srv_src=2 ct_state_ttl=2 ct_dst_ltm=1 ct_src_dport_ltm=1 ct_dst_sport_ltm=1 ct_dst_src_ltm=2 ct_src_ltm=1 ct_srv_dst=2 is_sm_ips_ports=0 attack_cat=Normal label=0
id=2 dur=0.000008 proto=udp service=- state=INT spkts=2 dpkts=0 sbytes=1762 dbytes=0 rate=125000.0003 sttl=254 dttl=0 sload=881000000.0 dload=0.0 sloss=0 dloss=0 sinpkt=0.008 dinpkt=0.0 smean=881 dmean=0 ct_srv_src=2 ct_state_ttl=2 ct_dst_ltm=1 ct_src_dport_ltm=1 ct_dst_sport_ltm=1 ct_dst_src_ltm=2 ct_src_ltm=1 ct_srv_dst=2 is_sm_ips_ports=0 attack_cat=Normal label=0
id=3 dur=0.000005 proto=udp service=- state=INT spkts=2 dpkts=0 sbytes=1068 dbytes=0 rate=200000.0051 sttl=254 dttl=0 sload=854400000.0 dload=0.0 sloss=0 dloss=0 sinpkt=0.005 dinpkt=0.0 smean=534 dmean=0 ct_srv_src=3 ct_state_ttl=2 ct_dst_ltm=1 ct_src_dport_ltm=1 ct_dst_sport_ltm=1 ct_dst_src_ltm=3 ct_src_ltm=1 ct_srv_dst=3 is_sm_ips_ports=0 attack_cat=Normal label=0
id=4 dur=0.000006 proto=udp service=- state=INT spkts=2 dpkts=0 sbytes=900 dbytes=0 rate=166666.6608 sttl=254 dttl=0 sload=600000000.0 dload=0.0 sloss=0 dloss=0 sinpkt=0.006 dinpkt=0.0 smean=450 dmean=0 ct_srv_src=3 ct_state_ttl=2 ct_dst_ltm=2 ct_src_dport_ltm=2 ct_dst_sport_ltm=1 ct_dst_src_ltm=3 ct_src_ltm=2 ct_srv_dst=3 is_sm_ips_ports=0 attack_cat=Normal label=0
id=5 dur=0.000010 proto=udp service=- state=INT spkts=2 dpkts=0 sbytes=2126 dbytes=0 rate=100000.0025 sttl=254 dttl=0 sload=850400000.0 dload=0.0 sloss=0 dloss=0 sinpkt=0.010 dinpkt=0.0 smean=1063 dmean=0 ct_srv_src=3 ct_state_ttl=2 ct_dst_ltm=2 ct_src_dport_ltm=2 ct_dst_sport_ltm=1 ct_dst_src_ltm=3 ct_src_ltm=2 ct_srv_dst=3 is_sm_ips_ports=0 attack_cat=Normal label=0
id=6 dur=0.043974 proto=tcp service=- state=FIN spkts=48 dpkts=50 sbytes=2958 dbytes=32368 rate=2205.848863 sttl=31 dttl=29 sload=527038.6875 dload=5770864.5 sloss=7 dloss=18 sinpkt=0.928745 dinpkt=0.885755 smean=62 dmean=647 ct_srv_src=6 ct_state_ttl=0 ct_dst_ltm=2 ct_src_dport_ltm=1 ct_dst_sport_ltm=1 ct_dst_src_ltm=1 ct_src_ltm=2 ct_srv_dst=8 is_sm_ips_ports=0 attack_cat=Normal label=0
id=7 dur=0.045134 proto=udp service=- state=CON spkts=4 dpkts=4 sbytes=512 dbytes=304 rate=155.093719 sttl=31 dttl=29 sload=68063.98438 dload=40412.99219 sloss=0 dloss=0 sinpkt=9.993333 dinpkt=10.683 smean=128 dmean=76 ct_srv_src=6 ct_state_ttl=0 ct_dst_ltm=3 ct_src_dport_ltm=1 ct_dst_sport_ltm=1 ct_dst_src_ltm=2 ct_src_ltm=5 ct_srv_dst=5 is_sm_ips_ports=0 attack_cat=Normal label=0
id=8 dur=0.012968 proto=tcp service=- state=FIN spkts=44 dpkts=46 sbytes=2766 dbytes=24004 rate=6863.047489 sttl=31 dttl=29 sload=1668106.125 dload=14486737.0 sloss=7 dloss=16 sinpkt=0.293535 dinpkt=0.277222 smean=63 dmean=522 ct_srv_src=11 ct_state_ttl=0 ct_dst_ltm=2 ct_src_dport_ltm=1 ct_dst_sport_ltm=1 ct_dst_src_ltm=1 ct_src_ltm=5 ct_srv_dst=6 is_sm_ips_ports=0 attack_cat=Normal label=0
id=9 dur=0.921987 proto=ospf service=- state=INT spkts=20 dpkts=0 sbytes=1280 dbytes=0 rate=20.607666 sttl=254 dttl=0 sload=10551.125 dload=0.0 sloss=0 dloss=0 sinpkt=48.525633 dinpkt=0.0 smean=64 dmean=0 ct_srv_src=1 ct_state_ttl=2 ct_dst_ltm=1 ct_src_dport_ltm=1 ct_dst_sport_ltm=1 ct_dst_src_ltm=2 ct_src_ltm=1 ct_srv_dst=1 is_sm_ips_ports=0 attack_cat=Reconnaissance label=1
id=10 dur=0.921987 proto=ospf service=- state=INT spkts=20 dpkts=0 sbytes=1280 dbytes=0 rate=20.607666 sttl=254 dttl=0 sload=10551.125 dload=0.0 sloss=0 dloss=0 sinpkt=48.525633 dinpkt=0.0 smean=64 dmean=0 ct_srv_src=1 ct_state_ttl=2 ct_dst_ltm=1 ct_src_dport_ltm=1 ct_dst_sport_ltm=1 ct_dst_src_ltm=2 ct_src_ltm=1 ct_srv_dst=1 is_sm_ips_ports=0 attack_cat=Reconnaissance label=1
id=11 dur=0.921987 proto=ospf service=- state=INT spkts=20 dpkts=0 sbytes=1280 dbytes=0 rate=20.607666 sttl=254 dttl=0 sload=10551.125 dload=0.0 sloss=0 dloss=0 sinpkt=48.525633 dinpkt=0.0 smean=64 dmean=0 ct_srv_src=1 ct_state_ttl=2 ct_dst_ltm=1 ct_src_dport_ltm=1 ct_dst_sport_ltm=1 ct_dst_src_ltm=2 ct_src_ltm=1 ct_srv_dst=1 is_sm_ips_ports=0 attack_cat=Backdoor label=1
id=12 dur=0.921987 proto=ospf service=- state=INT spkts=20 dpkts=0 sbytes=1280 dbytes=0 rate=20.607666 sttl=254 dttl=0 sload=10551.125 dload=0.0 sloss=0 dloss=0 sinpkt=48.525633 dinpkt=0.0 smean=64 dmean=0 ct_srv_src=1 ct_state_ttl=2 ct_dst_ltm=1 ct_src_dport_ltm=1 ct_dst_sport_ltm=1 ct_dst_src_ltm=2 ct_src_ltm=1 ct_srv_dst=1 is_sm_ips_ports=0 attack_cat=Backdoor label=1
"""


def _safe_float(value: Any) -> float:
    try:
        value = float(value)
        if math.isfinite(value):
            return value
    except Exception:
        pass
    return 0.0


def _split_tokens(line: str) -> List[str]:
    return [token for token in line.strip().split() if token]


def parse_log_line(line: str, line_number: int) -> Optional[Dict[str, Any]]:
    tokens = _split_tokens(line)
    if not tokens:
        return None

    record: Dict[str, Any] = {
        "line_number": line_number,
        "raw": line.strip(),
        "machine": "uploaded",
        "timestamp": float(line_number),
    }

    if any("=" in token for token in tokens):
        for token in tokens:
            if "=" in token:
                key, value = token.split("=", 1)
                record[key] = value
        event = "|".join(str(record.get(field, "-")) for field in ("proto", "service", "state"))
        record["event"] = event
        label = record.get("label")
        record["label"] = int(label) if label is not None and str(label).isdigit() else 0
    else:
        event = tokens[0]
        record["event"] = event
        record["proto"] = event
        record["service"] = tokens[1] if len(tokens) > 1 else "-"
        record["state"] = tokens[2] if len(tokens) > 2 else "-"
        record["attack_cat"] = "Unknown"
        record["label"] = 0

    for field in KEY_FIELDS:
        record.setdefault(field, "unknown")
    for field in NUMERIC_FIELDS:
        record[field] = _safe_float(record.get(field, 0.0))

    record.setdefault("attack_cat", "Normal" if record.get("label", 0) == 0 else "Attack")
    record["event"] = str(record["event"])
    record["host_group"] = derive_host_group(record)
    return record


def load_records_from_text(text: str) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        record = parse_log_line(line, line_number)
        if record is not None:
            records.append(record)
    return records


def load_records_from_file(path: Path, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8", errors="ignore") as infile:
        for line_number, line in enumerate(infile, start=1):
            record = parse_log_line(line, line_number)
            if record is None:
                continue
            records.append(record)
            if limit is not None and len(records) >= limit:
                break
    return records


def make_event_token(record: Dict[str, Any]) -> str:
    return f"{record.get('proto', 'unknown')}|{record.get('service', 'unknown')}|{record.get('state', 'unknown')}"


def derive_host_group(record: Dict[str, Any]) -> str:
    host = str(record.get("host", "")).strip()
    if host:
        return host
    machine = str(record.get("machine", "")).strip()
    if machine and machine != "uploaded":
        return machine
    ct_srv_src = int(_safe_float(record.get("ct_srv_src", 0)))
    if ct_srv_src > 0:
        return f"ct_srv_src:{ct_srv_src}"
    proto = str(record.get("proto", "unknown"))
    state = str(record.get("state", "unknown"))
    return f"fallback:{proto}:{state}"


def fit_scaler(records: Sequence[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    scaler: Dict[str, Dict[str, float]] = {}
    for field in NUMERIC_FIELDS:
        values = [_safe_float(record.get(field, 0.0)) for record in records]
        if values:
            mean = statistics.fmean(values)
            stdev = statistics.pstdev(values) or 1.0
        else:
            mean = 0.0
            stdev = 1.0
        scaler[field] = {"mean": mean, "std": stdev}
    return scaler


def scale_numeric_record(record: Dict[str, Any], scaler: Dict[str, Dict[str, float]]) -> List[float]:
    scaled: List[float] = []
    for field in NUMERIC_FIELDS:
        stats = scaler[field]
        value = _safe_float(record.get(field, 0.0))
        scaled.append((value - stats["mean"]) / stats["std"])
    return scaled


def build_sequence_tokens(records: Sequence[Dict[str, Any]]) -> List[str]:
    return [make_event_token(record) for record in records]


def build_windows(sequence: Sequence[Any], window_size: int) -> Tuple[List[List[Any]], List[Any]]:
    contexts: List[List[Any]] = []
    targets: List[Any] = []
    if len(sequence) <= window_size:
        return contexts, targets
    for index in range(window_size, len(sequence)):
        contexts.append(list(sequence[index - window_size:index]))
        targets.append(sequence[index])
    return contexts, targets


def binary_metrics(labels: Sequence[int], predictions: Sequence[int]) -> Dict[str, Optional[float]]:
    if not labels:
        return {
            "accuracy": None,
            "precision": None,
            "recall": None,
            "f1": None,
            "false_positive_rate": None,
            "tp": 0,
            "fp": 0,
            "tn": 0,
            "fn": 0,
        }
    tp = sum(1 for label, prediction in zip(labels, predictions) if label == 1 and prediction == 1)
    fp = sum(1 for label, prediction in zip(labels, predictions) if label == 0 and prediction == 1)
    tn = sum(1 for label, prediction in zip(labels, predictions) if label == 0 and prediction == 0)
    fn = sum(1 for label, prediction in zip(labels, predictions) if label == 1 and prediction == 0)
    accuracy = (tp + tn) / len(labels) if labels else None
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    false_positive_rate = fp / (fp + tn) if (fp + tn) else 0.0
    return {
        "accuracy": round(accuracy, 3) if accuracy is not None else None,
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
        "false_positive_rate": round(false_positive_rate, 3),
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
    }


def build_window_records(records: Sequence[Dict[str, Any]], window_size: int) -> List[Dict[str, Any]]:
    windows: List[Dict[str, Any]] = []
    if len(records) <= window_size:
        return windows
    for index in range(window_size, len(records)):
        context_records = list(records[index - window_size:index])
        current_record = dict(records[index])
        windows.append(
            {
                "index": index,
                "context_records": context_records,
                "current_record": current_record,
                "context_tokens": [make_event_token(item) for item in context_records],
                "target_token": make_event_token(current_record),
                "label": int(current_record.get("label", 0)),
                "attack_cat": str(current_record.get("attack_cat", "Unknown")),
            }
        )
    return windows


def encode_tokens(tokens: Sequence[str], vocabulary: Dict[str, int], unknown_token: str = "__UNK__") -> List[int]:
    unknown_index = vocabulary.get(unknown_token, 0)
    return [vocabulary.get(token, unknown_index) for token in tokens]


def build_feature_tensor(
    windows: Sequence[Dict[str, Any]],
    key_vocabularies: Dict[str, Dict[str, int]],
    scaler: Dict[str, Dict[str, float]],
) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    categorical: List[List[List[int]]] = []
    numeric: List[List[List[float]]] = []
    labels: List[int] = []

    for window in windows:
        cat_window: List[List[int]] = []
        num_window: List[List[float]] = []
        for record in window["context_records"]:
            cat_window.append(
                [
                    key_vocabularies[field].get(str(record.get(field, "unknown")), 0)
                    for field in KEY_FIELDS
                ]
            )
            num_window.append(scale_numeric_record(record, scaler))
        categorical.append(cat_window)
        numeric.append(num_window)
        labels.append(int(window["label"]))

    return (
        torch.tensor(categorical, dtype=torch.long),
        torch.tensor(numeric, dtype=torch.float32),
        torch.tensor(labels, dtype=torch.float32),
    )


def collect_key_vocabularies(records: Sequence[Dict[str, Any]]) -> Dict[str, Dict[str, int]]:
    vocabularies: Dict[str, Dict[str, int]] = {}
    for field in KEY_FIELDS:
        values = sorted({str(record.get(field, "unknown")) for record in records})
        vocabularies[field] = {"__UNK__": 0}
        vocabularies[field].update({value: index + 1 for index, value in enumerate(values)})
    return vocabularies


class ArgumentAwareNet(nn.Module):
    def __init__(
        self,
        key_vocab_sizes: Dict[str, int],
        numeric_dim: int,
        hidden_dim: int = 48,
        embedding_dim: int = 8,
    ) -> None:
        super().__init__()
        self.field_order = list(KEY_FIELDS)
        self.embeddings = nn.ModuleDict(
            {
                field: nn.Embedding(size, embedding_dim)
                for field, size in key_vocab_sizes.items()
            }
        )
        input_dim = len(self.field_order) * embedding_dim + numeric_dim
        self.gru = nn.GRU(input_dim, hidden_dim, batch_first=True)
        self.output = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1),
        )

    def forward(self, categorical: torch.Tensor, numeric: torch.Tensor) -> torch.Tensor:
        embedded_parts = []
        for field_index, field in enumerate(self.field_order):
            embedded_parts.append(self.embeddings[field](categorical[:, :, field_index]))
        embedded = torch.cat(embedded_parts, dim=-1)
        combined = torch.cat([embedded, numeric], dim=-1)
        output, _ = self.gru(combined)
        logits = self.output(output[:, -1, :]).squeeze(-1)
        return logits


@dataclass
class PredictionItem:
    index: int
    line_number: int
    event: str
    label: Optional[int]
    attack_cat: str
    host_group: str
    deeplog_prediction: int
    deeplog_score: float
    deeplog_top_matches: List[str]
    report_prediction: int
    report_score: float
    agreement: bool
    raw: str


class AnomalyWorkbench:
    def __init__(
        self,
        base_dir: Optional[Path] = None,
        window_size: int = DEFAULT_WINDOW_SIZE,
        baseline_top_k: int = DEFAULT_BASELINE_TOP_K,
    ) -> None:
        self.base_dir = Path(base_dir or BASE_DIR)
        self.data_dir = self.base_dir / "data"
        self.artifact_dir = self.base_dir / "artifacts"
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        self.window_size = window_size
        self.baseline_top_k = baseline_top_k
        self.device = torch.device("cpu")
        self._lock = threading.Lock()

        self.baseline_artifact_path = self.artifact_dir / "baseline_unsw.pt"
        self.baseline_meta_path = self.artifact_dir / "baseline_unsw.json"
        self.report_model_path = self.artifact_dir / "report_model.pt"
        self.report_meta_path = self.artifact_dir / "report_model.json"

        self.baseline_model: Optional[SequenceAnomalyModel] = None
        self.baseline_meta: Dict[str, Any] = {}
        self.report_model: Optional[ArgumentAwareNet] = None
        self.report_meta: Dict[str, Any] = {}
        self.adaptive_enabled = True
        self.report_threshold = DEFAULT_REPORT_THRESHOLD
        self.base_report_threshold = DEFAULT_REPORT_THRESHOLD
        self.last_adaptation: Dict[str, Any] = {
            "status": "idle",
            "threshold": self.report_threshold,
            "base_threshold": self.base_report_threshold,
            "updated_at": None,
            "reason": "Adaptive threshold not initialized yet.",
        }

    def ensure_ready(self) -> Dict[str, Any]:
        with self._lock:
            self._ensure_baseline_model()
            self._ensure_report_model()
        return {
            "window_size": self.window_size,
            "baseline_top_k": self.baseline_top_k,
            "baseline_ready": self.baseline_model is not None,
            "report_ready": self.report_model is not None,
            "artifacts_dir": str(self.artifact_dir),
            "adaptive_threshold_enabled": self.adaptive_enabled,
            "report_threshold": round(self.report_threshold, 4),
            "base_report_threshold": round(self.base_report_threshold, 4),
        }

    def _ensure_baseline_model(self) -> None:
        if self.baseline_model is not None:
            return
        if self.baseline_artifact_path.exists() and self.baseline_meta_path.exists():
            self.baseline_model = SequenceAnomalyModel.load(str(self.baseline_artifact_path), device=self.device).to(self.device)
            self.baseline_meta = json.loads(self.baseline_meta_path.read_text(encoding="utf-8"))
            return
        self._train_baseline_model()

    def _ensure_report_model(self) -> None:
        if self.report_model is not None:
            return
        if self.report_model_path.exists() and self.report_meta_path.exists():
            meta = json.loads(self.report_meta_path.read_text(encoding="utf-8"))
            model = ArgumentAwareNet(
                key_vocab_sizes=meta["key_vocab_sizes"],
                numeric_dim=len(NUMERIC_FIELDS),
                hidden_dim=meta["hidden_dim"],
                embedding_dim=meta["embedding_dim"],
            )
            state_dict = torch.load(self.report_model_path, map_location=self.device)
            try:
                model.load_state_dict(state_dict)
            except Exception:
                # Existing artifact no longer matches the current feature pipeline.
                self.report_model_path.unlink(missing_ok=True)
                self.report_meta_path.unlink(missing_ok=True)
                self._train_report_model()
                return
            model.eval()
            if "threshold" not in meta:
                train_normal, test_normal, test_attack = self._training_records()
                train_records = train_normal + test_normal[: DEFAULT_ATTACK_LIMIT // 2] + test_attack[: DEFAULT_ATTACK_LIMIT]
                windows = build_window_records(train_records, self.window_size)
                meta["threshold"] = self._calibrate_report_threshold(
                    model,
                    windows,
                    meta["key_vocabularies"],
                    meta["scaler"],
                )
                self.report_meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
            self.report_model = model.to(self.device)
            self.report_meta = meta
            self.base_report_threshold = float(meta.get("threshold", DEFAULT_REPORT_THRESHOLD))
            self.report_threshold = self.base_report_threshold
            self.last_adaptation = {
                "status": "ready",
                "threshold": round(self.report_threshold, 4),
                "base_threshold": round(self.base_report_threshold, 4),
                "updated_at": None,
                "reason": "Loaded stored threshold from artifact metadata.",
            }
            return
        self._train_report_model()

    def _training_records(self) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        train_normal = load_records_from_file(self.data_dir / "unsw_train.txt", limit=DEFAULT_TRAIN_LIMIT)
        test_normal = load_records_from_file(self.data_dir / "unsw_test_normal.txt", limit=DEFAULT_ATTACK_LIMIT)
        test_attack = load_records_from_file(self.data_dir / "unsw_test_attack.txt", limit=DEFAULT_ATTACK_LIMIT)
        return train_normal, test_normal, test_attack

    def _train_baseline_model(self) -> None:
        train_normal, _, _ = self._training_records()
        model, metadata = self._fit_baseline_model(train_normal)
        model.save(str(self.baseline_artifact_path))
        self.baseline_meta = metadata
        self.baseline_meta_path.write_text(json.dumps(self.baseline_meta, indent=2), encoding="utf-8")
        model.eval()
        self.baseline_model = model

    def _train_report_model(self) -> None:
        train_normal, test_normal, test_attack = self._training_records()
        train_records = train_normal + test_normal[: DEFAULT_ATTACK_LIMIT // 2] + test_attack[: DEFAULT_ATTACK_LIMIT]
        model, metadata = self._fit_report_model(train_records)
        torch.save(model.state_dict(), self.report_model_path)
        self.report_meta = metadata
        self.report_meta_path.write_text(json.dumps(self.report_meta, indent=2), encoding="utf-8")
        self.report_model = model
        self.base_report_threshold = float(metadata.get("threshold", DEFAULT_REPORT_THRESHOLD))
        self.report_threshold = self.base_report_threshold
        self.last_adaptation = {
            "status": "ready",
            "threshold": round(self.report_threshold, 4),
            "base_threshold": round(self.base_report_threshold, 4),
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "reason": "Calibrated threshold from training-time normal windows.",
        }

    def _fit_baseline_model(self, records: Sequence[Dict[str, Any]]) -> Tuple[SequenceAnomalyModel, Dict[str, Any]]:
        tokens = build_sequence_tokens(records)
        vocabulary = {"__UNK__": 0}
        vocabulary.update({token: index + 1 for index, token in enumerate(sorted(set(tokens)))})
        contexts, targets = build_windows(tokens, self.window_size)
        encoded_contexts = [encode_tokens(window, vocabulary) for window in contexts]
        encoded_targets = encode_tokens(targets, vocabulary)

        X = torch.tensor(encoded_contexts, dtype=torch.long)
        y = torch.tensor(encoded_targets, dtype=torch.long)

        model = SequenceAnomalyModel(
            input_size=len(vocabulary),
            hidden_size=64,
            output_size=len(vocabulary),
            num_layers=2,
        ).to(self.device)
        model.fit(
            X=X.to(self.device),
            y=y.to(self.device),
            epochs=2,
            batch_size=64,
            optimizer=torch.optim.Adam,
            verbose=False,
        )
        reverse_vocab = {index: token for token, index in vocabulary.items()}
        metadata = {
            "window_size": self.window_size,
            "baseline_top_k": self.baseline_top_k,
            "vocabulary": vocabulary,
            "reverse_vocabulary": reverse_vocab,
            "train_size": len(tokens),
        }
        model.eval()
        return model, metadata

    def _fit_report_model(self, train_records: Sequence[Dict[str, Any]]) -> Tuple[ArgumentAwareNet, Dict[str, Any]]:
        windows = build_window_records(train_records, self.window_size)
        key_vocabularies = collect_key_vocabularies(train_records)
        scaler = fit_scaler(train_records)
        categorical, numeric, labels = build_feature_tensor(windows, key_vocabularies, scaler)

        model = ArgumentAwareNet(
            key_vocab_sizes={field: len(vocabulary) for field, vocabulary in key_vocabularies.items()},
            numeric_dim=len(NUMERIC_FIELDS),
            hidden_dim=48,
            embedding_dim=8,
        ).to(self.device)
        optimizer = torch.optim.Adam(model.parameters(), lr=0.003)
        criterion = nn.BCEWithLogitsLoss()
        model.train()
        batch_size = 64
        for _ in range(4):
            for start in range(0, len(windows), batch_size):
                end = start + batch_size
                batch_cat = categorical[start:end].to(self.device)
                batch_num = numeric[start:end].to(self.device)
                batch_labels = labels[start:end].to(self.device)
                optimizer.zero_grad()
                logits = model(batch_cat, batch_num)
                loss = criterion(logits, batch_labels)
                loss.backward()
                optimizer.step()
        model.eval()
        metadata = {
            "window_size": self.window_size,
            "key_vocabularies": key_vocabularies,
            "key_vocab_sizes": {field: len(vocab) for field, vocab in key_vocabularies.items()},
            "scaler": scaler,
            "hidden_dim": 48,
            "embedding_dim": 8,
            "threshold": self._calibrate_report_threshold(model, windows, key_vocabularies, scaler),
        }
        return model, metadata

    def predict_records(self, records: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
        self.ensure_ready()
        windows = build_window_records(records, self.window_size)
        if not windows:
            return {
                "summary": {
                    "window_count": 0,
                    "deeplog_anomalies": 0,
                    "report_anomalies": 0,
                    "agreement_rate": 0.0,
                    "labeled_windows": 0,
                },
                "items": [],
                "charts": {"timeline": [], "comparison": [], "drift": []},
            }

        deeplog_results = self._predict_baseline(windows)
        report_scores = self._predict_report_scores(windows)
        preview_items: List[PredictionItem] = []
        for index, window in enumerate(windows):
            current_record = window["current_record"]
            deeplog_result = deeplog_results[index]
            preview_items.append(
                PredictionItem(
                    index=index,
                    line_number=int(current_record.get("line_number", index + self.window_size + 1)),
                    event=window["target_token"],
                    label=int(window["label"]) if "label" in window else None,
                    attack_cat=str(window["attack_cat"]),
                    host_group=str(current_record.get("host_group", "unknown")),
                    deeplog_prediction=deeplog_result["prediction"],
                    deeplog_score=deeplog_result["score"],
                    deeplog_top_matches=deeplog_result["top_matches"],
                    report_prediction=int(report_scores[index] >= self.report_threshold),
                    report_score=round(report_scores[index], 4),
                    agreement=False,
                    raw=str(current_record.get("raw", "")),
                )
            )
        preview_drift = self._compute_drift_summary(records, preview_items)
        self._maybe_adapt_threshold(windows, report_scores, preview_drift["summary"])
        report_results = self._finalize_report_predictions(report_scores)

        items: List[PredictionItem] = []
        for index, window in enumerate(windows):
            current_record = window["current_record"]
            deeplog_result = deeplog_results[index]
            report_result = report_results[index]
            items.append(
                PredictionItem(
                    index=index,
                    line_number=int(current_record.get("line_number", index + self.window_size + 1)),
                    event=window["target_token"],
                    label=int(window["label"]) if "label" in window else None,
                    attack_cat=str(window["attack_cat"]),
                    host_group=str(current_record.get("host_group", "unknown")),
                    deeplog_prediction=deeplog_result["prediction"],
                    deeplog_score=deeplog_result["score"],
                    deeplog_top_matches=deeplog_result["top_matches"],
                    report_prediction=report_result["prediction"],
                    report_score=report_result["score"],
                    agreement=deeplog_result["prediction"] == report_result["prediction"],
                    raw=str(current_record.get("raw", "")),
                )
            )

        timeline = [
            {
                "line_number": item.line_number,
                "deeplog": item.deeplog_score,
                "report": item.report_score,
                "label": item.label,
            }
            for item in items
        ]
        comparison = [
            {"label": "DeepLog anomalies", "value": sum(item.deeplog_prediction for item in items)},
            {"label": "Report model anomalies", "value": sum(item.report_prediction for item in items)},
            {"label": "Agreements", "value": sum(1 for item in items if item.agreement)},
        ]

        labeled_items = [item for item in items if item.label is not None]
        labeled_truth = [int(item.label) for item in labeled_items]
        deeplog_preds = [item.deeplog_prediction for item in labeled_items]
        report_preds = [item.report_prediction for item in labeled_items]
        deeplog_metrics = binary_metrics(labeled_truth, deeplog_preds)
        report_metrics = binary_metrics(labeled_truth, report_preds)
        drift = self._compute_drift_summary(records, items)
        agreement_rate = round(sum(1 for item in items if item.agreement) / len(items), 3)
        summary = {
            "window_count": len(items),
            "deeplog_anomalies": sum(item.deeplog_prediction for item in items),
            "report_anomalies": sum(item.report_prediction for item in items),
            "agreement_rate": agreement_rate,
            "labeled_windows": len(labeled_items),
            "normal_windows": sum(1 for item in labeled_items if item.label == 0),
            "attack_windows": sum(1 for item in labeled_items if item.label == 1),
            "distinct_host_groups": len({item.host_group for item in items}),
            "deep_vs_label_accuracy": deeplog_metrics["accuracy"],
            "report_vs_label_accuracy": report_metrics["accuracy"],
            "deeplog_metrics": deeplog_metrics,
            "report_metrics": report_metrics,
            "drift": drift["summary"],
            "adaptive_threshold": self.get_adaptive_status(),
        }

        return {
            "summary": summary,
            "items": [asdict(item) for item in items],
            "charts": {
                "timeline": timeline,
                "comparison": comparison,
                "drift": drift["chart"],
            },
        }

    def export_report_csv(self, result: Dict[str, Any]) -> str:
        output = io.StringIO()
        fieldnames = [
            "index",
            "line_number",
            "host_group",
            "event",
            "label",
            "attack_cat",
            "deeplog_prediction",
            "deeplog_score",
            "report_prediction",
            "report_score",
            "agreement",
            "raw",
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for item in result.get("items", []):
            writer.writerow({key: item.get(key) for key in fieldnames})
        return output.getvalue()

    def export_report_html(self, result: Dict[str, Any], title: str = "Anomaly Report") -> str:
        summary = result.get("summary", {})
        rows = []
        for item in result.get("items", [])[:200]:
            rows.append(
                "<tr>"
                f"<td>{item.get('line_number')}</td>"
                f"<td>{item.get('host_group', 'unknown')}</td>"
                f"<td><code>{item.get('event')}</code></td>"
                f"<td>{item.get('deeplog_prediction')}</td>"
                f"<td>{item.get('deeplog_score')}</td>"
                f"<td>{item.get('report_prediction')}</td>"
                f"<td>{item.get('report_score')}</td>"
                f"<td>{item.get('agreement')}</td>"
                f"<td>{item.get('label')}</td>"
                f"<td>{item.get('attack_cat')}</td>"
                "</tr>"
            )
        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{title}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; color: #1d2a22; }}
    h1 {{ margin-bottom: 8px; }}
    .summary {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 18px 0; }}
    .card {{ border: 1px solid #d9e1d2; border-radius: 12px; padding: 12px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    th, td {{ border-bottom: 1px solid #e8eee4; padding: 8px; text-align: left; vertical-align: top; }}
    code {{ white-space: pre-wrap; word-break: break-word; }}
  </style>
</head>
<body>
  <h1>{title}</h1>
  <p>Generated {time.strftime("%Y-%m-%d %H:%M:%S")}. This HTML report is printable to PDF from the browser.</p>
  <div class="summary">
    <div class="card"><strong>Windows</strong><br>{summary.get('window_count', 0)}</div>
    <div class="card"><strong>DeepLog anomalies</strong><br>{summary.get('deeplog_anomalies', 0)}</div>
    <div class="card"><strong>Report anomalies</strong><br>{summary.get('report_anomalies', 0)}</div>
    <div class="card"><strong>Agreement</strong><br>{summary.get('agreement_rate', 0)}</div>
  </div>
  <p><strong>Drift:</strong> {summary.get('drift', {}).get('status', 'n/a')} |
     score shift {summary.get('drift', {}).get('score_shift', 0)} |
     anomaly-rate shift {summary.get('drift', {}).get('anomaly_rate_shift', 0)} |
     protocol shift {summary.get('drift', {}).get('protocol_shift', 0)}</p>
  <table>
    <thead>
      <tr>
        <th>Line</th><th>Host Group</th><th>Event</th><th>DeepLog</th><th>Deep Score</th>
        <th>Report</th><th>Report Score</th><th>Agree</th><th>Truth</th><th>Attack Cat</th>
      </tr>
    </thead>
    <tbody>
      {''.join(rows)}
    </tbody>
  </table>
</body>
</html>"""

    def evaluate_cross_host_proxy(self, max_groups: int = 4, min_group_size: int = 80) -> Dict[str, Any]:
        train_normal, test_normal, test_attack = self._training_records()
        records = train_normal + test_normal + test_attack
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for record in records:
            grouped.setdefault(str(record.get("host_group", "unknown")), []).append(record)
        eligible_groups = [
            (group, group_records)
            for group, group_records in sorted(grouped.items(), key=lambda item: len(item[1]), reverse=True)
            if len(group_records) >= min_group_size
        ][:max_groups]
        folds: List[Dict[str, Any]] = []
        for group_name, test_records in eligible_groups:
            train_records = [record for record in records if str(record.get("host_group", "unknown")) != group_name]
            if len(train_records) <= self.window_size or len(test_records) <= self.window_size:
                continue
            deeplog_model, deeplog_meta = self._fit_baseline_model(train_records)
            report_model, report_meta = self._fit_report_model(train_records)
            deeplog_backup_model, deeplog_backup_meta = self.baseline_model, self.baseline_meta
            report_backup_model, report_backup_meta = self.report_model, self.report_meta
            try:
                self.baseline_model, self.baseline_meta = deeplog_model, deeplog_meta
                self.report_model, self.report_meta = report_model, report_meta
                result = self.predict_records(test_records)
            finally:
                self.baseline_model, self.baseline_meta = deeplog_backup_model, deeplog_backup_meta
                self.report_model, self.report_meta = report_backup_model, report_backup_meta
            summary = result["summary"]
            folds.append(
                {
                    "host_group": group_name,
                    "record_count": len(test_records),
                    "window_count": summary["window_count"],
                    "deeplog_accuracy": summary.get("deep_vs_label_accuracy"),
                    "report_accuracy": summary.get("report_vs_label_accuracy"),
                    "deeplog_anomalies": summary.get("deeplog_anomalies"),
                    "report_anomalies": summary.get("report_anomalies"),
                    "agreement_rate": summary.get("agreement_rate"),
                }
            )
        return {
            "note": "UNSW does not include explicit host ids here, so host groups are proxied with ct_srv_src-derived groups.",
            "folds": folds,
        }

    def set_adaptive_thresholding(self, enabled: bool) -> Dict[str, Any]:
        self.adaptive_enabled = bool(enabled)
        if not self.adaptive_enabled:
            self.report_threshold = self.base_report_threshold
        self.last_adaptation = {
            "status": "enabled" if self.adaptive_enabled else "disabled",
            "threshold": round(self.report_threshold, 4),
            "base_threshold": round(self.base_report_threshold, 4),
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "reason": "Adaptive thresholding enabled." if self.adaptive_enabled else "Adaptive thresholding disabled; reverted to the base threshold.",
        }
        return self.get_adaptive_status()

    def get_adaptive_status(self) -> Dict[str, Any]:
        return {
            "enabled": self.adaptive_enabled,
            "threshold": round(self.report_threshold, 4),
            "base_threshold": round(self.base_report_threshold, 4),
            "status": self.last_adaptation.get("status"),
            "updated_at": self.last_adaptation.get("updated_at"),
            "reason": self.last_adaptation.get("reason"),
        }

    def _compute_drift_summary(
        self,
        records: Sequence[Dict[str, Any]],
        items: Sequence[PredictionItem],
    ) -> Dict[str, Any]:
        if len(records) < 20 or len(items) < 6:
            return {
                "summary": {
                    "status": "insufficient_data",
                    "message": "Need more events before drift can be estimated.",
                    "score_shift": 0.0,
                    "anomaly_rate_shift": 0.0,
                    "protocol_shift": 0.0,
                },
                "chart": [],
            }

        midpoint_records = len(records) // 2
        baseline_records = records[:midpoint_records]
        recent_records = records[midpoint_records:]

        baseline_items = list(items[: max(1, len(items) // 2)])
        recent_items = list(items[max(1, len(items) // 2):])

        baseline_protocols = Counter(str(record.get("proto", "unknown")) for record in baseline_records)
        recent_protocols = Counter(str(record.get("proto", "unknown")) for record in recent_records)
        protocol_shift = self._distribution_shift(baseline_protocols, recent_protocols)

        baseline_score = statistics.fmean(item.report_score for item in baseline_items) if baseline_items else 0.0
        recent_score = statistics.fmean(item.report_score for item in recent_items) if recent_items else 0.0
        score_shift = round(recent_score - baseline_score, 3)

        baseline_rate = sum(item.report_prediction for item in baseline_items) / len(baseline_items) if baseline_items else 0.0
        recent_rate = sum(item.report_prediction for item in recent_items) / len(recent_items) if recent_items else 0.0
        anomaly_rate_shift = round(recent_rate - baseline_rate, 3)

        drift_intensity = max(abs(score_shift), abs(anomaly_rate_shift), protocol_shift)
        status = "stable" if drift_intensity < DRIFT_ALERT_THRESHOLD else "watch"
        if drift_intensity >= DRIFT_ALERT_THRESHOLD * 2:
            status = "drifting"

        return {
            "summary": {
                "status": status,
                "message": "Recent activity is compared against the first half of the stream.",
                "score_shift": score_shift,
                "anomaly_rate_shift": anomaly_rate_shift,
                "protocol_shift": round(protocol_shift, 3),
            },
            "chart": [
                {"label": "Baseline score", "value": round(baseline_score, 3)},
                {"label": "Recent score", "value": round(recent_score, 3)},
                {"label": "Baseline anomaly rate", "value": round(baseline_rate, 3)},
                {"label": "Recent anomaly rate", "value": round(recent_rate, 3)},
                {"label": "Protocol shift", "value": round(protocol_shift, 3)},
            ],
        }

    def _calibrate_report_threshold(
        self,
        model: ArgumentAwareNet,
        windows: Sequence[Dict[str, Any]],
        key_vocabularies: Dict[str, Dict[str, int]],
        scaler: Dict[str, Dict[str, float]],
    ) -> float:
        if not windows:
            return DEFAULT_REPORT_THRESHOLD
        categorical, numeric, labels = build_feature_tensor(windows, key_vocabularies, scaler)
        with torch.no_grad():
            logits = model(categorical.to(self.device), numeric.to(self.device))
            probabilities = torch.sigmoid(logits).detach().cpu().tolist()
        normal_scores = [float(score) for score, label in zip(probabilities, labels.tolist()) if int(label) == 0]
        if not normal_scores:
            return DEFAULT_REPORT_THRESHOLD
        sorted_scores = sorted(normal_scores)
        index = min(len(sorted_scores) - 1, max(0, int(0.95 * (len(sorted_scores) - 1))))
        return round(max(DEFAULT_REPORT_THRESHOLD, sorted_scores[index]), 4)

    def _predict_report_scores(self, windows: Sequence[Dict[str, Any]]) -> List[float]:
        assert self.report_model is not None
        categorical, numeric, _ = build_feature_tensor(
            windows,
            self.report_meta["key_vocabularies"],
            self.report_meta["scaler"],
        )
        with torch.no_grad():
            logits = self.report_model(
                categorical.to(self.device),
                numeric.to(self.device),
            )
            probabilities = torch.sigmoid(logits).detach().cpu().tolist()
        return [float(probability) for probability in probabilities]

    def _finalize_report_predictions(self, probabilities: Sequence[float]) -> List[Dict[str, Any]]:
        return [
            {
                "prediction": int(probability >= self.report_threshold),
                "score": round(float(probability), 4),
                "threshold": round(self.report_threshold, 4),
            }
            for probability in probabilities
        ]

    def _maybe_adapt_threshold(
        self,
        windows: Sequence[Dict[str, Any]],
        report_scores: Sequence[float],
        drift_summary: Dict[str, Any],
    ) -> None:
        if not self.adaptive_enabled:
            self.report_threshold = self.base_report_threshold
            return
        if len(windows) < 12:
            return
        drift_status = drift_summary.get("status")
        if drift_status not in {"watch", "drifting"}:
            self.last_adaptation = {
                "status": "stable",
                "threshold": round(self.report_threshold, 4),
                "base_threshold": round(self.base_report_threshold, 4),
                "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "reason": "Drift monitor is stable; threshold unchanged.",
            }
            return
        recent_count = max(8, len(windows) // 3)
        recent_windows = list(windows[-recent_count:])
        recent_scores = list(report_scores[-recent_count:])
        low_risk_scores = [
            score
            for score, window in zip(recent_scores, recent_windows)
            if int(window.get("label", 0)) == 0 or score < self.report_threshold
        ]
        if len(low_risk_scores) < 5:
            self.last_adaptation = {
                "status": "watching",
                "threshold": round(self.report_threshold, 4),
                "base_threshold": round(self.base_report_threshold, 4),
                "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "reason": "Drift detected, but there were not enough low-risk recent windows for recalibration.",
            }
            return
        sorted_scores = sorted(low_risk_scores)
        index = min(len(sorted_scores) - 1, max(0, int(0.9 * (len(sorted_scores) - 1))))
        candidate = max(self.base_report_threshold * 0.85, min(0.99, sorted_scores[index]))
        self.report_threshold = round(((1 - ADAPT_BLEND) * self.report_threshold) + (ADAPT_BLEND * candidate), 4)
        self.last_adaptation = {
            "status": "adapted",
            "threshold": round(self.report_threshold, 4),
            "base_threshold": round(self.base_report_threshold, 4),
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "reason": f"Threshold recalibrated from {len(low_risk_scores)} low-risk recent windows during {drift_status} drift.",
        }

    def _predict_baseline(self, windows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
        assert self.baseline_model is not None
        vocabulary = self.baseline_meta["vocabulary"]
        reverse_vocabulary = {int(key): value for key, value in self.baseline_meta["reverse_vocabulary"].items()}
        contexts = [encode_tokens(window["context_tokens"], vocabulary) for window in windows]
        targets = encode_tokens([window["target_token"] for window in windows], vocabulary)

        X = torch.tensor(contexts, dtype=torch.long).to(self.device)
        y = torch.tensor(targets, dtype=torch.long).to(self.device)
        predictions, confidence, anomaly_labels = self.baseline_model.predict_with_anomaly(
            X=X,
            y=y,
            k=self.baseline_top_k,
            verbose=False,
        )

        results: List[Dict[str, Any]] = []
        for index in range(len(windows)):
            top_ids = predictions[index].detach().cpu().tolist()
            confidences = confidence[index].detach().cpu().tolist()
            score = 1.0 - float(max(confidences)) if confidences else 0.0
            results.append(
                {
                    "prediction": int(anomaly_labels[index].detach().cpu().item()),
                    "score": round(score, 4),
                    "top_matches": [reverse_vocabulary.get(token_id, "__UNK__") for token_id in top_ids],
                }
            )
        return results

    @staticmethod
    def _accuracy(labels: Sequence[Optional[int]], predictions: Sequence[int]) -> Optional[float]:
        pairs = [(label, prediction) for label, prediction in zip(labels, predictions) if label is not None]
        if not pairs:
            return None
        correct = sum(1 for label, prediction in pairs if int(label) == int(prediction))
        return round(correct / len(pairs), 3)

    @staticmethod
    def _distribution_shift(left: Counter, right: Counter) -> float:
        keys = set(left) | set(right)
        left_total = sum(left.values()) or 1
        right_total = sum(right.values()) or 1
        return 0.5 * sum(
            abs((left.get(key, 0) / left_total) - (right.get(key, 0) / right_total))
            for key in keys
        )


class LiveMonitor:
    def __init__(self, workbench: AnomalyWorkbench) -> None:
        self.workbench = workbench
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._path: Optional[Path] = None
        self._results: Dict[str, Any] = {
            "status": "idle",
            "path": None,
            "updated_at": None,
            "result": None,
        }
        self._history: Deque[Dict[str, Any]] = deque(maxlen=20)

    def start(self, path: str) -> Dict[str, Any]:
        file_path = Path(path).expanduser().resolve()
        self.stop()
        self._stop.clear()
        self._path = file_path
        self._results["status"] = "starting"
        self._results["path"] = str(file_path)
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return self.status()

    def stop(self) -> Dict[str, Any]:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._thread = None
        self._results["status"] = "idle"
        return self.status()

    def status(self) -> Dict[str, Any]:
        return {
            "status": self._results["status"],
            "path": self._results["path"],
            "updated_at": self._results["updated_at"],
            "history": list(self._history),
            "result": self._results["result"],
        }

    def _run(self) -> None:
        assert self._path is not None
        seen_lines = 0
        self._results["status"] = "running"
        while not self._stop.is_set():
            if self._path.exists():
                text = self._path.read_text(encoding="utf-8", errors="ignore")
                records = load_records_from_text(text)
                if len(records) > seen_lines:
                    result = self.workbench.predict_records(records)
                    summary = result["summary"]
                    snapshot = {
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "line_count": len(records),
                        "deeplog_anomalies": summary["deeplog_anomalies"],
                        "report_anomalies": summary["report_anomalies"],
                        "agreement_rate": summary["agreement_rate"],
                    }
                    self._history.appendleft(snapshot)
                    self._results["updated_at"] = snapshot["timestamp"]
                    self._results["result"] = result
                    seen_lines = len(records)
            time.sleep(2.0)


# Backwards-compatible alias for older imports.
DeepLogReportWorkbench = AnomalyWorkbench
