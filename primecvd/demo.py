"""独立工程测试样本，不是官方PRIME-CVD，不宣称重现其参数或行记录。"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.special import expit
from .common import write_json, sha256
from .data import EMR_FILES, patient_id_from_source_row


def create_demo(folder: Path, n: int = 5000, seed: int = 927) -> dict:
    if n < 500: raise ValueError("演示至少500人，以便检验训练与验证流程。")
    folder.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    irsd = rng.integers(1, 6, n)
    age = rng.uniform(25, 85, n)
    bmi = np.clip(rng.normal(29 - (irsd - 3)*0.5, 4.5, n), 16, 48)
    smoking = rng.choice(["non", "ex", "current"], n, p=[0.7, 0.2, 0.1])
    dm = rng.binomial(1, expit(-2.4 + 0.04*(age-50) + 0.09*(bmi-28)))
    # 有意提高罕见病频率，便于小样本软件测试，不用于描述官方人群。
    ckd = rng.binomial(1, expit(-3.2 + 0.02*(age-50) + 0.4*dm))
    af = rng.binomial(1, expit(-3.4 + 0.04*(age-50)))
    hba = np.clip(rng.normal(4.8+1.8*dm, 0.65, n), 2.3, 13)
    egfr = rng.normal(87-0.18*(age-50)-17*ckd, 5, n)
    sbp = rng.normal(122+0.35*(age-50)+(bmi-28)+8*dm, 12, n)
    lp = .032*(age-50)+.65*dm+.55*af+.015*(sbp-120)+.22*(smoking=="current")
    event_time = rng.exponential(1/(0.022*np.exp(lp)))
    censor_time = rng.uniform(3.4, 6.4, n)
    df = pd.DataFrame({"IRSD_quintile":irsd,"Age":age,"smoking_status":smoking,"BMI":bmi,
                       "diabetes":dm,"CKD":ckd,"HbA1c":hba,"eGFR":egfr,"SBP":sbp,"AF":af,
                       "cvd_event":(event_time<=censor_time).astype(int),"cvd_time":np.minimum(event_time,censor_time)})
    df.to_csv(folder/"asset1.csv", index=False)
    pid=patient_id_from_source_row(np.arange(n))
    master=pd.DataFrame({"Patient_ID":pid,"Age_At_2024":np.round(age+7,2),"SMOKING_STATUS":smoking,
                          "IRSD_Quintile":irsd,"CVD_Event":df.cvd_event})
    ix=master.index[(master.SMOKING_STATUS=="non") & (rng.uniform(size=n)<.16)]
    master.loc[ix,"SMOKING_STATUS"]=np.nan
    dates=pd.Timestamp("2017-01-01")+pd.to_timedelta(df.cvd_time*365.25,unit="D")
    master["CVD_Time"]=dates.dt.strftime("%Y-%m")
    master.loc[master.CVD_Event==0,"CVD_Time"]="2022-12"
    months=pd.date_range("2012-01-01","2016-12-01",freq="MS").strftime("%Y-%m").to_numpy()
    diagnoses=[]
    vocab={"diabetes":["Diabetes","T2DM","ICD10: E11"],"CKD":["CKD","Chronic renal failure","ICD10: N18"],"AF":["AF","A-fib","ICD10: I48"]}
    for c in ("diabetes","CKD","AF"):
        ids=pid[df[c].to_numpy()==1]
        diagnoses.append(pd.DataFrame({"Patient_ID":ids,"Category":rng.choice(vocab[c],len(ids)),"Date":rng.choice(months,len(ids))}))
    diseases=pd.concat(diagnoses,ignore_index=True).sample(frac=1,random_state=seed)
    measurement=[]
    vocabm={"HbA1c":["HbA1c","Hb A1c","Glycated haemoglobin"],"eGFR":["eGFR","Estimated GFR","LOINC: 33914-3"],"SBP":["SBP","Systolic BP","Systolic blood pressure"]}
    for c in ("HbA1c","eGFR","SBP"):
        vals=df[c].to_numpy().copy(); units=np.array([{"HbA1c":"%","eGFR":"mL/min/1.73m2","SBP":"mmHg"}[c]]*n,dtype=object)
        if c=="HbA1c":
            conv=rng.choice(n,int(.05*n),replace=False); vals[conv]=(vals[conv]-2.15)*10.929; units[conv]="mmol/mol"
        measurement.append(pd.DataFrame({"Patient_ID":pid,"Measure":c,"Value":np.round(vals,2),"Description":rng.choice(vocabm[c],n),"Date":rng.choice(months,n),"Unit":units}))
    meas=pd.concat(measurement,ignore_index=True).sample(frac=1,random_state=seed)
    for k,d in (("master",master),("diseases",diseases),("measurements",meas)):
        d.to_csv(folder/EMR_FILES[k],index=False)
    manifest={"data_status":"INDEPENDENT_DEMO_NOT_OFFICIAL_PRIME_CVD","n":n,"seed":seed,
              "purpose":"仅用于工程测试与离线教学；不复制官方参数，不作为官方分析结果。",
              "files":{p.name:sha256(p) for p in folder.glob("*.csv")}}
    write_json(folder/"manifest.json",manifest)
    return manifest
