"""配置、来源标识与可复现性工具。"""
from __future__ import annotations
from pathlib import Path
from typing import Any
import hashlib
import importlib.metadata
import json
import platform

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    def clean(obj):
        import numpy as np
        if isinstance(obj, dict): return {str(k): clean(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)): return [clean(v) for v in obj]
        if isinstance(obj, np.ndarray): return clean(obj.tolist())
        if isinstance(obj, (float, np.floating)):
            return float(obj) if np.isfinite(obj) else None
        if isinstance(obj, np.integer): return int(obj)
        if isinstance(obj, np.bool_): return bool(obj)
        if isinstance(obj, Path): return str(obj)
        return obj
    path.write_text(json.dumps(clean(data), ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def load_config(path: str | Path = "configs/official.json") -> dict:
    p = Path(path)
    if not p.is_absolute(): p = ROOT / p
    cfg = json.loads(p.read_text(encoding="utf-8"))
    if cfg["mode"] not in ("official", "demo"):
        raise ValueError("mode 必须显式指定为 official 或 demo；不会自动替换数据。")
    if cfg["horizon_years"] <= 0: raise ValueError("预测时间必须大于零。")
    if cfg["cv_folds"] < 2: raise ValueError("交叉验证至少两折。")
    if not 0 < cfg["train_fraction"] < 1 or not 0 < cfg["valid_fraction"] < 1 - cfg["train_fraction"]:
        raise ValueError("训练、验证、测试比例不合法。")
    cfg["_config_path"] = str(p)
    return cfg


def config_hash(cfg: dict) -> str:
    raw = {k: v for k, v in cfg.items() if not k.startswith("_")}
    return hashlib.sha256(json.dumps(raw, sort_keys=True).encode()).hexdigest()


def data_dir(cfg: dict) -> Path:
    return ROOT / "data" / ("raw" if cfg["mode"] == "official" else "demo")


def output_dir(cfg: dict) -> Path:
    p = ROOT / cfg.get("output_dir", f"outputs/{cfg['mode']}")
    for sub in ("tables", "figures", "models", "logs"):
        (p / sub).mkdir(parents=True, exist_ok=True)
    return p


def provenance_label(cfg: dict) -> str:
    return ("OFFICIAL SOURCE FILES / 官方下载文件" if cfg["mode"] == "official"
            else "DEMO FIXTURE — NOT PRIME-CVD / 工程演示数据，不是官方 PRIME-CVD")


def environment() -> dict:
    packages = ["numpy", "pandas", "scipy", "scikit-learn", "statsmodels", "matplotlib", "requests", "pytest", "nbformat", "nbclient"]
    result = {"python": platform.python_version(), "platform": platform.platform()}
    for p in packages:
        try: result[p] = importlib.metadata.version(p)
        except importlib.metadata.PackageNotFoundError: result[p] = "not installed"
    return result
