"""从原始数据到冻结模型、验证和最终测试的完整教学流水线。"""
from __future__ import annotations
from pathlib import Path
import json
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold
from .common import data_dir,output_dir,write_json,sha256,config_hash,provenance_label
from .data import load_clean,load_emr,audit_clean
from .splitting import create_splits,validate_splits,select_split
from .survival import CoxModel
from .metrics import KaplanMeier,evaluate_survival,brier_ipcw,calibration_edges,calibration_table
from .basics import run_basics
from .plots import draw_eda,draw_forest,draw_calibration,draw_ph
from .reconstruction import reconstruct,compare_to_clean
from .reporting import generate_report


def prepare(cfg):
    folder=data_dir(cfg); out=output_dir(cfg)
    if cfg["mode"]=="official":
        mp=folder/"manifest.json"
        if not mp.exists(): raise RuntimeError("官方来源manifest不存在，请先执行download；禁止把演示文件手动改名成官方数据。")
        m=json.loads(mp.read_text(encoding="utf-8"))
        if m.get("status")!="downloaded" or m.get("sources",{}).get("asset1",{}).get("sha256")!=sha256(folder/"asset1.csv"):
            raise RuntimeError("官方数据的来源/哈希未通过检查。")
    df=load_clean(cfg); digest=sha256(folder/"asset1.csv")
    manifest_path=out/"split_manifest.json"
    if manifest_path.exists():
        m=json.loads(manifest_path.read_text(encoding="utf-8"))
        if m["data_sha256"]!=digest or m["seed"]!=cfg["seed"] or m["train_fraction"]!=cfg["train_fraction"] or m["valid_fraction"]!=cfg["valid_fraction"]:
            raise RuntimeError("数据或划分参数已改变。不要复用旧划分或已解锁测试集。")
        splits=pd.read_csv(out/"splits.csv"); validate_splits(splits,df)
        if m["splits_sha256"]!=sha256(out/"splits.csv"): raise RuntimeError("已冻结的划分文件被修改。")
    else:
        splits=create_splits(df,cfg); splits.to_csv(out/"splits.csv",index=False)
        write_json(manifest_path,{"data_sha256":digest,"seed":cfg["seed"],"train_fraction":cfg["train_fraction"],
                                  "valid_fraction":cfg["valid_fraction"],"splits_sha256":sha256(out/"splits.csv")})
    audit=audit_clean(df,cfg["horizon_years"]); audit["data_provenance"]=provenance_label(cfg)
    write_json(out/"data_audit.json",audit)
    return df,splits


def training_summary(train):
    rows=[]
    for c in ("Age","BMI","HbA1c","eGFR","SBP"):
        s=train[c]; rows.append({"variable":c,"n":len(s),"summary":f"mean {s.mean():.3f}; SD {s.std():.3f}; median {s.median():.3f}; IQR {s.quantile(.25):.3f}–{s.quantile(.75):.3f}"})
    for c in ("diabetes","CKD","AF","IRSD_quintile","smoking_status"):
        for k,n in train[c].value_counts(dropna=False).sort_index().items():
            rows.append({"variable":f"{c}={k}","n":int(n),"summary":f"{n/len(train):.2%}"})
    return pd.DataFrame(rows)


def subgroup_table(train,valid,model,cfg):
    rows=[]; horizon=cfg["horizon_years"]
    definitions={"age_18_39":valid.Age<40,"age_40_59":valid.Age.between(40,60,inclusive="left"),"age_60_plus":valid.Age>=60}
    definitions.update({f"IRSD_{q}":valid.IRSD_quintile==q for q in range(1,6)})
    for name,mask in definitions.items():
        d=valid.loc[mask]; row={"subgroup":name,"n":len(d),"observed_events":int(d.cvd_event.sum())}
        if len(d)<50 or d.cvd_event.sum()<5 or (d.cvd_time>horizon).sum()<20:
            row["status"]="sparse: no full metric set"
        else:
            row.update(evaluate_survival(train,d,model.predict_risk(d,horizon),model.score(d),horizon,cfg["min_censor_survival"]))
            row["status"]="exploratory; not external validation"
        rows.append(row)
    return pd.DataFrame(rows)


def train_models(cfg):
    out=output_dir(cfg)
    if (out/"test_evaluation.json").exists(): raise RuntimeError("本输出目录的测试集已打开，禁止继续重训/选择模型。")
    df,splits=prepare(cfg); train=select_split(df,splits,"train"); valid=select_split(df,splits,"valid")
    horizon=cfg["horizon_years"]; features=cfg["features"]
    training_summary(train).to_csv(out/"tables/baseline_training.csv",index=False)
    linear,logistic,basic_metrics=run_basics(train,valid)
    linear.to_csv(out/"tables/linear_coefficients.csv",index=False); logistic.to_csv(out/"tables/logistic_coefficients.csv",index=False)
    write_json(out/"basics_validation.json",basic_metrics); draw_eda(train,out/"figures")
    cv=StratifiedKFold(n_splits=cfg["cv_folds"],shuffle=True,random_state=cfg["seed"]+2)
    folds=list(cv.split(train,train.cvd_event)); rows=[]
    for alpha in cfg["ridge_alphas"]:
        for k,(it,iv) in enumerate(folds,1):
            a=train.iloc[it]; b=train.iloc[iv]
            # 每个折都重新fit编码器和基线危险，不预先在全训练集拟合。
            m=CoxModel(features,alpha).fit(a)
            p=m.predict_risk(b,horizon)
            loss=brier_ipcw(a.cvd_time,a.cvd_event,b.cvd_time,b.cvd_event,p,horizon,cfg["min_censor_survival"])
            rows.append({"alpha":alpha,"fold":k,"n_train":len(a),"n_valid":len(b),"Brier_IPCW":loss,"iterations":m.diagnostics["iterations"]})
            print(f"  CV alpha={alpha:g}, fold={k}, Brier={loss:.5f}",flush=True)
    cvtable=pd.DataFrame(rows); cvtable.to_csv(out/"tables/cv_results.csv",index=False)
    means=cvtable.groupby("alpha").Brier_IPCW.mean().sort_values(kind="stable")
    selected_alpha=float(means.index[0]); baseline=CoxModel(features,0).fit(train)
    selected=baseline if selected_alpha==0 else CoxModel(features,selected_alpha).fit(train)
    baseline.save(out/"models/cox_unpenalized.json"); selected.save(out/"models/selected_cox.json")
    coefficients=baseline.coefficient_table(); coefficients.to_csv(out/"tables/cox_coefficients.csv",index=False)
    selected.coefficient_table().to_csv(out/"tables/selected_coefficients.csv",index=False)
    draw_forest(coefficients,out/"figures")
    residuals=baseline.schoenfeld_residuals(train); residuals.to_csv(out/"tables/schoenfeld_training.csv",index=False); draw_ph(residuals,out/"figures")
    valrows=[]
    nullrisk=1-KaplanMeier.fit(train.cvd_time,train.cvd_event).at(horizon)
    nullbs=brier_ipcw(train.cvd_time,train.cvd_event,valid.cvd_time,valid.cvd_event,np.full(len(valid),nullrisk),horizon,cfg["min_censor_survival"])
    for name,m in (("Cox_unpenalized",baseline),("Cox_selected_by_training_CV",selected)):
        row=evaluate_survival(train,valid,m.predict_risk(valid,horizon),m.score(valid),horizon,cfg["min_censor_survival"])
        row.update({"model":name,"alpha":m.alpha,"null_Brier":nullbs,"Brier_skill_vs_training_KM":1-row["Brier_IPCW"]/nullbs})
        valrows.append(row)
    pd.DataFrame(valrows).to_csv(out/"tables/validation_metrics.csv",index=False)
    edges=calibration_edges(selected.predict_risk(train,horizon),cfg["calibration_bins"])
    # JSON中保存有限内分割点；±inf在加载时显式恢复。
    write_json(out/"calibration_boundaries.json",{"inner_edges":edges[1:-1].tolist(),"learned_on":"train"})
    calibration=calibration_table(valid.cvd_time,valid.cvd_event,selected.predict_risk(valid,horizon),horizon,edges)
    calibration.to_csv(out/"tables/calibration_valid.csv",index=False); draw_calibration(calibration,out/"figures")
    subgroup_table(train,valid,selected,cfg).to_csv(out/"tables/subgroup_valid.csv",index=False)
    write_json(out/"frozen_spec.json",{"config_sha256":config_hash(cfg),"data_sha256":sha256(data_dir(cfg)/"asset1.csv"),
                                      "splits_sha256":sha256(out/"splits.csv"),"model_sha256":sha256(out/"models/selected_cox.json"),
                                      "calibration_sha256":sha256(out/"calibration_boundaries.json"),"selected_alpha":selected_alpha,
                                      "selection_rule":f"Minimum mean training-only CV {horizon:g}-year IPCW Brier; validation not used for model selection.",
                                      "final_fit_set":"train only (70%); no train+valid refit", "test_opened":False,
                                      "source":provenance_label(cfg)})
    return generate_report(cfg)


def reconstruct_emr(cfg):
    out=output_dir(cfg); clean,splits=prepare(cfg); tables=load_emr(cfg)
    rec,audit,meas=reconstruct(tables)
    rec.to_csv(out/"tables/reconstructed_cohort.csv",index=False)
    meas.to_csv(out/"tables/standardized_measurements.csv",index=False)
    compare_to_clean(rec,clean).to_csv(out/"tables/reconstruction_comparison.csv",index=False)
    write_json(out/"reconstruction_audit.json",audit)
    modelpath=out/"models/selected_cox.json"
    if modelpath.exists():
        # 受控数据错误实验：其他所有Asset1特征固定，只替换HbA1c；不是EMR-only验证。
        model=CoxModel.load(modelpath); train=select_split(clean,splits,"train"); valid=select_split(clean,splits,"valid")
        bad,_,_=reconstruct(tables,convert_units=False)
        rows=[]
        for name,source in (("correct_unit_conversion",rec),("deliberately_omitted_conversion",bad)):
            values=source.set_index("Patient_ID").HbA1c
            v=valid.copy(); v["HbA1c"]=v.Patient_ID.map(values)
            row=evaluate_survival(train,v,model.predict_risk(v,cfg["horizon_years"]),model.score(v),cfg["horizon_years"],cfg["min_censor_survival"])
            row["scenario"]=name; row["design"]="Only HbA1c changed; all other Asset1 predictors held fixed. NOT external/EMR-only validation."
            rows.append(row)
        pd.DataFrame(rows).to_csv(out/"tables/unit_sensitivity_valid.csv",index=False)
    return generate_report(cfg)


def finalize(cfg,unlock_test=False):
    if not unlock_test: raise RuntimeError("测试集默认封存。完成方案冻结后显式添加 --unlock-test。")
    out=output_dir(cfg)
    if (out/"test_evaluation.json").exists(): raise RuntimeError("测试结果已存在；请阅读已有结果，不要反复调参测试。")
    fp=out/"frozen_spec.json"
    if not fp.exists(): raise RuntimeError("请先完成train，冻结模型。")
    frozen=json.loads(fp.read_text(encoding="utf-8"))
    checks={"config_sha256":config_hash(cfg),"data_sha256":sha256(data_dir(cfg)/"asset1.csv"),
            "splits_sha256":sha256(out/"splits.csv"),"model_sha256":sha256(out/"models/selected_cox.json"),
            "calibration_sha256":sha256(out/"calibration_boundaries.json")}
    if any(frozen[k]!=v for k,v in checks.items()): raise RuntimeError("冻结后配置、数据、划分、模型或校准边界发生变化。测试已阻止。")
    df,splits=prepare(cfg); train=select_split(df,splits,"train"); test=select_split(df,splits,"test")
    model=CoxModel.load(out/"models/selected_cox.json"); h=cfg["horizon_years"]
    row=evaluate_survival(train,test,model.predict_risk(test,h),model.score(test),h,cfg["min_censor_survival"])
    row.update({"model":"frozen_selected_cox","alpha":model.alpha})
    pd.DataFrame([row]).to_csv(out/"tables/test_metrics.csv",index=False)
    inner=json.loads((out/"calibration_boundaries.json").read_text())["inner_edges"]
    cal=calibration_table(test.cvd_time,test.cvd_event,model.predict_risk(test,h),h,np.r_[-np.inf,inner,np.inf])
    cal.to_csv(out/"tables/calibration_test.csv",index=False)
    draw_calibration(cal,out/"figures","calibration_test.png","Final frozen-model test calibration")
    write_json(out/"test_evaluation.json",{"opened":True,"data_provenance":provenance_label(cfg),"metrics":row,"frozen_spec":frozen,
                                           "warning":"测试集已打开；不得以本结果反复选择模型。仅报告点估计，未计算性能指标bootstrap置信区间。"})
    return generate_report(cfg)


def run_all(cfg):
    prepare(cfg); train_models(cfg); reconstruct_emr(cfg)
    return generate_report(cfg)
