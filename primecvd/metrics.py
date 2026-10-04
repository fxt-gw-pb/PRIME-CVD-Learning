"""可读的生存评价教学实现；支持普通右删失，不支持竞争风险/左截断。
IPCW 使用训练集的边际删失分布；需要独立删失假设和足够的时间支持。
事件权重使用 G(T-)，同一时刻事件先于删失；详见 docs/05_methods.md。
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score


def validate_outcome(time, event):
    t=np.asarray(time,dtype=float); e=np.asarray(event)
    if t.ndim!=1 or e.shape!=t.shape or not len(t): raise ValueError("time/event形状错误。")
    if not np.isfinite(t).all() or np.any(t<=0): raise ValueError("观察时间必须有限且>0。")
    if not np.isin(e,[0,1]).all(): raise ValueError("事件必须为0/1。")
    return t,e.astype(int)


@dataclass
class KaplanMeier:
    times: np.ndarray
    survival: np.ndarray
    greenwood: np.ndarray
    observed_times: np.ndarray

    @classmethod
    def fit(cls, time, event, reverse: bool=False):
        t,e=validate_outcome(time,event)
        times,inv,counts=np.unique(t,return_inverse=True,return_counts=True)
        deaths=np.bincount(inv,weights=e,minlength=len(times))
        risk=len(t)-np.r_[0,np.cumsum(counts)[:-1]]
        if reverse:
            # 反向KM：同刻先移除结局事件，再计算删失分布的跳跃。
            d=counts-deaths; risk=risk-deaths
        else: d=deaths
        frac=np.divide(d,risk,out=np.zeros_like(d,dtype=float),where=risk>0)
        surv=np.cumprod(1-frac)
        terms=np.divide(d,risk*(risk-d),out=np.zeros_like(d,dtype=float),where=(risk-d)>0)
        gw=np.cumsum(terms)
        return cls(times,surv,gw,t)

    def at(self, times, left: bool=False):
        arr=np.atleast_1d(np.asarray(times,float))
        idx=np.searchsorted(self.times,arr,side="left" if left else "right")-1
        out=np.ones_like(arr)
        ok=idx>=0; out[ok]=self.survival[idx[ok]]
        return float(out[0]) if np.ndim(times)==0 else out

    def risk_ci(self, horizon: float):
        """1-KM及点态log-log 95%CI；S=0/1边界不伪造零宽区间。"""
        if horizon>self.observed_times.max(): return np.nan,np.nan,np.nan
        s=self.at(horizon)
        if not 0<s<1: return 1-s,np.nan,np.nan
        i=np.searchsorted(self.times,horizon,side="right")-1
        g=self.greenwood[i]
        se=np.sqrt(g)/abs(np.log(s)); center=np.log(-np.log(s))
        low_s=np.exp(-np.exp(center+1.96*se)); high_s=np.exp(-np.exp(center-1.96*se))
        return 1-s,1-high_s,1-low_s

    def frame(self):
        return pd.DataFrame({"time":self.times,"survival":self.survival,"cumulative_risk":1-self.survival})


def ipcw_weights(train_time,train_event,time,event,horizon,min_g=.05):
    tr,er=validate_outcome(train_time,train_event); t,e=validate_outcome(time,event)
    if not 0<horizon<min(tr.max(),t.max()):
        raise ValueError("预测时间须严格小于训练/评价最大随访时间，禁止越界外推。")
    g=KaplanMeier.fit(tr,er,reverse=True)
    gt=g.at(horizon)
    if gt<min_g: raise ValueError(f"G({horizon})={gt:.4f}太小，IPCW不稳定。")
    cases=(e==1)&(t<=horizon); controls=t>horizon
    weights=np.zeros(len(t)); gc=g.at(t[cases],left=True)
    if np.any(gc<min_g): raise ValueError("事件时间处的删失生存概率太低。")
    weights[cases]=1/gc; weights[controls]=1/gt
    labels=cases.astype(int)
    # 早期删失的权重为0：没有将其当作已知阴性。
    return labels,weights,cases,controls


def brier_ipcw(train_time,train_event,time,event,risk,horizon,min_g=.05):
    p=np.asarray(risk,float)
    if p.shape!=np.asarray(time).shape or not np.isfinite(p).all() or np.any((p<0)|(p>1)):
        raise ValueError("预测风险必须为[0,1]有限概率，且与评价队列等长。")
    y,w,_,_=ipcw_weights(train_time,train_event,time,event,horizon,min_g)
    return float(np.mean(w*(y-p)**2))


def auc_ipcw(train_time,train_event,time,event,risk,horizon,min_g=.05):
    y,w,cases,controls=ipcw_weights(train_time,train_event,time,event,horizon,min_g)
    if not cases.any() or not controls.any(): return float("nan")
    use=w>0
    return float(roc_auc_score(y[use],np.asarray(risk)[use],sample_weight=w[use]))


def concordance(time,event,score,train_time=None,train_event=None,tau=None,min_g=.05):
    """高分=更高风险。给训练结局和tau时为截断Uno型IPCW C，否则为Harrell C。
    不比较同刻的两个事件；事件与同刻删失可比；分数近似相同计0.5。
    """
    t,e=validate_outcome(time,event); s=np.asarray(score,float)
    if s.shape!=t.shape or not np.isfinite(s).all(): raise ValueError("分数形状或数值错误。")
    idx=np.flatnonzero(e==1)
    weights=np.ones(len(t))
    if train_time is not None:
        if tau is None: raise ValueError("Uno型C需要明确tau。")
        tr,er=validate_outcome(train_time,train_event)
        if not 0<tau<min(tr.max(),t.max()): raise ValueError("tau无足够随访支持。")
        g=KaplanMeier.fit(tr,er,reverse=True)
        if g.at(tau)<min_g: raise ValueError("删失权重不稳定。")
        idx=idx[t[idx]<=tau]
        weights[idx]=1/g.at(t[idx],left=True)**2
    numerator=denominator=0.0
    for i in idx:
        comparable=(t>t[i])|((t==t[i])&(e==0))
        dif=s[i]-s[comparable]
        tied=np.abs(dif)<=1e-8
        correct=np.sum((dif>0)&~tied)+.5*np.sum(tied)
        numerator+=weights[i]*correct; denominator+=weights[i]*len(dif)
    return float(numerator/denominator) if denominator else float("nan")


def evaluate_survival(train, evaluation, risk, score, horizon=5.0, min_g=.05):
    args=(train.cvd_time,train.cvd_event,evaluation.cvd_time,evaluation.cvd_event)
    km=KaplanMeier.fit(evaluation.cvd_time,evaluation.cvd_event)
    kr,lo,hi=km.risk_ci(horizon)
    return {"n":len(evaluation),"observed_events":int(evaluation.cvd_event.sum()),
            "events_by_horizon":int(((evaluation.cvd_event==1)&(evaluation.cvd_time<=horizon)).sum()),
            "early_censored":int(((evaluation.cvd_event==0)&(evaluation.cvd_time<=horizon)).sum()),
            "at_risk_after_horizon":int((evaluation.cvd_time>horizon).sum()),
            "horizon_years":horizon,"mean_predicted_risk":float(np.mean(risk)),
            "KM_risk":kr,"KM_risk_ci_low":lo,"KM_risk_ci_high":hi,
            "Harrell_C":concordance(evaluation.cvd_time,evaluation.cvd_event,score),
            "Uno_C_to_horizon":concordance(evaluation.cvd_time,evaluation.cvd_event,score,train.cvd_time,train.cvd_event,horizon,min_g),
            "AUC_IPCW":auc_ipcw(*args,risk,horizon,min_g),
            "Brier_IPCW":brier_ipcw(*args,risk,horizon,min_g)}


def calibration_edges(training_risk,bins=5):
    v=np.asarray(training_risk,float)
    inner=np.unique(np.quantile(v,np.linspace(0,1,bins+1)[1:-1]))
    return np.r_[-np.inf,inner,np.inf]


def calibration_table(time,event,risk,horizon,edges):
    t,e=validate_outcome(time,event); p=np.asarray(risk,float)
    groups=np.digitize(p,np.asarray(edges)[1:-1],right=True)
    rows=[]
    for g in range(len(edges)-1):
        m=groups==g
        if not m.any(): continue
        km=KaplanMeier.fit(t[m],e[m]); obs,lo,hi=km.risk_ci(horizon)
        events=int(((e[m]==1)&(t[m]<=horizon)).sum()); atrisk=int((t[m]>horizon).sum())
        rows.append({"group":g+1,"n":int(m.sum()),"events_by_horizon":events,"at_risk_after_horizon":atrisk,
                     "mean_prediction":float(p[m].mean()),"KM_risk":obs,"ci_low":lo,"ci_high":hi,
                     "sparse_or_unsupported":events<5 or atrisk<20 or not np.isfinite(obs)})
    return pd.DataFrame(rows)
