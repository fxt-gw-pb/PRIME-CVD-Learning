import numpy as np
import pandas as pd
import pytest
from primecvd.data import validate_clean,patient_id_from_source_row
from primecvd.splitting import create_splits,validate_splits,select_split
from primecvd.features import FeatureEncoder


def test_data_schema(clean):
    validate_clean(clean)
    assert len(clean)==5000
    assert clean.Patient_ID.is_unique

@pytest.mark.parametrize("column,value",[("cvd_time",0),("cvd_time",np.nan),("cvd_event",2),("IRSD_quintile",8),("smoking_status","other"),("Age",np.inf)])
def test_invalid_data_rejected(clean,column,value):
    d=clean.copy(); d.loc[0,column]=value
    with pytest.raises(ValueError): validate_clean(d)


def test_patient_id_mapping():
    np.testing.assert_array_equal(patient_id_from_source_row([0,1,2,3,4]),[269,272,281,296,317])
    with pytest.raises(ValueError): patient_id_from_source_row([-.1])


def test_split_exact_sizes_disjoint_and_repeatable(clean,cfg):
    s=create_splits(clean,cfg); again=create_splits(clean,cfg)
    pd.testing.assert_frame_equal(s,again)
    assert s.split.value_counts().to_dict()=={"train":3500,"valid":750,"test":750}
    assert len(select_split(clean,s,"train"))==3500
    validate_splits(s,clean)


def test_duplicate_split_rejected(clean,cfg):
    s=create_splits(clean,cfg)
    with pytest.raises(ValueError): validate_splits(pd.concat([s,s.iloc[:1]]),clean)

@pytest.mark.parametrize("bad",["cvd_time","cvd_event","Patient_ID","source_row_index","coarsened_time_midpoint_years_NOT_original"])
def test_target_id_leakage_blocked(bad):
    with pytest.raises(ValueError): FeatureEncoder(["Age",bad])


def test_encoder_uses_train_median_only(clean):
    train=clean.iloc[:1000].copy(); valid=clean.iloc[1000:1100].copy()
    enc=FeatureEncoder(["Age","BMI"]).fit(train)
    before=dict(enc.state["medians"])
    valid.loc[valid.index[0],"BMI"]=np.nan
    valid.loc[valid.index[1:],"BMI"]=999
    out=enc.transform(valid)
    assert enc.state["medians"]==before
    expected=(before["BMI"]/5-enc.state["means"]["BMI_per5"])/enc.state["scales"]["BMI_per5"]
    assert out.iloc[0]["BMI_per5"]==pytest.approx(expected)


def test_unseen_category_not_silently_reference(clean):
    enc=FeatureEncoder(["Age","smoking_status"]).fit(clean.iloc[:1000])
    v=clean.iloc[:2].copy(); v.loc[v.index[0],"smoking_status"]="unknown"
    with pytest.raises(ValueError): enc.transform(v)
