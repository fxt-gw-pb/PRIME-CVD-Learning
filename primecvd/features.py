"""可审查的训练集编码器：固定参考组，医学单位缩放，再进行训练集标准化。"""
from __future__ import annotations
import numpy as np
import pandas as pd

UNITS = {"Age": 10.0, "BMI": 5.0, "SBP": 10.0, "eGFR": 10.0, "HbA1c": 1.0}
ALLOWED = set(UNITS) | {"diabetes", "CKD", "AF", "IRSD_quintile", "smoking_status"}


class FeatureEncoder:
    def __init__(self, features):
        self.features = list(features)
        extra = set(self.features) - ALLOWED
        if extra: raise ValueError(f"禁止用患者标识、结局或未知字段作预测变量：{extra}")
        self.state = None

    def _raw(self, df, medians):
        out = {}
        for c in self.features:
            if c not in df: raise ValueError(f"缺少预先规定的预测变量：{c}")
            if c in UNITS:
                s = pd.to_numeric(df[c], errors="raise").fillna(medians[c])
                out[f"{c}_per{UNITS[c]:g}"] = s.to_numpy(float) / UNITS[c]
            elif c == "IRSD_quintile":
                s = pd.to_numeric(df[c], errors="raise")
                if not s.isin([1, 2, 3, 4, 5]).all(): raise ValueError("IRSD未知值，不能静默编码成参考组。")
                for q in (1, 2, 3, 4): out[f"IRSD_{q}_vs5"] = (s == q).to_numpy(float)
            elif c == "smoking_status":
                s = df[c].fillna("unknown")
                if not s.isin(["non", "ex", "current", "unknown"]).all(): raise ValueError("吸烟编码未知。")
                for v in ("ex", "current", "unknown"):
                    out[f"smoking_{v}_vs_non"] = (s == v).to_numpy(float)
            else:
                if not df[c].isin([0, 1]).all(): raise ValueError(f"{c} 应为完整0/1。")
                out[c] = df[c].to_numpy(float)
        return pd.DataFrame(out, index=df.index)

    def fit(self, df):
        meds = {c: float(pd.to_numeric(df[c]).median()) for c in self.features if c in UNITS}
        if not all(np.isfinite(list(meds.values()))): raise ValueError("有变量在训练集完全缺失。")
        raw = self._raw(df, meds)
        keep = [c for c in raw if raw[c].std(ddof=0) > 1e-12]
        dropped = [c for c in raw if c not in keep]
        self.state = {"features": self.features, "medians": meds, "columns": keep,
                      "dropped_constant_columns": dropped,
                      "constant_values": raw[dropped].iloc[0].to_dict(),
                      "means": raw[keep].mean().to_dict(),
                      "scales": raw[keep].std(ddof=0).to_dict()}
        return self

    def transform(self, df):
        if self.state is None: raise RuntimeError("先在训练数据上fit。")
        raw = self._raw(df, self.state["medians"])
        # 训练时从未出现的类别，不允许在验证/测试时悄悄当成参考组。
        for c in self.state["dropped_constant_columns"]:
            if not np.allclose(raw[c], self.state["constant_values"][c]):
                raise ValueError(f"训练集恒定字段 {c} 在新数据变化；此模型不支持该类别/亚群。")
        keep = self.state["columns"]
        a = (raw[keep] - pd.Series(self.state["means"])) / pd.Series(self.state["scales"])
        if not np.isfinite(a.to_numpy()).all(): raise ValueError("变换后含非有限值。")
        return a

    @classmethod
    def from_state(cls, state):
        obj = cls(state["features"]); obj.state = state; return obj
