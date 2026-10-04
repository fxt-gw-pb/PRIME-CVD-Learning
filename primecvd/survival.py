"""Cox与纯L2惩罚Cox。部分似然及梯度调用statsmodels，优化调用SciPy。
保存可读JSON而非不可信pickle；Breslow基线使用事件时刻的右连续跳跃。
"""
from __future__ import annotations
from pathlib import Path
import json
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import norm
from statsmodels.duration.hazard_regression import PHReg
from .features import FeatureEncoder
from .metrics import validate_outcome
from .common import write_json


class CoxModel:
    def __init__(self, features, alpha=0.0):
        if alpha<0: raise ValueError("alpha不能为负。")
        self.features=list(features); self.alpha=float(alpha)
        self.encoder=FeatureEncoder(features)

    def fit(self, df):
        t,e=validate_outcome(df.cvd_time,df.cvd_event)
        X=self.encoder.fit(df).transform(df).to_numpy()
        if e.sum()<max(10, X.shape[1]+1): raise ValueError("事件数不足以稳定拟合本教学模型。")
        ph=PHReg(t,X,status=e,ties="breslow",missing="raise")
        n=len(t)
        def objective(b): return -ph.loglike(b)/n + self.alpha*np.dot(b,b)/2
        def gradient(b): return -ph.score(b)/n + self.alpha*b
        result=minimize(objective,np.zeros(X.shape[1]),jac=gradient,method="BFGS",
                        options={"maxiter":250,"gtol":1e-7})
        maxgrad=float(np.max(np.abs(gradient(result.x))))
        if not np.isfinite(result.x).all() or maxgrad>1e-5:
            raise RuntimeError(f"Cox未收敛：{result.message}，最大梯度={maxgrad:.3g}")
        self.beta=np.asarray(result.x)
        self.diagnostics={"optimizer_success":bool(result.success),"message":str(result.message),
                          "iterations":int(result.nit),"max_abs_gradient":maxgrad,
                          "n":n,"events":int(e.sum()),"objective":float(result.fun)}
        self.cov=None
        if self.alpha==0:
            self.cov=np.linalg.inv(-ph.hessian(self.beta))
        self.training_max_time=float(t.max())
        self._fit_baseline(t,e,X@self.beta)
        return self

    def _fit_baseline(self,t,e,eta):
        self.eta_center=float(np.mean(eta))
        order=np.argsort(t); ts=t[order]; es=e[order]
        exp_eta=np.exp(eta[order]-self.eta_center)
        if not np.isfinite(exp_eta).all(): raise RuntimeError("风险分数溢出，检查模型。")
        cumulative_at_risk=np.cumsum(exp_eta[::-1])[::-1]
        event_times,counts=np.unique(ts[es==1],return_counts=True)
        starts=np.searchsorted(ts,event_times,side="left")
        self.event_times=event_times
        self.baseline_ch=np.cumsum(counts/cumulative_at_risk[starts])

    def score(self,df):
        return self.encoder.transform(df).to_numpy()@self.beta

    def predict_risk(self,df,horizon):
        if not 0<horizon<=self.training_max_time:
            raise ValueError("预测时间超出训练随访支持。")
        idx=np.searchsorted(self.event_times,horizon,side="right")-1
        h0=self.baseline_ch[idx] if idx>=0 else 0.0
        return -np.expm1(-h0*np.exp(self.score(df)-self.eta_center))

    def coefficient_table(self):
        names=self.encoder.state["columns"]
        scales=np.array([self.encoder.state["scales"][c] for c in names])
        b=self.beta/scales
        out=pd.DataFrame({"term":names,"log_HR":b,"HR":np.exp(b)})
        # 惩罚模型不输出未经校正的推断性置信区间/p值。
        if self.cov is not None:
            se=np.sqrt(np.diag(self.cov))/scales
            out["SE"]=se; out["ci_low"]=np.exp(b-1.96*se); out["ci_high"]=np.exp(b+1.96*se)
            out["p_value"]=2*norm.sf(np.abs(b/se))
        return out

    def save(self,path: Path):
        write_json(path,{"model_class":"CoxModel","schema_version":1,"features":self.features,"alpha":self.alpha,
                         "encoder":self.encoder.state,"beta":self.beta,"cov":self.cov,
                         "event_times":self.event_times,"baseline_ch":self.baseline_ch,
                         "eta_center":self.eta_center,"training_max_time":self.training_max_time,
                         "diagnostics":self.diagnostics})

    @classmethod
    def load(cls,path: Path):
        d=json.loads(path.read_text(encoding="utf-8"))
        if d.get("schema_version")!=1 or d.get("model_class")!="CoxModel": raise ValueError("模型格式不支持。")
        obj=cls(d["features"],d["alpha"]); obj.encoder=FeatureEncoder.from_state(d["encoder"])
        for k in ("beta","event_times","baseline_ch"): setattr(obj,k,np.array(d[k],float))
        obj.cov=np.array(d["cov"]) if d["cov"] is not None else None
        for k in ("eta_center","training_max_time","diagnostics"): setattr(obj,k,d[k])
        return obj

    def schoenfeld_residuals(self,df):
        """训练集未缩放Schoenfeld残差，仅作诊断图，不冒充正式PH全局检验。"""
        X=self.encoder.transform(df).to_numpy(); t,e=validate_outcome(df.cvd_time,df.cvd_event)
        score=X@self.beta; rr=np.exp(score-score.mean()); rows=[]
        for i in np.flatnonzero(e):
            m=t>=t[i]; weighted=(X[m]*rr[m,None]).sum(axis=0)/rr[m].sum()
            rows.append(np.r_[t[i],X[i]-weighted])
        return pd.DataFrame(rows,columns=["event_time"]+self.encoder.state["columns"])
