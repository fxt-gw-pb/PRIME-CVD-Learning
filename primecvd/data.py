"""原始数据读取与模式校验；原始文件只读。"""
from __future__ import annotations
from pathlib import Path
import json
import numpy as np
import pandas as pd
from .common import data_dir, sha256

CLEAN_NAME = "asset1.csv"
EMR_FILES = {
    "master": "Data002_PatientEMR_MasterSummary_RE.csv",
    "diseases": "Data002_PatientEMR_ChronicDiseases_RE.csv",
    "measurements": "Data002_PatientEMR_MeasAndPath_RE.csv",
}
REQUIRED = ["IRSD_quintile", "Age", "smoking_status", "BMI", "diabetes", "CKD",
            "HbA1c", "eGFR", "SBP", "AF", "cvd_event", "cvd_time"]
NUMERIC = ["Age", "BMI", "HbA1c", "eGFR", "SBP"]
BINARY = ["diabetes", "CKD", "AF", "cvd_event"]


def patient_id_from_source_row(rows) -> np.ndarray:
    """作者公开映射 (row_index**2 - 77)*3+500，仅适用于该版本模拟数据。"""
    a = np.asarray(rows)
    if np.any(a < 0) or np.any(a != np.floor(a)):
        raise ValueError("源文件行索引必须为非负整数。")
    if np.any(a > 1_000_000_000): raise ValueError("行索引过大。")
    return a.astype(np.int64) ** 2 * 3 + 269


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"缺少 {path}\n官方数据：python run.py download\n离线演示：python run.py --config configs/demo.json demo\n不会用演示数据冒充官方数据。")
    return pd.read_csv(path)


def load_clean(cfg: dict) -> pd.DataFrame:
    df = read_csv(data_dir(cfg) / CLEAN_NAME)
    # 先保留导出的原始行索引，再处理多余CSV索引列，不能在随机打乱后重新编号。
    if "Unnamed: 0" in df:
        original = pd.to_numeric(df["Unnamed: 0"], errors="raise").to_numpy()
        if not np.array_equal(original, np.arange(len(df))):
            raise ValueError("源CSV索引不再是0..N-1，禁止猜测患者映射。请核对文件版本。")
        df = df.drop(columns=["Unnamed: 0"])
    missing = set(REQUIRED) - set(df)
    if missing: raise ValueError(f"Asset1 缺少字段：{sorted(missing)}")
    # 源字典禁止出现额外目标派生列；保留规定字段，派生标识不作为预测变量。
    df = df[REQUIRED].copy()
    for col in NUMERIC + BINARY + ["IRSD_quintile", "cvd_time"]:
        df[col] = pd.to_numeric(df[col], errors="raise")
    df["source_row_index"] = np.arange(len(df), dtype=np.int64)
    df["Patient_ID"] = patient_id_from_source_row(df["source_row_index"])
    validate_clean(df)
    return df


def validate_clean(df: pd.DataFrame) -> None:
    missing = set(REQUIRED) - set(df)
    if missing: raise ValueError(f"缺少字段：{missing}")
    if len(df) < 2: raise ValueError("队列不足两行。")
    for c in BINARY:
        if df[c].isna().any() or not df[c].isin([0, 1]).all():
            raise ValueError(f"{c} 必须是非缺失的0/1。")
    if not np.isfinite(df["cvd_time"]).all() or not (df["cvd_time"] > 0).all():
        raise ValueError("cvd_time 必须为有限的正数（年）。")
    if df[NUMERIC].isna().any().any() or not np.isfinite(df[NUMERIC].to_numpy()).all():
        raise ValueError("此版本 Asset1 的连续字段应为完整有限数值；出现缺失请先审查来源。")
    if not df["IRSD_quintile"].isin([1, 2, 3, 4, 5]).all():
        raise ValueError("IRSD 必须为1..5。")
    if not df["smoking_status"].isin(["non", "ex", "current"]).all():
        raise ValueError("Asset1 吸烟字段编码不符合词典。")
    if "Patient_ID" in df and df["Patient_ID"].duplicated().any():
        raise ValueError("患者标识重复。")


def load_emr(cfg: dict) -> dict[str, pd.DataFrame]:
    if cfg["mode"] == "official":
        folder = data_dir(cfg)
        manifest_path = folder / "manifest.json"
        if not manifest_path.exists():
            raise RuntimeError("官方EMR来源manifest缺失，请先运行download。")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        expected_hashes = manifest.get("extracted_sha256", {})
        if manifest.get("status") != "downloaded":
            raise RuntimeError("官方EMR下载记录尚未完整。")
        for name in EMR_FILES.values():
            path = folder / name
            if not path.exists() or expected_hashes.get(name) != sha256(path):
                raise RuntimeError(f"官方EMR文件的本地完整性核验失败：{name}")
    tables = {}
    for key, filename in EMR_FILES.items():
        d = read_csv(data_dir(cfg) / filename)
        d = d.drop(columns=[c for c in d if c.startswith("Unnamed:")])
        if "Patient_ID" not in d: raise ValueError(f"{filename} 缺少 Patient_ID")
        vals = pd.to_numeric(d["Patient_ID"], errors="raise")
        if vals.isna().any() or (vals % 1 != 0).any(): raise ValueError("Patient_ID 非完整整数")
        d["Patient_ID"] = vals.astype("int64")
        tables[key] = d
    master = tables["master"]
    if master["Patient_ID"].duplicated().any(): raise ValueError("患者主表一人多行：先排查，不能默默去重。")
    for k in ("diseases", "measurements"):
        if not tables[k]["Patient_ID"].isin(master["Patient_ID"]).all():
            raise ValueError(f"{k} 存在无法连接主表的孤立患者标识。")
    return tables


def audit_clean(df: pd.DataFrame, horizon: float = 5.0) -> dict:
    validate_clean(df)
    return {"n": len(df), "fields": REQUIRED,
            "observed_events": int(df.cvd_event.sum()),
            "observed_event_fraction_not_5y_risk": float(df.cvd_event.mean()),
            "early_censored_before_horizon": int(((df.cvd_event == 0) & (df.cvd_time < horizon)).sum()),
            "followup_min": float(df.cvd_time.min()), "followup_max": float(df.cvd_time.max()),
            "at_risk_after_horizon": int((df.cvd_time > horizon).sum()),
            "missing_by_field": df[REQUIRED].isna().sum().to_dict()}
