import numpy as np
import pytest
from statsmodels.duration.hazard_regression import PHReg
from primecvd.survival import CoxModel
from primecvd.reconstruction import reconstruct,compare_to_clean,normalize_measurements

@pytest.fixture(scope="module")
def model(clean): return CoxModel(["Age","BMI","diabetes","SBP"],0).fit(clean.iloc[:2000])


def test_cox_coefficients_match_statsmodels(clean,model):
    d=clean.iloc[:2000]; X=model.encoder.transform(d).to_numpy()
    ref=PHReg(d.cvd_time.to_numpy(),X,status=d.cvd_event.to_numpy(),ties="breslow").fit(disp=0)
    np.testing.assert_allclose(model.beta,ref.params,atol=3e-5)


def test_risk_bounded_and_monotonic(clean,model):
    d=clean.iloc[2000:2200]
    a=model.predict_risk(d,2); b=model.predict_risk(d,5)
    assert np.all((a>=0)&(b<=1)&(a<=b))
    with pytest.raises(ValueError): model.predict_risk(d,10)


def test_json_model_roundtrip(clean,model,tmp_path):
    path=tmp_path/"model.json"; model.save(path); loaded=CoxModel.load(path)
    np.testing.assert_allclose(loaded.predict_risk(clean.iloc[:10],5),model.predict_risk(clean.iloc[:10],5))


def test_ridge_shrinks_standardized_coefficients(clean,model):
    r=CoxModel(["Age","BMI","diabetes","SBP"],.1).fit(clean.iloc[:2000])
    assert np.linalg.norm(r.beta)<np.linalg.norm(model.beta)
    assert "ci_low" not in r.coefficient_table()


def test_reconstruction_maps_and_missing_information(clean,emr):
    rec,audit,_=reconstruct(emr)
    tab=compare_to_clean(rec,clean)
    assert len(rec)==len(clean)
    assert rec.BMI.isna().all()
    assert "cvd_time" not in rec
    assert (rec.smoking_status=="unknown").sum()>0
    assert not audit["survival_time_recoverable"]
    avail=tab[tab.n_comparable>0]
    assert np.allclose(avail.within_tolerance_fraction,1)


def test_omitted_unit_conversion_changes_hba1c(emr):
    correct,_,_=reconstruct(emr); bad,_,_=reconstruct(emr,convert_units=False)
    assert np.max(np.abs(correct.HbA1c-bad.HbA1c))>10


def test_unknown_unit_rejected(emr):
    m=emr["measurements"].copy(); m.loc[m.index[0],"Unit"]="unrecognised"
    with pytest.raises(ValueError): normalize_measurements(m)


def test_unknown_disease_not_treated_as_no_disease(emr):
    tables={k:d.copy() for k,d in emr.items()}
    tables["diseases"].loc[tables["diseases"].index[0],"Category"]="unknown syndrome"
    with pytest.raises(ValueError): reconstruct(tables)


def test_duplicate_measurement_not_silently_averaged(emr):
    import pandas as pd
    tables={k:d.copy() for k,d in emr.items()}
    tables["measurements"]=pd.concat([tables["measurements"],tables["measurements"].iloc[:1]])
    with pytest.raises(ValueError): reconstruct(tables)


# ---------------------------------------------------------------------------
# 官方 Asset2 的写法、单位和 BMI 派生（2026-09-27 起在官方文件上实测）
# ---------------------------------------------------------------------------
import pandas as pd
from pathlib import Path
from primecvd.reconstruction import disease_from_label,feet_inches_to_cm

OFFICIAL_DESCRIPTIONS={
    "HbA1c":["HbA1c","HBA1C","A1C","Hb A1c","Glycated hemoglobin","Glycosylated hemoglobin","HA1C","HbAlc",
             "LOINC: 4548-4","HbA1c mmol/mol"],
    "eGFR":["eGFR","EGFR","eGFR (mL/min/1.73m²)","GFR","Estimated GFR","GFR-e","e-GFR","e GFR","EGfr","eGFr"],
    "SBP":["SBP","Systolic BP","Systolic Blood Pressure","BP Systolic","BP_sys","BP SYS","BP_Systolic",
           "Blood Pressure – Systolic","SBP (mmHg)","SyBP","Syst BP","SystolicBP"],
}
UNITS={"HbA1c":"%","eGFR":"mL/min/1.73m²","SBP":"mmHg"}


def test_official_measure_labels_all_mapped():
    rows=[{"Patient_ID":1,"Description":desc,"Value":"5.0","Unit":UNITS[m],"Date":"2015-01"}
          for m,descs in OFFICIAL_DESCRIPTIONS.items() for desc in descs]
    d,_=normalize_measurements(pd.DataFrame(rows))
    expected=[m for m,descs in OFFICIAL_DESCRIPTIONS.items() for _ in descs]
    assert d.canonical_measure.tolist()==expected


def test_official_disease_labels_all_mapped():
    labels={"diabetes":["Diabetes","T2DM","ICD10: E11","ICD9:250","High glucose","High blood sugar"],
            "CKD":["CKD","Chronic kidney disease","ICD10: N18","ICD9: 585","Renal insufficiency","Chronic renal failure","CRF"],
            "AF":["AF","Atrial fibrillation","AFib","A-fib","ICD10: I48","ICD9: 427.31"]}
    for key,values in labels.items():
        assert [disease_from_label(v) for v in values]==[key]*len(values)


def test_feet_inches_parsing_including_uncarried_inches():
    assert feet_inches_to_cm("5'7\"")==pytest.approx(170.18)
    assert feet_inches_to_cm("5'12\"")==pytest.approx(feet_inches_to_cm("6'0\""))
    with pytest.raises(ValueError): feet_inches_to_cm("170")


def test_hba1c_unit_column_wins_over_name():
    # 名称写着 mmol/mol，单位列写 %：按 % 处理，不做换算
    m=pd.DataFrame({"Patient_ID":[1,2],"Description":["HbA1c mmol/mol","HbA1c"],"Value":["6.0","42.1"],
                    "Unit":["%","mmol/mol"],"Date":["2015-01"]*2})
    d,audit=normalize_measurements(m)
    assert d.standard_value.iloc[0]==pytest.approx(6.0)
    assert d.standard_value.iloc[1]==pytest.approx(42.1/10.929+2.15)
    assert audit["hba1c_mmol_mol_rows"]==1


def test_bmi_derived_from_height_weight_and_labelled():
    master=pd.DataFrame({"Patient_ID":[1,2,3],"Age_At_2024":[57.0,50.0,40.0],"IRSD_Quintile":[1,2,3],
                         "SMOKING_STATUS":["non",np.nan,"ex"],"CVD_Event":[0,1,0],
                         "CVD_Time":["2022-12","2019-05","2022-12"]})
    base=[(p,"HbA1c","5.0","%") for p in (1,2,3)]+[(p,"eGFR","80","mL/min/1.73m²") for p in (1,2,3)]
    base+=[(p,"SBP","120","mmHg") for p in (1,2,3)]
    base+=[(1,"BMI","25.0",np.nan),(2,"Height","5'7\"","feet-and-inch"),(2,"Weight","70.0","kg"),
           (3,"Height","180.0","cm")]
    meas=pd.DataFrame(base,columns=["Patient_ID","Description","Value","Unit"]).assign(Date="2015-01")
    diseases=pd.DataFrame({"Patient_ID":[2],"Category":["CRF"],"Date":["2014-01"]})
    rec,audit,_=reconstruct({"master":master,"diseases":diseases,"measurements":meas})
    rec=rec.set_index("Patient_ID")
    assert rec.loc[1,"BMI"]==pytest.approx(25.0) and rec.loc[1,"BMI_source"]=="recorded"
    assert rec.loc[2,"BMI"]==pytest.approx(70/(1.7018**2)) and rec.loc[2,"BMI_source"]=="derived_from_height_weight"
    assert np.isnan(rec.loc[3,"BMI"]) and rec.loc[3,"BMI_source"]=="unavailable"    # 只有身高，不编造
    assert rec.loc[2,"CKD"]==1 and rec.loc[2,"smoking_status"]=="unknown"
    assert audit["bmi_rows_without_unit"]==1 and audit["height_feet_inch_rows"]==1


OFFICIAL_RAW=Path(__file__).resolve().parents[1]/"data"/"raw"


@pytest.mark.skipif(not (OFFICIAL_RAW/"manifest.json").exists(),reason="官方数据未下载：python run.py download")
def test_official_files_reconstruct_against_asset1():
    from primecvd.common import load_config
    from primecvd.data import load_clean,load_emr
    cfg=load_config("configs/official.json")
    rec,audit,_=reconstruct(load_emr(cfg))
    tab=compare_to_clean(rec,load_clean(cfg)).set_index("variable")
    assert audit["reconstructed_rows"]==50000 and audit["BMI_source_counts"]=={"recorded":40000,"derived_from_height_weight":10000}
    for c in ("HbA1c","eGFR","SBP","IRSD_quintile","diabetes","CKD","AF","cvd_event"):
        assert tab.loc[c,"max_absolute_error"]<1e-9, c
    assert tab.loc["Age","max_absolute_error"]<=0.0051        # 两位小数的舍入
    assert tab.loc["BMI","max_absolute_error"]<0.7            # 由身高体重派生：身高 0.1 cm / 整英寸、体重 0.1 kg 的舍入
