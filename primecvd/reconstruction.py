"""病历式表重建：保留不能恢复的信息，禁止偷偷用Asset1回填模型特征。
患者映射只能用于核对同一合成人群；绝不是外部验证。
"""
from __future__ import annotations
import re
import unicodedata
import numpy as np
import pandas as pd


def normalize(text):
    if pd.isna(text): return ""
    return re.sub(r"[^a-z0-9]","",unicodedata.normalize("NFKC",str(text)).casefold())

# 官方 Asset2 的全部写法（2026-09-27 核对：糖尿病 6 种、CKD 7 种、房颤 6 种）都已收录。
# "High glucose"/"High blood sugar" 按作者 Data Asset 2 派生代码属于糖尿病；
# 真实 EMR 中一次高血糖记录不等于糖尿病诊断，这条映射只适用于本合成数据。
DISEASE_TERMS={
 "diabetes":["diabetes","diabetes mellitus","type 2 diabetes","type ii diabetes","type 2 diabetes mellitus","T2DM","DM","NIDDM","ICD10: E11","ICD9: 250","ICD9: 250.00","sugar diabetes","type2dm",
             "High glucose","High blood sugar"],
 "CKD":["CKD","chronic kidney disease","chronic renal disease","chronic renal failure","renal insufficiency","chronic renal insufficiency","ICD10: N18","ICD9: 585","CRF"],
 "AF":["AF","atrial fibrillation","A-fib","AFib","ICD10: I48","ICD9: 427.31","atrial fib"]}
# 官方 Asset2 的 35 种 Description 写法都已收录（HbA1c 10 种、eGFR 10 种、SBP 12 种，
# BMI/Height/Weight 各 1 种）。注意："HbA1c mmol/mol" 这个名称里的单位不可信，
# 它的大多数记录 Unit 列写的是 %；单位一律以 Unit 列为准。"HbAlc" 中是字母 l 而不是数字 1。
MEAS_TERMS={
 "HbA1c":["HbA1c","Hb A1c","HBA1C","A1C","Glycated haemoglobin","Glycated hemoglobin","Glycosylated haemoglobin","Glycosylated hemoglobin","Haemoglobin A1c","Hemoglobin A1c","HbA1C (%)","HbA1c IFCC","LOINC: 4548-4","LOINC: 17856-6",
          "HA1C","HbAlc","HbA1c mmol/mol"],
 "eGFR":["eGFR","Estimated GFR","estimated glomerular filtration rate","GFR estimated","eGFR CKD-EPI","eGFR (CKD-EPI)","eGFR (MDRD)","LOINC: 33914-3","LOINC: 62238-1","eGFRr",
         "GFR","GFR-e","e GFR","eGFR (mL/min/1.73m²)"],
 "SBP":["SBP","systolic BP","Systolic blood pressure","BP systolic","Systolic","Systolic pressure","Systolic BP (mmHg)","SystolicBloodPressure","LOINC: 8480-6","Systolic blood presure","Systolic bloood pressure",
        "BP SYS","SBP (mmHg)","SyBP","Syst BP","Blood Pressure – Systolic"],
 "BMI":["BMI","Body mass index","LOINC: 39156-5"],
 "Height":["Height","Body height"],
 "Weight":["Weight","Body weight"]}
DLOOK={normalize(x):k for k,vs in DISEASE_TERMS.items() for x in vs}
MLOOK={normalize(x):k for k,vs in MEAS_TERMS.items() for x in vs}


FEET_INCHES=re.compile(r"""^\s*(\d+)\s*'\s*(\d+)\s*"\s*$""")


def feet_inches_to_cm(text):
    """把 5'7" 这样的英制身高换算成厘米。官方数据中存在 5'12" 这类未进位写法，按 5×12+12 英寸照常换算。"""
    m=FEET_INCHES.match(str(text))
    if m is None: raise ValueError(f"无法解析的英制身高：{text!r}")
    return (int(m.group(1))*12+int(m.group(2)))*2.54


def disease_from_label(label):
    n=normalize(label)
    if n in DLOOK: return DLOOK[n]
    # 仅匹配这份模拟数据生成器使用的疾病族，不能泛化为临床编码定义。
    for prefix,key in (("icd10e11","diabetes"),("icd9250","diabetes"),("icd10n18","CKD"),("icd9585","CKD"),("icd10i48","AF"),("icd942731","AF")):
        if n.startswith(prefix): return key
    return None


def normalize_measurements(meas,convert_units=True,use_measure_hint=True):
    d=meas.copy()
    if not {"Description","Value","Unit"}.issubset(d): raise ValueError("检验表缺少Description/Value/Unit。")
    mapped=d.Description.map(lambda x:MLOOK.get(normalize(x)))
    hint=d.Measure.map(lambda x:MLOOK.get(normalize(x))) if "Measure" in d else pd.Series(None,index=d.index)
    conflict=mapped.notna()&hint.notna()&(mapped!=hint)
    if conflict.any(): raise ValueError("Measure和Description给出相互冲突的测量类型。")
    d["canonical_measure"]=mapped.fillna(hint) if use_measure_hint else mapped
    unknown=d.loc[d.canonical_measure.isna(),"Description"].drop_duplicates().tolist()
    if unknown: raise ValueError(f"出现未映射测量名称，需审查词典：{unknown[:20]}。原始数据不会被丢弃。")
    used_hint=int((mapped.isna()&hint.notna()).sum()) if use_measure_hint else 0
    imperial=((d.canonical_measure=="Height")&(d.Unit.map(normalize)=="feetandinch")).to_numpy()
    values=np.empty(len(d))
    values[~imperial]=pd.to_numeric(d.Value[~imperial],errors="raise").to_numpy(float)
    values[imperial]=d.Value[imperial].map(feet_inches_to_cm).to_numpy(float)
    if not np.isfinite(values).all(): raise ValueError("测量值非有限数字。")
    converted=0; unknown_units=[]; bmi_without_unit=0
    for i,(measure,unit) in enumerate(zip(d.canonical_measure,d.Unit)):
        un=normalize(unit); is_percent=str(unit).strip()=="%" or un in {"percent","pct"}
        if measure=="HbA1c":
            if un=="mmolmol":
                if convert_units: values[i]=values[i]/10.929+2.15
                converted+=1
            elif not is_percent: unknown_units.append((measure,str(unit)))
        elif measure=="eGFR":
            if un not in {"mlmin173m2","mlmin173m²"}: unknown_units.append((measure,str(unit)))
        elif measure=="SBP":
            if un!="mmhg": unknown_units.append((measure,str(unit)))
        elif measure=="BMI":
            # BMI 按定义就是 kg/m²；官方数据的 BMI 行单位列为空，计数记录在审查结果里，而不是静默放过
            if pd.isna(unit) or un=="": bmi_without_unit+=1
            elif un not in {"kgm2","kgm²"}: unknown_units.append((measure,str(unit)))
        elif measure=="Height":
            if un not in {"cm","feetandinch"}: unknown_units.append((measure,str(unit)))
        elif measure=="Weight":
            if un!="kg": unknown_units.append((measure,str(unit)))
    if unknown_units: raise ValueError(f"不识别的单位：{sorted(set(unknown_units))}")
    d["standard_value"]=values
    return d,{"hba1c_mmol_mol_rows":converted,"unit_conversion_enabled":convert_units,
              "height_feet_inch_rows":int(imperial.sum()),"bmi_rows_without_unit":bmi_without_unit,
              "description_unmapped_but_canonical_measure_used":used_hint}


def reconstruct(tables,convert_units=True,use_measure_hint=True):
    master=tables["master"].copy(); disease=tables["diseases"].copy()
    if master.Patient_ID.duplicated().any(): raise ValueError("主表患者重复。")
    for table in (disease,tables["measurements"]):
        if not table.Patient_ID.isin(master.Patient_ID).all(): raise ValueError("存在孤立患者ID。")
    expected={"Age_At_2024","IRSD_Quintile","SMOKING_STATUS","CVD_Event","CVD_Time"}
    if not expected.issubset(master): raise ValueError(f"主表缺少{expected-set(master)}")
    out=pd.DataFrame({"Patient_ID":master.Patient_ID,"Age":pd.to_numeric(master.Age_At_2024)-7,
                      "IRSD_quintile":pd.to_numeric(master.IRSD_Quintile),
                      "smoking_status":master.SMOKING_STATUS.where(master.SMOKING_STATUS.isin(["non","ex","current"]),"unknown"),
                      "cvd_event":pd.to_numeric(master.CVD_Event),"CVD_Time_month_recorded":master.CVD_Time})
    unexpected=master.SMOKING_STATUS.notna()&~master.SMOKING_STATUS.isin(["non","ex","current","N/A"])
    if unexpected.any(): raise ValueError("主表出现未识别吸烟编码。")
    label="Category" if "Category" in disease else "Classification" if "Classification" in disease else None
    if label is None: raise ValueError("慢病表缺少Category或Classification。")
    disease["canonical"]=disease[label].map(disease_from_label)
    bad=disease.loc[disease.canonical.isna(),label].drop_duplicates().tolist()
    if bad: raise ValueError(f"慢病词典需要扩充，未识别：{bad}。不得直接把未知记录归为无病。")
    for c in ("diabetes","CKD","AF"):
        out[c]=out.Patient_ID.isin(disease.loc[disease.canonical==c,"Patient_ID"]).astype(int)
    cleaned,audit=normalize_measurements(tables["measurements"],convert_units,use_measure_hint)
    # 重复患者-测量记录禁止静默均值/取最近一次；数据版本改变应重新定义聚合窗口。
    duplicate=cleaned.duplicated(["Patient_ID","canonical_measure"],keep=False)
    if duplicate.any(): raise ValueError("同一患者存在重复同类测量，需要先明确定义聚合规则。")
    wide=cleaned.pivot(index="Patient_ID",columns="canonical_measure",values="standard_value").reset_index()
    out=out.merge(wide,on="Patient_ID",how="left",validate="one_to_one")
    if {"Height","Weight"}.issubset(out):
        # 官方版本中 80% 的人直接记录 BMI，其余 20% 只有身高和体重。按定义 BMI = 体重/身高²，
        # 这是用同一份病历里的实测值派生，不是从 Asset1 回填；每个值的来源写在 BMI_source 里。
        derived=out.Weight/(out.Height/100)**2
        if "BMI" not in out: out["BMI"]=np.nan
        recorded=out.BMI.notna()
        out["BMI_source"]=np.select([recorded,derived.notna()],["recorded","derived_from_height_weight"],"unavailable")
        out["BMI"]=out.BMI.where(recorded,derived)
    if "BMI" not in out:
        # 公开早期数据的检验表仅包含三个生化/生理指标；不可凭空补回BMI。
        if "BMI" in master:
            out=out.merge(master[["Patient_ID","BMI"]],on="Patient_ID",validate="one_to_one")
        else: out["BMI"]=np.nan
    if "BMI_source" not in out:
        out["BMI_source"]=np.where(out.BMI.notna(),"recorded","unavailable")
    month=pd.to_datetime(out.CVD_Time_month_recorded,format="%Y-%m",errors="raise")
    elapsed=(month.dt.year-2017)*12+month.dt.month-1
    out["coarsened_time_midpoint_years_NOT_original"]=(elapsed+.5)/12
    audit.update({"master_rows":len(master),"disease_rows":len(disease),"measurement_rows":len(cleaned),
                  "reconstructed_rows":len(out),"unknown_smoking":int((out.smoking_status=="unknown").sum()),
                  "BMI_available":bool(out.BMI.notna().any()),
                  "BMI_source_counts":out.BMI_source.value_counts().to_dict(),
                  "survival_time_recoverable":False,
                  "note":"Age仅按模拟规则减7并含四舍五入误差；cvd_time不可从统一月份无损还原。"})
    return out,audit,cleaned


def compare_to_clean(reconstructed,clean):
    """验证作者公开ID映射后，仅在共同可恢复字段上核对。"""
    if set(reconstructed.Patient_ID)!=set(clean.Patient_ID): raise ValueError("两套数据患者集合不匹配，不能按行盲目连接。")
    d=clean.merge(reconstructed,on="Patient_ID",suffixes=("_clean","_emr"),validate="one_to_one")
    # 先用几乎未改变的字段确认映射；否则不输出看似可信的差异表。
    if not np.array_equal(d.IRSD_quintile_clean,d.IRSD_quintile_emr) or not np.array_equal(d.cvd_event_clean,d.cvd_event_emr):
        raise ValueError("公开患者映射与当前数据不相符；请核对源版本。")
    if (np.abs(d.Age_clean-d.Age_emr)>.011).any(): raise ValueError("年龄映射核对失败。")
    rows=[]
    for c in ("Age","BMI","HbA1c","eGFR","SBP","IRSD_quintile","diabetes","CKD","AF","cvd_event"):
        a=d[f"{c}_clean"]; b=d[f"{c}_emr"]; observed=a.notna()&b.notna()
        tol=.011 if c in {"Age","BMI","HbA1c","eGFR","SBP"} else 0
        error=np.abs(a[observed]-b[observed])
        rows.append({"variable":c,"n_comparable":int(observed.sum()),"n_unavailable":int((~observed).sum()),
                     "mean_absolute_error":float(error.mean()) if len(error) else np.nan,
                     "max_absolute_error":float(error.max()) if len(error) else np.nan,
                     "tolerance":tol,"within_tolerance_fraction":float((error<=tol).mean()) if len(error) else np.nan})
    return pd.DataFrame(rows)
