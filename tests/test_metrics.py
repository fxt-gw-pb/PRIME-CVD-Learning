import numpy as np
import pytest
from statsmodels.duration.survfunc import SurvfuncRight
from sklearn.metrics import roc_auc_score
from primecvd.metrics import KaplanMeier,concordance,brier_ipcw,auc_ipcw,ipcw_weights,calibration_edges,calibration_table


def test_km_hand_calculation():
    km=KaplanMeier.fit([1,2,3,4],[1,0,1,0])
    assert km.at(.5)==1
    assert km.at(1)==pytest.approx(.75)
    assert km.at(3)==pytest.approx(.375)
    assert km.at(3,left=True)==pytest.approx(.75)


def test_km_matches_statsmodels(clean):
    t=clean.cvd_time.to_numpy(); e=clean.cvd_event.to_numpy()
    ref=SurvfuncRight(t,e); ours=KaplanMeier.fit(t,e)
    np.testing.assert_allclose(ours.at(ref.surv_times),ref.surv_prob,atol=1e-12)


def test_km_no_event_ci_not_zero_width():
    risk,lo,hi=KaplanMeier.fit([2,3,4],[0,0,0]).risk_ci(2.5)
    assert risk==0 and np.isnan(lo) and np.isnan(hi)


def test_cindex_direction_and_ties():
    t=[1,2,3,4]; e=[1,1,1,1]
    assert concordance(t,e,[4,3,2,1])==1
    assert concordance(t,e,[1,2,3,4])==0
    assert concordance(t,e,[1,1,1,1])==.5
    assert concordance([1,1,2],[1,0,1],[3,2,1])==1


def test_brier_reduces_to_binary_without_early_censoring():
    t=np.array([1.,2.,3.,4.]); e=np.array([1,1,0,0]); p=np.array([.8,.3,.1,.2])
    actual=brier_ipcw(t,e,t,e,p,1.5)
    assert actual==pytest.approx(np.mean((np.array([1,0,0,0])-p)**2))
    assert auc_ipcw(t,e,t,e,p,1.5)==roc_auc_score([1,0,0,0],p)


def test_early_censored_has_zero_weight():
    t=np.array([1.,2.,3.,4.]); e=np.array([0,1,0,0]); p=np.array([.99,.7,.2,.1])
    y,w,case,control=ipcw_weights(t,e,t,e,2.5)
    assert w[0]==0
    np.testing.assert_allclose(w[1:],[4/3]*3)
    expected=(4/3)*((1-.7)**2+.2**2+.1**2)/4
    assert brier_ipcw(t,e,t,e,p,2.5)==pytest.approx(expected)


def test_bad_horizon_rejected():
    with pytest.raises(ValueError): brier_ipcw([1,2,3],[1,0,0],[1,2,3],[1,0,0],[.1,.1,.1],5)


def test_invalid_probability_rejected():
    with pytest.raises(ValueError): brier_ipcw([1,2,3],[1,0,0],[1,2,3],[1,0,0],[2,.1,.1],1.5)


def test_calibration_bins_from_train_only():
    edges=calibration_edges([.1,.2,.3,.4,.5],bins=2)
    assert edges[1]==.3
    tab=calibration_table([1,3,4,6],[1,0,1,0],[.01,.2,.4,.99],2,edges)
    assert tab.n.sum()==4
    assert tab.group.tolist()==[1,2]


def test_optional_sksurv_metric_crosscheck(clean):
    sk=pytest.importorskip("sksurv.metrics",reason="可选scikit-survival未安装；核心测试不依赖它。")
    from sksurv.util import Surv
    a=clean.iloc[:3000]; b=clean.iloc[3000:4000]
    yt=Surv.from_arrays(a.cvd_event.astype(bool),a.cvd_time)
    yv=Surv.from_arrays(b.cvd_event.astype(bool),b.cvd_time)
    p=np.linspace(.01,.7,len(b)); h=5.
    _,ref=sk.brier_score(yt,yv,(1-p)[:,None],[h])
    assert brier_ipcw(a.cvd_time,a.cvd_event,b.cvd_time,b.cvd_event,p,h)==pytest.approx(ref[0],abs=1e-10)
    auc,_=sk.cumulative_dynamic_auc(yt,yv,p,[h])
    assert auc_ipcw(a.cvd_time,a.cvd_event,b.cvd_time,b.cvd_event,p,h)==pytest.approx(auc[0],abs=1e-10)
