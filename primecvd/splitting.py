"""分层患者级划分；所有变换仅在训练部分拟合。"""
from __future__ import annotations
import pandas as pd
from sklearn.model_selection import train_test_split


def create_splits(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    if df.Patient_ID.duplicated().any(): raise ValueError("必须先聚合为一人一行。")
    if df.cvd_event.value_counts().min() < 6: raise ValueError("事件或非事件太少，不能稳定三段分层划分。")
    n_train = round(len(df) * cfg["train_fraction"])
    n_valid = round(len(df) * cfg["valid_fraction"])
    train, rest = train_test_split(df.Patient_ID, train_size=n_train,
                                  stratify=df.cvd_event, random_state=cfg["seed"])
    d = df.set_index("Patient_ID")
    valid, test = train_test_split(rest, train_size=n_valid,
                                  stratify=d.loc[rest, "cvd_event"], random_state=cfg["seed"] + 1)
    out = pd.concat([pd.DataFrame({"Patient_ID": ids, "split": label})
                     for ids, label in ((train, "train"), (valid, "valid"), (test, "test"))], ignore_index=True)
    out = out.sort_values("Patient_ID").reset_index(drop=True)
    validate_splits(out, df)
    return out


def validate_splits(splits: pd.DataFrame, df: pd.DataFrame) -> None:
    if splits.Patient_ID.duplicated().any(): raise ValueError("划分重叠：同一患者出现多次。")
    if set(splits.Patient_ID) != set(df.Patient_ID): raise ValueError("划分患者集合与数据不一致。")
    if set(splits.split) != {"train", "valid", "test"}: raise ValueError("划分标签必须完整为train/valid/test。")


def select_split(df: pd.DataFrame, splits: pd.DataFrame, which: str) -> pd.DataFrame:
    if which not in {"train", "valid", "test"}: raise ValueError(which)
    return df[df.Patient_ID.isin(splits.loc[splits.split == which, "Patient_ID"])].copy().reset_index(drop=True)
